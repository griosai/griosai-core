import io
import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

from griosai.brain import ensure_vault
from griosai.cli import main
from griosai.vault_archive import (
    BACKUP_MANIFEST,
    BACKUP_SCHEMA,
    VaultArchiveError,
    backup_vault,
    restore_vault,
    verify_backup,
)


class VaultArchiveTests(unittest.TestCase):
    def test_backup_and_restore_round_trip_without_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = _sample_vault(root / "vault")
            archive = backup_vault(vault, output_path=root / "backups")
            restored = root / "restored"

            result = restore_vault(archive.archive_path, vault_dir=restored)

            self.assertEqual(result.file_count, 3)
            self.assertEqual((restored / "notes" / "daily.md").read_text(encoding="utf-8"), "# Daily\n")
            self.assertEqual((restored / "dashboards" / "daily.html").read_text(encoding="utf-8"), "<h1>Daily</h1>\n")
            self.assertEqual((restored / "images" / "pixel.png").read_bytes(), b"png")

            with zipfile.ZipFile(archive.archive_path) as handle:
                manifest = json.loads(handle.read(BACKUP_MANIFEST).decode("utf-8"))
            self.assertEqual(manifest["schema"], BACKUP_SCHEMA)
            encoded = json.dumps(manifest)
            self.assertNotIn(str(root), encoded)
            self.assertEqual(
                sorted(item["path"] for item in manifest["files"]),
                ["dashboards/daily.html", "images/pixel.png", "notes/daily.md"],
            )

            verified = verify_backup(archive.archive_path)
            self.assertTrue(verified.ok)
            self.assertEqual(verified.file_count, 3)
            self.assertEqual(verified.total_bytes, archive.total_bytes)

    def test_backup_allocates_unique_archive_without_clobbering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = _sample_vault(root / "vault")
            exact = root / "vault.zip"
            exact.write_text("do not replace", encoding="utf-8")

            result = backup_vault(vault, output_path=exact)

            self.assertNotEqual(result.archive_path, exact)
            self.assertEqual(exact.read_text(encoding="utf-8"), "do not replace")
            self.assertTrue(result.archive_path.name.startswith("vault-"))

    def test_backup_rejects_output_inside_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = _sample_vault(Path(tmp) / "vault")

            with self.assertRaises(VaultArchiveError):
                backup_vault(vault, output_path=vault / "inbox" / "backup.zip")

    def test_restore_refuses_existing_files_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = _sample_vault(root / "vault")
            archive = backup_vault(vault, output_path=root / "vault.zip")
            restored = _sample_vault(root / "restored")

            with self.assertRaises(FileExistsError):
                restore_vault(archive.archive_path, vault_dir=restored)

            result = restore_vault(archive.archive_path, vault_dir=restored, overwrite=True)
            self.assertGreater(result.overwritten_count, 0)

    def test_restore_rejects_path_traversal_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "bad.zip"
            manifest = {
                "schema": BACKUP_SCHEMA,
                "files": [
                    {
                        "path": "../evil.md",
                        "size": 4,
                        "sha256": "0" * 64,
                    }
                ],
            }
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr(BACKUP_MANIFEST, json.dumps(manifest))
                handle.writestr("../evil.md", "evil")

            with self.assertRaises(VaultArchiveError):
                restore_vault(archive, vault_dir=Path(tmp) / "vault")

    def test_restore_rejects_invalid_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "not-a-zip.zip"
            archive.write_text("not a zip", encoding="utf-8")

            with self.assertRaises(VaultArchiveError):
                restore_vault(archive, vault_dir=Path(tmp) / "vault")

    def test_restore_rejects_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "bad-digest.zip"
            body = b"safe"
            manifest = {
                "schema": BACKUP_SCHEMA,
                "files": [
                    {
                        "path": "notes/safe.md",
                        "size": len(body),
                        "sha256": hashlib.sha256(b"different").hexdigest(),
                    }
                ],
            }
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr(BACKUP_MANIFEST, json.dumps(manifest))
                handle.writestr("notes/safe.md", body)

            with self.assertRaises(VaultArchiveError):
                restore_vault(archive, vault_dir=Path(tmp) / "vault")
            with self.assertRaises(VaultArchiveError):
                verify_backup(archive)

    def test_restore_rejects_unexpected_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "unexpected.zip"
            body = b"safe"
            manifest = {
                "schema": BACKUP_SCHEMA,
                "files": [
                    {
                        "path": "notes/safe.md",
                        "size": len(body),
                        "sha256": hashlib.sha256(body).hexdigest(),
                    }
                ],
            }
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr(BACKUP_MANIFEST, json.dumps(manifest))
                handle.writestr("notes/safe.md", body)
                handle.writestr("notes/extra.md", "extra")

            with self.assertRaises(VaultArchiveError):
                restore_vault(archive, vault_dir=Path(tmp) / "vault")

    def test_backup_skips_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = _sample_vault(root / "vault")
            try:
                os.symlink(root / "outside.txt", vault / "notes" / "outside.md")
            except OSError:
                self.skipTest("symlink creation is not available")

            result = backup_vault(vault, output_path=root / "vault.zip")

            self.assertEqual(result.skipped_count, 1)
            with zipfile.ZipFile(result.archive_path) as handle:
                self.assertNotIn("notes/outside.md", handle.namelist())

    def test_cli_backup_and_restore_emit_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = _sample_vault(root / "vault")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(["backup", "--vault", str(vault), "--output", str(root / "backup.zip")]),
                    0,
                )
            backup = json.loads(output.getvalue())
            self.assertEqual(backup["file_count"], 3)

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["verify-backup", backup["archive_path"]]), 0)
            verified = json.loads(output.getvalue())
            self.assertTrue(verified["ok"])
            self.assertEqual(verified["file_count"], 3)

            restored = root / "restored"
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(["restore", backup["archive_path"], "--vault", str(restored)]),
                    0,
                )
            restore = json.loads(output.getvalue())
            self.assertEqual(restore["file_count"], 3)
            self.assertTrue((restored / "notes" / "daily.md").exists())


def _sample_vault(path: Path) -> Path:
    vault = ensure_vault(path)
    (vault / "notes" / "daily.md").write_text("# Daily\n", encoding="utf-8")
    (vault / "dashboards" / "daily.html").write_text("<h1>Daily</h1>\n", encoding="utf-8")
    (vault / "images" / "pixel.png").write_bytes(b"png")
    return vault


if __name__ == "__main__":
    unittest.main()
