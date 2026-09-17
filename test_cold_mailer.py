import unittest
import os
import tempfile
from cold_mailer_pro import parse_and_validate_email, ColdMailerApp

class TestEmailValidation(unittest.TestCase):
    def test_valid_emails(self):
        self.assertEqual(parse_and_validate_email("rahul@example.com"), "rahul@example.com")
        self.assertEqual(parse_and_validate_email("Rahul Sharma <rahul@example.com>"), "rahul@example.com")
        self.assertEqual(parse_and_validate_email("anita@company.co.in"), "anita@company.co.in")

    def test_invalid_emails(self):
        self.assertEqual(parse_and_validate_email("invalid_email"), "")
        self.assertEqual(parse_and_validate_email("@example.com"), "")
        self.assertEqual(parse_and_validate_email("user@"), "")
        self.assertEqual(parse_and_validate_email("user@.com"), "")
        self.assertEqual(parse_and_validate_email("user@com"), "")

class TestPasswordVisibilityToggle(unittest.TestCase):
    def test_toggle_password_visibility(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)

        # Initial state should be hidden with bullet character
        self.assertEqual(app.password_entry.cget("show"), "•")
        self.assertEqual(app.toggle_pass_btn.cget("text"), "👁 Show")

        # Toggle once -> visible
        app.toggle_password_visibility()
        self.assertEqual(app.password_entry.cget("show"), "")
        self.assertEqual(app.toggle_pass_btn.cget("text"), "🙈 Hide")

        # Toggle twice -> hidden
        app.toggle_password_visibility()
        self.assertEqual(app.password_entry.cget("show"), "•")
        self.assertEqual(app.toggle_pass_btn.cget("text"), "👁 Show")

        root.destroy()

if __name__ == "__main__":
    unittest.main()
