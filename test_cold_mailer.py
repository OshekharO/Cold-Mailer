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

if __name__ == "__main__":
    unittest.main()
