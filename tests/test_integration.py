"""Integration tests: BLL + DAL + an isolated SQLite test database."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from business_logic import ClinicService
from data_access import Database


class ClinicIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="vet_test_")
        self.db = Database(str(Path(self.temp_dir.name) / "test_clinic.db"))
        self.db.initialize()
        self.service = ClinicService(self.db)
        self.user = self.service.login("user", "user123")
        self.admin = self.service.login("admin", "admin123")
        self.assertIsNotNone(self.user)
        self.assertIsNotNone(self.admin)

    def tearDown(self):
        self.temp_dir.cleanup()

    def future_time(self, days=3, minutes=0):
        value = datetime.now() + timedelta(days=days, minutes=minutes)
        return value.replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

    def add_pet(self, owner_id=None, name="Тестовый питомец"):
        self.service.add_pet(owner_id or self.user["id"], name, "Кошка", "Тестовая порода", 2)
        return self.db.query("SELECT PetID FROM Pets WHERE PetName=? ORDER BY PetID DESC", (name,))[0][0]

    def test_demo_users_and_seed_products_are_created(self):
        self.assertEqual(self.user["role"], "user")
        self.assertEqual(self.admin["role"], "admin")
        self.assertEqual(len(self.service.products()), 3)
        self.assertIsNone(self.service.login("not-found", "wrong"))
        self.assertIsNone(self.service.login("user", "wrong"))

    def test_add_pet_accepts_age_boundaries(self):
        owner_id = self.user["id"]
        for age in (0, 100):
            self.service.add_pet(owner_id, f"Возраст {age}", "Кошка", "", age)
        rows = self.db.query("SELECT Age FROM Pets WHERE PetName IN (?,?) ORDER BY PetName",
                             ("Возраст 0", "Возраст 100"))
        self.assertEqual(sorted(row[0] for row in rows), [0, 100])

    def test_add_pet_is_persisted_and_audited(self):
        self.add_pet()
        rows = self.service.pets(self.user["id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Тестовый питомец")
        audit = self.service.audit()
        event = next(r for r in audit if r[1] == "Pets" and r[2] == "INSERT")
        self.assertIn('"PetName":"Тестовый питомец"', event[5])

    def test_booking_is_persisted_and_overlap_is_blocked(self):
        pet_id = self.add_pet()
        first = self.future_time()
        self.service.book(self.user["id"], pet_id, first, "Плановый осмотр", "Приём")
        self.assertEqual(len(self.service.appointments(self.user["id"], "Приём")), 1)
        start = datetime.strptime(first, "%Y-%m-%d %H:%M")
        second = (start + timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M")
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.book(self.user["id"], pet_id, second, "Повторный осмотр", "Приём")

    def test_user_cannot_book_another_owners_pet(self):
        pet_id = self.add_pet(self.admin["id"], "Питомец администратора")
        with self.assertRaisesRegex(ValueError, "своего питомца"):
            self.service.book(self.user["id"], pet_id, self.future_time(), "Осмотр", "Приём")

    def test_purchase_accepts_upper_quantity_boundary(self):
        with self.db.connect() as con:
            con.execute("INSERT INTO Products(ProductName,Price,Stock) VALUES(?,?,?)",
                        ("Тестовый товар 99", 1.0, 99))
        product_id = self.db.query("SELECT ProductID FROM Products WHERE ProductName=?",
                                   ("Тестовый товар 99",))[0][0]
        self.service.buy(self.user["id"], product_id, 99)
        self.assertEqual(self.db.query("SELECT Stock FROM Products WHERE ProductID=?", (product_id,))[0][0], 0)
        self.assertEqual(self.db.query("SELECT Quantity FROM Purchases WHERE ProductID=?", (product_id,))[0][0], 99)

    def test_purchase_reduces_stock_and_updates_sales_view(self):
        product_id, _name, _price, original_stock = self.service.products()[0]
        self.service.buy(self.user["id"], product_id, 2)
        new_stock = self.db.query("SELECT Stock FROM Products WHERE ProductID=?", (product_id,))[0][0]
        self.assertEqual(new_stock, original_stock - 2)
        sales = self.db.query("SELECT Sold FROM vw_ProductSales WHERE ProductID=?", (product_id,))[0][0]
        self.assertEqual(sales, 2)

    def test_failed_purchase_rolls_back_both_purchase_and_stock_change(self):
        product_id, _name, _price, stock = self.service.products()[0]
        with self.db.connect() as con:
            con.execute("""CREATE TRIGGER test_force_update_failure BEFORE UPDATE OF Stock ON Products
                          BEGIN SELECT RAISE(ABORT, 'forced test failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.buy(self.user["id"], product_id, 1)
        self.assertEqual(self.db.query("SELECT Stock FROM Products WHERE ProductID=?", (product_id,))[0][0], stock)
        self.assertEqual(self.db.query("SELECT COUNT(*) FROM Purchases")[0][0], 0)

    def test_purchase_rejects_missing_product_and_insufficient_stock(self):
        with self.assertRaisesRegex(ValueError, "Товар не найден"):
            self.service.buy(self.user["id"], 999999, 1)
        product_id, _name, _price, stock = self.service.products()[0]
        with self.assertRaisesRegex(ValueError, "Недостаточно"):
            self.service.buy(self.user["id"], product_id, stock + 1)
        self.assertEqual(self.db.query("SELECT COUNT(*) FROM Purchases")[0][0], 0)

    def test_report_returns_summary_metrics(self):
        labels = {row[0] for row in self.service.report()}
        self.assertEqual(labels, {"Всего питомцев", "Записей на приём", "Продажи, сумма", "Средний чек"})

    def test_database_constraints_reject_invalid_age_and_bad_foreign_key(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.connect() as con:
                con.execute("INSERT INTO Pets(OwnerID,PetName,Species,Age) VALUES(?,?,?,?)",
                            (self.user["id"], "Не допустимый", "Кошка", 101))
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.connect() as con:
                con.execute("INSERT INTO Pets(OwnerID,PetName,Species,Age) VALUES(?,?,?,?)",
                            (999999, "Чужой", "Кошка", 1))

    def test_appointment_details_view_contains_owner_and_pet(self):
        pet_id = self.add_pet()
        self.service.book(self.user["id"], pet_id, self.future_time(), "Плановый осмотр", "Приём")
        row = self.db.query("SELECT PetName,OwnerName,Kind FROM vw_AppointmentDetails")[0]
        self.assertEqual(row[0], "Тестовый питомец")
        self.assertEqual(row[1], self.user["name"])
        self.assertEqual(row[2], "Приём")


if __name__ == "__main__":
    unittest.main()
