import tempfile
import unittest
from pathlib import Path

from griosai.cli import main


class CliTests(unittest.TestCase):
    def test_add_analysis_imports_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "analysis.json"
            vault = Path(tmp) / "vault"
            payload.write_text(
                '{"title": "Manual Insight", "summary": "No model required"}',
                encoding="utf-8",
            )
            self.assertEqual(
                main(["add-analysis", "--vault", str(vault), "--json-file", str(payload)]),
                0,
            )
            self.assertTrue((vault / "notes" / "manual-insight.md").exists())
            self.assertTrue((vault / "dashboards" / "manual-insight.html").exists())


if __name__ == "__main__":
    unittest.main()
