"""Tkinter system smoke tests. Automatically skipped when no graphical display exists."""
import os
import tempfile
import unittest
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

from data_access import Database
import app  

class TkinterSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except tk.TclError as exc:
            raise unittest.SkipTest(
                f"Нет доступного графического дисплея: UI smoke-тесты описаны в TEST_CHECKLIST.md ({exc})"
            )

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="vet_ui_test_")
        db = Database(str(Path(self.temp_dir.name) / "ui_test.db"))
        db.initialize()
        self.db_patcher = patch("app.Database", return_value=db)
        self.db_patcher.start()
        self.app = app.App()
        self.app.update_idletasks()

    def tearDown(self):
        if getattr(self, "app", None) is not None:
            try:
                self.app.destroy()
            except Exception:
                pass
        self.db_patcher.stop()
        self.temp_dir.cleanup()

    def tab_labels(self):
        notebooks = [w for w in self.app.winfo_children() if isinstance(w, ttk.Notebook)]
        self.assertEqual(len(notebooks), 1)
        notebook = notebooks[0]
        return notebook, [notebook.tab(tab, "text") for tab in notebook.tabs()]

    def login(self, login, password):
        self.app.login.insert(0, login)
        self.app.password.insert(0, password)
        self.app.do_login()
        self.app.update_idletasks()

    def test_user_sees_only_user_tabs(self):
        self.login("user", "user123")
        _notebook, labels = self.tab_labels()
        self.assertIn("Мои питомцы", labels)
        self.assertIn("Приём", labels)
        self.assertIn("Прививки", labels)
        self.assertIn("Магазин", labels)
        self.assertNotIn("Отчёты администратора", labels)
        self.assertNotIn("Аудит", labels)

    def test_admin_sees_report_and_audit_tabs(self):
        self.login("admin", "admin123")
        _notebook, labels = self.tab_labels()
        self.assertIn("Отчёты администратора", labels)
        self.assertIn("Аудит", labels)

    def test_added_pet_appears_in_booking_and_vaccination_choices(self):
        self.login("user", "user123")
        notebook, labels = self.tab_labels()
        pets_frame = notebook.nametowidget(notebook.tabs()[labels.index("Мои питомцы")])
        row = next(child for child in pets_frame.winfo_children() if isinstance(child, ttk.Frame))
        entries = [child for child in row.winfo_children() if isinstance(child, ttk.Entry)]
        entries[0].delete(0, "end"); entries[0].insert(0, "Регрессионный тест")
        # The pet form order is name, species combobox, breed, age.
        entries[1].delete(0, "end"); entries[1].insert(0, "Порода")
        button = next(child for child in row.winfo_children()
                      if isinstance(child, ttk.Button) and child.cget("text") == "Добавить питомца")
        button.invoke()
        self.app.update_idletasks()
        for i, label in enumerate(labels):
            if label in ("Приём", "Прививки"):
                page = notebook.nametowidget(notebook.tabs()[i])
                booking_row = next(child for child in page.winfo_children() if isinstance(child, ttk.Frame))
                combo = next(child for child in booking_row.winfo_children() if isinstance(child, ttk.Combobox))
                self.assertTrue(any("Регрессионный тест" in str(value) for value in combo.cget("values")))


if __name__ == "__main__":
    unittest.main()
