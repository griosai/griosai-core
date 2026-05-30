import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from griosai.brain import ensure_vault
from griosai.cli import main
from griosai.vault_audit import audit_exit_code, audit_vault, format_audit_json, format_audit_text


class VaultAuditTests(unittest.TestCase):
    def test_audit_reports_inventory_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            note = vault / "notes" / "daily.md"
            body = b"# Daily\n"
            note.write_bytes(body)

            audit = audit_vault(vault)
            parsed = json.loads(format_audit_json(audit))

            self.assertEqual(audit_exit_code(audit), 0)
            self.assertEqual(parsed["summary"]["files"], 1)
            self.assertEqual(parsed["summary"]["bytes"], len(body))
            self.assertEqual(parsed["summary"]["directories"]["notes"]["files"], 1)
            self.assertEqual(parsed["files"][0]["path"], "notes/daily.md")
            self.assertEqual(parsed["files"][0]["sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(parsed["summary"]["findings"]["fail"], 0)

    def test_audit_fails_missing_layout_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            (vault / "notes").rmdir()
            try:
                os.symlink(Path(tmp) / "outside", vault / "images" / "outside")
            except OSError:
                self.skipTest("symlink creation is not available")

            audit = audit_vault(vault)
            codes = {finding.code for finding in audit.findings}

            self.assertEqual(audit_exit_code(audit), 1)
            self.assertIn("layout-missing", codes)
            self.assertIn("file-symlink", codes)

    def test_audit_warns_on_secret_like_text_without_printing_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("A" * 24)
            (vault / "notes" / "secret.md").write_text(f"token={secret}\n", encoding="utf-8")

            audit = audit_vault(vault)
            output = format_audit_json(audit)
            codes = {finding.code for finding in audit.findings}

            self.assertEqual(audit_exit_code(audit), 0)
            self.assertIn("secret-looking-key", codes)
            self.assertIn("secret-looking-assignment", codes)
            self.assertNotIn(secret, output)

    def test_cli_vault_audit_json_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            (vault / "notes" / "daily.md").write_text("# Daily\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["vault-audit", "--vault", str(vault), "--json"]), 0)
            parsed = json.loads(output.getvalue())
            self.assertEqual(parsed["summary"]["files"], 1)

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["vault-audit", "--vault", str(vault)]), 0)
            self.assertIn("Findings: none", output.getvalue())

    def test_audit_missing_vault_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = audit_vault(Path(tmp) / "missing")

            self.assertEqual(audit_exit_code(audit), 1)
            self.assertEqual(audit.findings[0].code, "vault-missing")


if __name__ == "__main__":
    unittest.main()
