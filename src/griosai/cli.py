from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .brain import AnalysisRecord, ensure_vault, slugify, write_analysis_note
from .config import GriosConfig
from .dashboard import write_dashboard
from .ollama_client import DEFAULT_IMAGE_PROMPT, analyze_image
from .server import create_sample, run_server


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        vault = ensure_vault(Path(args.vault))
        print(f"Initialized GriosAI vault at {vault}")
        return 0
    if args.command == "sample":
        note, dashboard = create_sample(Path(args.vault))
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        return 0
    if args.command == "analyze-image":
        config = GriosConfig.from_env(
            vault_dir=args.vault,
            ollama_url=args.ollama_url,
            vision_model=args.model,
        )
        record = analyze_image(
            Path(args.image),
            model=config.vision_model,
            ollama_url=config.ollama_url,
            prompt=args.prompt,
        )
        slug = slugify(args.slug or record.title)
        note = write_analysis_note(config.vault_dir, record, slug=slug)
        dashboard = write_dashboard(config.vault_dir, record, slug=slug)
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        return 0
    if args.command == "add-analysis":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        slug = slugify(args.slug or record.title)
        note = write_analysis_note(Path(args.vault), record, slug=slug)
        dashboard = write_dashboard(Path(args.vault), record, slug=slug)
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        return 0
    if args.command == "serve":
        config = GriosConfig.from_env(
            vault_dir=args.vault,
            host=args.host,
            port=args.port,
            ollama_url=args.ollama_url,
            vision_model=args.model,
            api_token=args.api_token,
            allowed_hosts=tuple(args.allow_host),
        )
        run_server(config)
        return 0
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="griosai")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create the local vault layout")
    init.add_argument("--vault", required=True, help="Vault directory")

    sample = subparsers.add_parser("sample", help="Write a sample dashboard")
    sample.add_argument("--vault", required=True, help="Vault directory")

    analyze = subparsers.add_parser("analyze-image", help="Analyze an image through local Ollama")
    analyze.add_argument("image", help="Image path")
    analyze.add_argument("--vault", required=True, help="Vault directory")
    analyze.add_argument("--model", default=None, help="Ollama vision model")
    analyze.add_argument("--ollama-url", default=None, help="Ollama base URL")
    analyze.add_argument("--prompt", default=DEFAULT_IMAGE_PROMPT, help="Vision prompt")
    analyze.add_argument("--slug", default=None, help="Output slug")

    add_analysis = subparsers.add_parser("add-analysis", help="Import manual analysis JSON")
    add_analysis.add_argument("--vault", required=True, help="Vault directory")
    add_analysis.add_argument(
        "--json-file",
        default="-",
        help="JSON file to import, or '-' for stdin",
    )
    add_analysis.add_argument("--slug", default=None, help="Output slug")

    serve = subparsers.add_parser("serve", help="Run the local dashboard server")
    serve.add_argument("--vault", required=True, help="Vault directory")
    serve.add_argument("--host", default=None, help="Bind host; defaults to 127.0.0.1")
    serve.add_argument("--port", type=int, default=None, help="Bind port; defaults to 8765")
    serve.add_argument("--model", default=None, help="Ollama vision model")
    serve.add_argument("--ollama-url", default=None, help="Ollama base URL")
    serve.add_argument("--api-token", default=None, help="Bearer token for mutation APIs")
    serve.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="Additional allowed Host/Origin hostname for private proxies",
    )

    return parser


def _load_json_payload(path: str) -> dict[str, object]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("analysis JSON must be an object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
