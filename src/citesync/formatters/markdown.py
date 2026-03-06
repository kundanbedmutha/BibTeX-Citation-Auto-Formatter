"""Convert Publication objects into a human-readable Markdown page."""

from __future__ import annotations

from itertools import groupby

from citesync.models import Publication

DEFAULT_TITLE = "Publications"
UNDATED_LABEL = "Undated"


def format_markdown(
    publications: list[Publication],
    page_title: str = DEFAULT_TITLE,
) -> str:
    """Render publications as a Markdown page, grouped by year (newest first).

    Assumes `publications` is already sorted/deduplicated the way it should
    be displayed (e.g. via `dedup.deduplicate`, which sorts by year desc).
    """
    lines = [f"# {page_title}", ""]

    if not publications:
        lines.append("_No publications found._")
        return "\n".join(lines) + "\n"

    for year, group in groupby(publications, key=lambda p: p.year):
        year_label = str(year) if year is not None else UNDATED_LABEL
        lines.append(f"## {year_label}")
        lines.append("")
        for pub in group:
            lines.append(_format_entry(pub))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _format_entry(pub: Publication) -> str:
    title_text = f"**{pub.title}**"
    if pub.url:
        title_text = f"[{pub.title}]({pub.url})"
        title_text = f"**{title_text}**"

    parts = [f"- {title_text}"]

    detail_bits = []
    if pub.authors:
        detail_bits.append(", ".join(pub.authors))
    if pub.venue:
        detail_bits.append(f"*{pub.venue}*")
    if detail_bits:
        parts.append("  \n  " + ". ".join(detail_bits) + ".")

    if pub.doi:
        parts.append(f"  \n  DOI: [{pub.doi}](https://doi.org/{pub.doi})")

    return "".join(parts)
