import tempfile
import unittest
from pathlib import Path

from griosai.brain import AnalysisRecord, ensure_vault, list_notes, safe_child, slugify, write_analysis_note


class BrainTests(unittest.TestCase):
    def test_ensure_vault_creates_expected_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            for name in ("notes", "dashboards", "images", "inbox", "lineage", "notebook-packets"):
                self.assertTrue((vault / name).is_dir())

    def test_safe_child_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            with self.assertRaises(ValueError):
                safe_child(vault, "..", "outside.txt")

    def test_slugify_handles_empty_and_unsafe_text(self) -> None:
        self.assertEqual(slugify("GriosAI Phase 0!"), "griosai-phase-0")
        self.assertEqual(slugify("../../"), "analysis")

    def test_write_analysis_note_and_list_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = AnalysisRecord(
                title="Private Dashboard",
                summary="Local only",
                observations=["No cloud"],
                actions=["Serve on localhost"],
            )
            path = write_analysis_note(Path(tmp), record)
            self.assertEqual(path.name, "private-dashboard.md")
            notes = list_notes(Path(tmp))
            self.assertEqual(notes[0]["title"], "Private Dashboard")
            self.assertNotIn("path", notes[0])

    def test_repeated_note_titles_do_not_clobber(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = AnalysisRecord(title="Same Title", summary="One")
            first = write_analysis_note(Path(tmp), record)
            second = write_analysis_note(Path(tmp), record)
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_markdown_escapes_html_and_frontmatter_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_analysis_note(
                Path(tmp),
                AnalysisRecord(
                    title="Bad\nTitle <script>",
                    summary="<b>unsafe</b>",
                    observations=["``` fence"],
                    actions=["<img src=x>"],
                    raw={"payload": "```"},
                ),
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn('title: "Bad Title <script>"', text)
            self.assertIn("&lt;b&gt;unsafe&lt;/b&gt;", text)
            self.assertIn("&lt;img src=x&gt;", text)
            self.assertIn("````json", text)


if __name__ == "__main__":
    unittest.main()
