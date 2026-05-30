from __future__ import annotations

from html import escape
from pathlib import Path

from .brain import AnalysisRecord, ensure_vault, safe_child, slugify, unique_path


def render_dashboard(record: AnalysisRecord) -> str:
    title = escape(record.title)
    summary = escape(record.summary or "No summary captured yet.")
    observations = _render_list(record.observations)
    actions = _render_list(record.actions)
    model = escape(record.model)
    created_at = escape(record.created_at)
    source = escape(record.source_image or "No image recorded")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none';">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f7f7f2;
      --ink: #171717;
      --muted: #5b605c;
      --line: #d8d8d0;
      --panel: #ffffff;
      --accent: #176b87;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #111312;
        --ink: #f2f1ea;
        --muted: #b8bbb4;
        --line: #30342f;
        --panel: #191c1a;
        --accent: #6ec6df;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    main {{
      width: min(940px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 42px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 22px;
    }}
    h1 {{
      font-size: clamp(1.8rem, 4vw, 3.4rem);
      line-height: 1.05;
      margin: 0 0 12px;
      letter-spacing: 0;
    }}
    .summary {{
      color: var(--muted);
      font-size: 1.06rem;
      margin: 0;
      max-width: 72ch;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }}
    .meta span {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 5px 8px;
      color: var(--muted);
      font-size: .86rem;
      max-width: 100%;
      overflow-wrap: anywhere;
    }}
    section {{
      border-bottom: 1px solid var(--line);
      padding: 18px 0;
    }}
    h2 {{
      color: var(--accent);
      font-size: 1rem;
      margin: 0 0 10px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    ul {{
      margin: 0;
      padding-left: 1.2rem;
    }}
    li + li {{
      margin-top: 8px;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <p class="summary">{summary}</p>
      <div class="meta">
        <span>Model: {model}</span>
        <span>Created: {created_at}</span>
        <span>Source: {source}</span>
      </div>
    </header>
    <section>
      <h2>Observations</h2>
      {observations}
    </section>
    <section>
      <h2>Actions</h2>
      {actions}
    </section>
  </main>
</body>
</html>
"""


def write_dashboard(
    vault_dir: Path,
    record: AnalysisRecord,
    *,
    slug: str | None = None,
) -> Path:
    vault = ensure_vault(vault_dir)
    dashboard_slug = slugify(slug or record.title)
    path = unique_path(safe_child(vault, "dashboards", f"{dashboard_slug}.html"))
    path.write_text(render_dashboard(record), encoding="utf-8")
    return path


def list_dashboards(vault_dir: Path) -> list[dict[str, str]]:
    dashboards_dir = safe_child(ensure_vault(vault_dir), "dashboards")
    dashboards: list[dict[str, str]] = []
    for path in sorted(dashboards_dir.glob("*.html"), key=lambda item: item.stat().st_mtime, reverse=True):
        dashboards.append(
            {
                "name": path.name,
                "url": f"/dashboards/{path.name}",
            }
        )
    return dashboards


def _render_list(items: list[str]) -> str:
    safe_items = [escape(item) for item in items if item.strip()]
    if not safe_items:
        return "<p>No items captured yet.</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in safe_items) + "</ul>"
