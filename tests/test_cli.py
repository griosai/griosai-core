import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from griosai.brain import AnalysisRecord, ensure_vault
from griosai.cli import main
from griosai.lineage import analysis_id


class CliTests(unittest.TestCase):
    def test_add_analysis_imports_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "analysis.json"
            vault = Path(tmp) / "vault"
            payload_data = {"title": "Manual Insight", "summary": "No model required"}
            payload.write_text(json.dumps(payload_data), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["add-analysis", "--vault", str(vault), "--json-file", str(payload)]),
                    0,
                )
            self.assertTrue((vault / "notes" / "manual-insight.md").exists())
            self.assertTrue((vault / "dashboards" / "manual-insight.html").exists())
            expected_id = analysis_id(
                AnalysisRecord.from_mapping(payload_data, model="manual")
            )
            expected_lineage = f"analysis-{expected_id[:12]}.json"
            self.assertTrue((vault / "lineage" / expected_lineage).exists())

    def test_credential_lease_cli_redacts_token(self) -> None:
        with patch.dict(os.environ, {"SERVICE_TOKEN": "super-" + "secret-token"}):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "credential-lease",
                            "--secret-name",
                            "service",
                            "--env-var",
                            "SERVICE_TOKEN",
                            "--scope",
                            "service:read",
                        ]
                    ),
                    0,
                )

        parsed = json.loads(output.getvalue())
        self.assertEqual(parsed["token"], "[redacted]")
        self.assertNotIn("super-" + "secret-token", output.getvalue())

    def test_doctor_cli_returns_zero_for_safe_temp_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".gitignore").write_text("GriosAI-vault/\nprivate/\n*.token\n", encoding="utf-8")
            (repo / ".env.example").write_text("GRIOSAI_API_TOKEN=\n", encoding="utf-8")
            vault = ensure_vault(Path(tmp) / "vault")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(["doctor", "--vault", str(vault), "--repo", str(repo), "--json"]),
                    0,
                )
            self.assertEqual(json.loads(output.getvalue())["summary"]["fail"], 0)

    def test_cli_expected_errors_are_concise_without_traceback(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["add-analysis", "--vault", "/tmp/griosai-vault", "--json-file", "/no/such/file.json"])

        self.assertEqual(code, 1)
        self.assertIn("error:", stderr.getvalue())
        self.assertIn("No such file", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
