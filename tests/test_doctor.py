import json
import tempfile
import unittest
from pathlib import Path

from griosai.brain import ensure_vault
from griosai.doctor import doctor_exit_code, format_doctor_json, run_doctor


class DoctorTests(unittest.TestCase):
    def test_doctor_passes_safe_repo_and_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            (repo / ".gitignore").write_text("GriosAI-vault/\nprivate/\n*.token\n", encoding="utf-8")
            (repo / ".env.example").write_text("GRIOSAI_API_TOKEN=\n", encoding="utf-8")
            vault = ensure_vault(root / "vault")

            checks = run_doctor(
                repo_dir=repo,
                vault_dir=vault,
                environ={"GRIOSAI_HOST": "127.0.0.1", "GRIOSAI_OBSIDIAN_URL": "https://127.0.0.1:27124"},
            )
            self.assertEqual(doctor_exit_code(checks), 0)
            self.assertFalse([check for check in checks if check.status == "fail"])
            parsed = json.loads(format_doctor_json(checks))
            self.assertGreater(parsed["summary"]["pass"], 0)

    def test_doctor_fails_unsafe_config_and_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            (repo / ".gitignore").write_text("", encoding="utf-8")
            (repo / ".env.example").write_text("TOKEN=abcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")
            vault = ensure_vault(root / "vault")
            packet = vault / "notebook-packets" / "bad"
            packet.mkdir(parents=True)
            fake_token = "abcdefghijklmnopqrstuvwxyz"
            (packet / "index.md").write_text(f"Bearer {fake_token}", encoding="utf-8")

            checks = run_doctor(
                repo_dir=repo,
                vault_dir=vault,
                environ={
                    "GRIOSAI_HOST": "0.0.0.0",
                    "GRIOSAI_API_TOKEN": "short",
                    "GRIOSAI_OBSIDIAN_URL": "https://example.com",
                    "GRIOSAI_MLFLOW_TRACKING_URI": "http://mlflow-tracking:5000",
                },
            )
            self.assertEqual(doctor_exit_code(checks), 1)
            self.assertTrue(any(check.name == "obsidian-url" and check.status == "fail" for check in checks))
            self.assertTrue(any(check.name == "mlflow-tracking-uri" and check.status == "fail" for check in checks))
            self.assertTrue(any(check.name == "notebook-packets" and check.status == "fail" for check in checks))

    def test_doctor_warns_when_remote_mlflow_is_explicit(self) -> None:
        checks = run_doctor(
            environ={
                "GRIOSAI_HOST": "127.0.0.1",
                "GRIOSAI_OBSIDIAN_URL": "https://127.0.0.1:27124",
                "GRIOSAI_MLFLOW_TRACKING_URI": "http://mlflow-tracking:5000",
                "GRIOSAI_MLFLOW_ALLOW_REMOTE": "true",
            }
        )

        self.assertEqual(doctor_exit_code(checks), 0)
        self.assertTrue(
            any(check.name == "mlflow-tracking-uri" and check.status == "warn" for check in checks)
        )


if __name__ == "__main__":
    unittest.main()
