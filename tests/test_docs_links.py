import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]+\")?\)")


class DocsLinkTests(unittest.TestCase):
    def test_markdown_local_links_point_to_existing_files(self) -> None:
        missing: list[str] = []
        for path in sorted(ROOT.rglob("*.md")):
            if ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for raw_target in LINK_RE.findall(text):
                parsed = urlparse(raw_target)
                if parsed.scheme or raw_target.startswith("#"):
                    continue
                local = unquote(parsed.path)
                if not local:
                    continue
                target = (path.parent / local).resolve()
                try:
                    target.relative_to(ROOT)
                except ValueError:
                    missing.append(f"{path.relative_to(ROOT)} -> {raw_target} escapes repo")
                    continue
                if not target.exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {raw_target}")

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
