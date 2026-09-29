import unittest
import os
import tempfile
from unittest.mock import patch
from cold_mailer_pro import parse_and_validate_email, ColdMailerApp, TEMPLATES

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

class TestCSVLoading(unittest.TestCase):
    def test_load_csv_valid(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)

        csv_content = "name,email\nAlice,alice@example.com\nBob,bob@domain.org\n"
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            with patch("tkinter.filedialog.askopenfilename", return_value=tmp_path):
                app.load_csv()

            self.assertEqual(len(app.email_list), 2)
            self.assertEqual(app.email_list[0], {"name": "Alice", "email": "alice@example.com"})
            self.assertEqual(app.email_list[1], {"name": "Bob", "email": "bob@domain.org"})
        finally:
            os.remove(tmp_path)
            root.destroy()

    def test_load_csv_filters_invalid_rows(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)

        csv_content = (
            "name,email\n"
            "Alice,alice@example.com\n"
            ",no_name@example.com\n"
            "Invalid Email,not-an-email\n"
            "Bob,bob@domain.org\n"
        )
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            with patch("tkinter.filedialog.askopenfilename", return_value=tmp_path):
                app.load_csv()

            self.assertEqual(len(app.email_list), 2)
            self.assertEqual(app.email_list[0]["name"], "Alice")
            self.assertEqual(app.email_list[1]["name"], "Bob")
        finally:
            os.remove(tmp_path)
            root.destroy()

    def test_load_csv_cancelled(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)

        with patch("tkinter.filedialog.askopenfilename", return_value=""):
            app.load_csv()

        self.assertEqual(len(app.email_list), 0)
        root.destroy()

class TestSendConfigurationValidation(unittest.TestCase):
    def test_send_no_data(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)
        app.email_list = []

        with patch.object(app, "_dialog") as mock_dialog:
            app._send_emails()
            mock_dialog.assert_called_once_with("warning", "No Data", "Load CSV first")

        root.destroy()

    def test_send_missing_credentials(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)
        app.email_list = [{"name": "Alice", "email": "alice@example.com"}]

        with patch.object(app, "_dialog") as mock_dialog:
            app._send_emails()
            mock_dialog.assert_called_once_with("warning", "Missing", "Enter sender email and app password")

        root.destroy()

    def test_send_missing_subject_or_body(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)
        app.email_list = [{"name": "Alice", "email": "alice@example.com"}]
        app.email_entry.insert(0, "sender@example.com")
        app.password_entry.insert(0, "app-password")

        with patch.object(app, "_dialog") as mock_dialog:
            app._send_emails()
            mock_dialog.assert_called_once_with("warning", "Missing", "Subject and body required")

        root.destroy()

    def test_send_invalid_limit_or_delay(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)
        app.email_list = [{"name": "Alice", "email": "alice@example.com"}]
        app.email_entry.insert(0, "sender@example.com")
        app.password_entry.insert(0, "app-password")
        app.subject_entry.insert(0, "Test Subject")
        app.body_text.insert("1.0", "Hello {name}")

        app.limit_entry.insert(0, "invalid_num")

        with patch.object(app, "_dialog") as mock_dialog:
            app._send_emails()
            mock_dialog.assert_called_once_with("error", "Error", "Limit & delay must be integers")

        root.destroy()

class TestTemplates(unittest.TestCase):
    def test_apply_template(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)

        for template_name, expected_body in TEMPLATES.items():
            app.template_var.set(template_name)
            app.apply_template()
            body_content = app.body_text.get("1.0", tk.END).strip()
            self.assertEqual(body_content, expected_body.strip())

        root.destroy()

if __name__ == "__main__":
    unittest.main()

class TestAttachmentsAndUIStatus(unittest.TestCase):
    def test_select_and_clear_attachment(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".pdf") as tmp:
            tmp.write("dummy pdf content")
            tmp_path = tmp.name

        try:
            with patch("tkinter.filedialog.askopenfilename", return_value=tmp_path):
                app.select_attachment()

            self.assertEqual(app.attachment_path, tmp_path)
            self.assertIn(os.path.basename(tmp_path), app.attachment_status_lbl.cget("text"))

            app.clear_attachment()
            self.assertIsNone(app.attachment_path)
            self.assertEqual(app.attachment_status_lbl.cget("text"), "No file attached")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            root.destroy()

    def test_csv_status_label_update(self):
        import tkinter as tk
        root = tk.Tk()
        app = ColdMailerApp(root)

        csv_content = "name,email\nAlice,alice@example.com\n"
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            with patch("tkinter.filedialog.askopenfilename", return_value=tmp_path):
                app.load_csv()

            self.assertIn("Loaded 1 contacts", app.csv_status_lbl.cget("text"))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            root.destroy()
