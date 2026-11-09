import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from griosai.analysis_schema import (
    analysis_input_schema,
    validate_analysis_payload,
    validation_exit_code,
)
from griosai.cli import main
from griosai.notebook import NotebookConnectorAdapter


class AnalysisSchemaTests(unittest.TestCase):
    def test_valid_analysis_payload_has_no_findings(self) -> None:
        findings = validate_analysis_payload(
            {
                "title": "Schema Smoke",
                "summary": "This is ready to import.",
                "observations": ["one"],
                "actions": ["ship"],
            }
        )

        self.assertEqual(findings, ())
        self.assertEqual(validation_exit_code(findings), 0)

    def test_invalid_analysis_payload_reports_failures(self) -> None:
        findings = validate_analysis_payload(
            {
                "title": "",
                "summary": "ok",
                "observations": [1],
            }
        )
        codes = {finding.code for finding in findings}

        self.assertEqual(validation_exit_code(findings), 1)
        self.assertIn("title-required", codes)
        self.assertIn("title-empty", codes)
        self.assertIn("observations-item-type", codes)

    def test_secret_like_payload_values_are_warnings_only(self) -> None:
        secret = "sk-proj-" + ("D" * 24)
        findings = validate_analysis_payload(
            {
                "title": "Private",
                "summary": f"Keep this local {secret}",
            }
        )

        self.assertEqual(validation_exit_code(findings), 0)
        self.assertIn("secret-looking-key", {finding.code for finding in findings})

    def test_schema_command_prints_contract(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["analysis-schema"]), 0)
        parsed = json.loads(output.getvalue())

        self.assertEqual(parsed, analysis_input_schema())
        self.assertEqual(parsed["x-griosai"]["schema_version"], "griosai.analysis-input.v1")

    def test_validate_analysis_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "analysis.json"
            payload.write_text(
                json.dumps({"title": "CLI Valid", "summary": "ok"}),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(["validate-analysis", "--json-file", str(payload), "--json"]),
                    0,
                )
            parsed = json.loads(output.getvalue())

            self.assertEqual(parsed["summary"]["fail"], 0)
            self.assertEqual(parsed["findings"], [])

    def test_import_rejects_invalid_analysis_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "analysis.json"
            payload.write_text(json.dumps({"title": "Missing summary"}), encoding="utf-8")

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(
                    main(["add-analysis", "--vault", str(Path(tmp) / "vault"), "--json-file", str(payload)]),
                    1,
                )

            self.assertIn("summary-required", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertFalse((Path(tmp) / "vault").exists())

    def test_notebook_adapter_rejects_invalid_mapping_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = NotebookConnectorAdapter(Path(tmp) / "vault")

            with self.assertRaises(ValueError):
                adapter.write_packet({"title": "Missing summary"})


if __name__ == "__main__":
    unittest.main()
