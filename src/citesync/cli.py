"""Command-line interface for CiteSync.

    citesync generate --orcid 0009-0000-XXXX-XXXX --output citations.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from citesync.dedup import deduplicate
from citesync.fetchers.orcid import OrcidFetchError, OrcidFetcher, OrcidValidationError
from citesync.fetchers.scholar import ScholarFetchError, ScholarFetcher
from citesync.formatters.bibtex import format_bibtex
from citesync.formatters.markdown import format_markdown
from citesync.models import Publication


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="citesync",
        description="Generate a formatted citations page from ORCID (and optionally Scholar).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate", help="Fetch publications and write Markdown + BibTeX output."
    )
    generate.add_argument(
        "--orcid",
        metavar="ORCID_ID",
        help="ORCID iD, e.g. 0009-0000-1234-5678 (primary source, recommended).",
    )
    generate.add_argument(
        "--scholar-id",
        metavar="SCHOLAR_USER_ID",
        help=(
            "Google Scholar 'user' query-param id, used as a fallback/supplement. "
            "Fragile — see fetchers/scholar.py for caveats."
        ),
    )
    generate.add_argument(
        "--output",
        "-o",
        required=True,
        metavar="PATH",
        help="Path to write the Markdown citations page to, e.g. citations.md",
    )
    generate.add_argument(
        "--bibtex-output",
        metavar="PATH",
        help="Path to write the .bib file to. Defaults to the --output path with a .bib extension.",
    )
    generate.add_argument(
        "--no-bibtex",
        action="store_true",
        help="Skip writing a BibTeX file; only write the Markdown page.",
    )
    generate.add_argument(
        "--title",
        default="Publications",
        help="Heading for the generated Markdown page (default: 'Publications').",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return _run_generate(args)

    parser.print_help()
    return 1


def _run_generate(args: argparse.Namespace) -> int:
    if not args.orcid and not args.scholar_id:
        print("error: provide at least one of --orcid or --scholar-id", file=sys.stderr)
        return 2

    publications: list[Publication] = []

    if args.orcid:
        try:
            orcid_fetcher = OrcidFetcher(args.orcid)
            fetched = orcid_fetcher.fetch()
            publications.extend(fetched)
            print(f"Fetched {len(fetched)} publication(s) from ORCID ({args.orcid})")
        except OrcidValidationError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        except OrcidFetchError as exc:
            print(f"error fetching from ORCID: {exc}", file=sys.stderr)
            return 1

    if args.scholar_id:
        try:
            scholar_fetcher = ScholarFetcher(args.scholar_id)
            fetched = scholar_fetcher.fetch()
            publications.extend(fetched)
            print(f"Fetched {len(fetched)} publication(s) from Google Scholar (fallback)")
        except ScholarFetchError as exc:
            print(f"warning: Scholar fetch failed, continuing with other sources: {exc}", file=sys.stderr)

    if not publications:
        print("No publications found from any source.", file=sys.stderr)
        return 1

    deduped = deduplicate(publications)
    if len(deduped) != len(publications):
        print(f"Deduplicated {len(publications)} raw record(s) into {len(deduped)} unique publication(s)")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_text = format_markdown(deduped, page_title=args.title)
    output_path.write_text(markdown_text, encoding="utf-8")
    print(f"Wrote Markdown page to {output_path}")

    if not args.no_bibtex:
        bibtex_path = Path(args.bibtex_output) if args.bibtex_output else output_path.with_suffix(".bib")
        bibtex_text = format_bibtex(deduped)
        bibtex_path.parent.mkdir(parents=True, exist_ok=True)
        bibtex_path.write_text(bibtex_text, encoding="utf-8")
        print(f"Wrote BibTeX file to {bibtex_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
