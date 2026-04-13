"""CLI entry point for markdown-to-confluence."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from .confluence_api import ConfluenceClient
from .converter import MarkdownToConfluenceConverter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markdown-to-confluence",
        description=(
            "Convert markdown files (including mermaid diagrams) to Confluence pages. "
            "Credentials can be supplied via CLI flags or environment variables "
            "(CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY)."
        ),
    )

    # --- Input ---
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Markdown file(s) to convert and publish.",
    )

    # --- Confluence connection ---
    parser.add_argument(
        "--url",
        default=os.getenv("CONFLUENCE_URL", ""),
        help="Confluence base URL (e.g. https://myorg.atlassian.net/wiki).",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("CONFLUENCE_USERNAME", ""),
        help="Atlassian account email address.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("CONFLUENCE_API_TOKEN", ""),
        help="Atlassian API token.",
    )
    parser.add_argument(
        "--space",
        default=os.getenv("CONFLUENCE_SPACE_KEY", ""),
        help="Confluence space key.",
    )

    # --- Page structure ---
    parser.add_argument(
        "--parent-id",
        default=os.getenv("CONFLUENCE_PARENT_ID", ""),
        metavar="PAGE_ID",
        help="ID of the parent page. New pages are created as children.",
    )
    parser.add_argument(
        "--sections",
        action="store_true",
        help=(
            "Combine all input files into a single Confluence page "
            "where each file is an expandable section."
        ),
    )
    parser.add_argument(
        "--title",
        default="",
        help="Override the page title (useful with --sections).",
    )

    # --- Mermaid ---
    parser.add_argument(
        "--mermaid-output-dir",
        default="",
        metavar="DIR",
        help="Directory where generated mermaid PNG images are saved.",
    )
    parser.add_argument(
        "--no-local-mermaid",
        action="store_true",
        help="Skip the local mermaid CLI (mmdc) and use mermaid.ink URLs instead.",
    )

    # --- Dry run ---
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Convert markdown but do not publish to Confluence. Print storage XML to stdout.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    # ---- validate inputs ----
    for f in args.files:
        if not Path(f).is_file():
            print(f"ERROR: File not found: {f}", file=sys.stderr)
            return 1

    mermaid_dir = args.mermaid_output_dir or tempfile.mkdtemp(prefix="mermaid_")

    converter = MarkdownToConfluenceConverter(
        mermaid_output_dir=mermaid_dir,
        use_local_mermaid_cli=not args.no_local_mermaid,
    )

    # ---- convert ----
    if args.sections:
        result = converter.convert_files_as_sections(args.files)
    elif len(args.files) == 1:
        result = converter.convert_file(args.files[0])
    else:
        # Multiple files without --sections: convert each separately
        results = [converter.convert_file(f) for f in args.files]

        if args.dry_run:
            for r in results:
                print(f"=== {r.title} ===")
                print(r.body)
                print()
            return 0

        if not all([args.url, args.username, args.token, args.space]):
            print(
                "ERROR: --url, --username, --token, and --space are required when publishing.",
                file=sys.stderr,
            )
            return 1

        client = ConfluenceClient(args.url, args.username, args.token, args.space)
        parent_id = args.parent_id or None

        for r in results:
            title = r.title
            page = client.upsert_page(title, r.body, parent_id=parent_id)
            page_id = page.get("id")
            print(f"Published: {title} (id={page_id})")
            for attachment in r.attachments:
                client.upload_attachment(page_id, attachment)
                print(f"  Attached: {os.path.basename(attachment)}")

        return 0

    if args.dry_run:
        title = args.title or result.title
        print(f"=== {title} ===")
        print(result.body)
        return 0

    if not all([args.url, args.username, args.token, args.space]):
        print(
            "ERROR: --url, --username, --token, and --space are required when publishing.",
            file=sys.stderr,
        )
        return 1

    title = args.title or result.title
    client = ConfluenceClient(args.url, args.username, args.token, args.space)
    parent_id = args.parent_id or None

    page = client.upsert_page(title, result.body, parent_id=parent_id)
    page_id = page.get("id")
    print(f"Published: {title} (id={page_id})")

    for attachment in result.attachments:
        client.upload_attachment(page_id, attachment)
        print(f"  Attached: {os.path.basename(attachment)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
