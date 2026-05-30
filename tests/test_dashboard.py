import tempfile
import unittest
from pathlib import Path

from griosai.brain import AnalysisRecord
from griosai.dashboard import list_dashboards, render_dashboard, write_dashboard
from griosai.server import _resolve_api_image_path


class DashboardTests(unittest.TestCase):
    def test_dashboard_escapes_model_content(self) -> None:
        html = render_dashboard(
            AnalysisRecord(
                title="<script>alert(1)</script>",
                summary="Summary <b>bold</b>",
                observations=["<img src=x onerror=alert(1)>"],
                actions=["Use localhost"],
            )
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)

    def test_write_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_dashboard(
                Path(tmp),
                AnalysisRecord(title="Phase 0", summary="Works"),
            )
            self.assertTrue(path.exists())
            self.assertEqual(path.name, "phase-0.html")
            dashboards = list_dashboards(Path(tmp))
            self.assertEqual(dashboards[0]["url"], "/dashboards/phase-0.html")
            self.assertNotIn("path", dashboards[0])

    def test_rest_image_path_must_stay_in_vault_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            image = vault / "images" / "sample.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"fake")
            self.assertEqual(_resolve_api_image_path(vault, str(image)), image.resolve())
            with self.assertRaises(ValueError):
                _resolve_api_image_path(vault, str(Path(tmp) / "outside.png"))


if __name__ == "__main__":
    unittest.main()
