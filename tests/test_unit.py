"""Unit tests for isolated validation and password helpers (unittest/xUnit style)."""
import unittest
from datetime import datetime, timedelta
from business_logic import ClinicService, password_hash, verify_password


class NoDatabase:
    """Fails fast if a validation-only test unexpectedly attempts database access."""
    def query(self, *_args, **_kwargs):
        raise AssertionError("Database must not be accessed by this unit test")

    def connect(self):
        raise AssertionError("Database must not be accessed by this unit test")


class PasswordTests(unittest.TestCase):
    def test_hash_is_not_plain_text_and_password_verifies(self):
        stored = password_hash("correct horse", b"0123456789abcdef")
        self.assertNotEqual(stored, "correct horse")
        self.assertTrue(verify_password("correct horse", stored))

    def test_wrong_password_does_not_verify(self):
        self.assertFalse(verify_password("wrong", password_hash("right")))

    def test_malformed_hash_returns_false(self):
        for stored in (None, "", "not-a-hash", "gg$bad"):
            with self.subTest(stored=stored):
                self.assertFalse(verify_password("anything", stored))


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.service = ClinicService(NoDatabase())

    def test_add_pet_rejects_blank_name(self):
        with self.assertRaisesRegex(ValueError, "кличку"):
            self.service.add_pet(2, "   ", "Кошка", "", 2)

    def test_add_pet_rejects_blank_species(self):
        with self.assertRaisesRegex(ValueError, "вид"):
            self.service.add_pet(2, "Мурка", " ", "", 2)

    def test_add_pet_rejects_non_integer_age(self):
        with self.assertRaisesRegex(ValueError, "целым числом"):
            self.service.add_pet(2, "Мурка", "Кошка", "", "два")

    def test_add_pet_age_boundaries(self):
        for age in (-1, 101):
            with self.subTest(age=age), self.assertRaisesRegex(ValueError, "от 0 до 100"):
                self.service.add_pet(2, "Мурка", "Кошка", "", age)

    def test_booking_rejects_blank_reason(self):
        with self.assertRaisesRegex(ValueError, "описание"):
            self.service.book(2, 1, "2099-01-01 10:00", "   ", "Приём")

    def test_booking_rejects_invalid_date(self):
        with self.assertRaisesRegex(ValueError, "формате"):
            self.service.book(2, 1, "not-a-date", "Осмотр", "Приём")

    def test_booking_rejects_past_time(self):
        past = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        with self.assertRaisesRegex(ValueError, "будущем"):
            self.service.book(2, 1, past, "Осмотр", "Приём")

    def test_booking_rejects_unknown_kind(self):
        with self.assertRaisesRegex(ValueError, "тип"):
            self.service.book(2, 1, "2099-01-01 10:00", "Осмотр", "Груминг")

    def test_purchase_quantity_boundaries(self):
        for quantity in (0, -1, 100, "abc", 1.5, True):
            with self.subTest(quantity=quantity), self.assertRaisesRegex(ValueError, "Количество"):
                self.service.buy(2, 1, quantity)


if __name__ == "__main__":
    unittest.main()
