import unittest
import tempfile
import os
import csv
import base64
from email.mime.base import MIMEBase
from email import encoders

class TestColdMailerLogic(unittest.TestCase):

    def test_csv_loading_validation(self):
        """Test that CSV loader correctly parses valid rows and filters invalid ones."""
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as f:
            f.write("name,email\n")
            f.write("Alice,alice@example.com\n")
            f.write("Bob,invalid-email\n")
            f.write(",no-name@example.com\n")
            f.write("Charlie,charlie@domain.org\n")
            f_path = f.name

        try:
            from email.utils import parseaddr
            loaded = []
            with open(f_path, newline="", encoding="utf-8") as csv_file:
                for row in csv.DictReader(csv_file):
                    name = row.get("name", "").strip()
                    email = row.get("email", "").strip()
                    _, addr = parseaddr(email)
                    local, _, domain = addr.partition("@")
                    if name and local and domain and "." in domain and not domain.startswith("."):
                        loaded.append({"name": name, "email": addr})

            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0], {"name": "Alice", "email": "alice@example.com"})
            self.assertEqual(loaded[1], {"name": "Charlie", "email": "charlie@domain.org"})
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    def test_pre_encoded_attachment(self):
        """Test that pre-encoding attachment payload matches MIME base64 structure."""
        test_content = b"Hello world attachment content"
        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            f.write(test_content)
            f_path = f.name

        try:
            # Pre-read and encode (optimized approach)
            with open(f_path, "rb") as f:
                cached_payload = base64.b64encode(f.read()).decode("ascii")

            part_opt = MIMEBase("application", "octet-stream")
            part_opt.set_payload(cached_payload)
            part_opt["Content-Transfer-Encoding"] = "base64"

            # Standard encoders.encode_base64 approach
            part_std = MIMEBase("application", "octet-stream")
            part_std.set_payload(test_content)
            encoders.encode_base64(part_std)

            # Raw decoded content should be identical
            decoded_opt = base64.b64decode(part_opt.get_payload())
            decoded_std = base64.b64decode(part_std.get_payload())

            self.assertEqual(decoded_opt, test_content)
            self.assertEqual(decoded_std, test_content)
            self.assertEqual(decoded_opt, decoded_std)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

if __name__ == "__main__":
    unittest.main()
