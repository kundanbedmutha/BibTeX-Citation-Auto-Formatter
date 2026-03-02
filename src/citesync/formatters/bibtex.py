"""Convert Publication objects into BibTeX entries."""

from __future__ import annotations

from citesync.models import Publication

# Map ORCID/CiteSync pub_type strings to BibTeX entry types. Anything not
# listed here falls back to "misc" rather than raising, since ORCID's type
# vocabulary is broader than BibTeX's and new types shouldn't break output.
_ENTRY_TYPE_MAP = {
    "journal-article": "article",
    "conference-paper": "inproceedings",
    "conference-abstract": "inproceedings",
    "book": "book",
    "book-chapter": "incollection",
    "preprint": "unpublished",
    "dissertation-thesis": "phdthesis",
    "report": "techreport",
}

_FIELDS_NEEDING_ESCAPE = {"&", "%", "$", "#", "_", "{", "}"}


def format_bibtex(publications: list[Publication]) -> str:
    """Render a list of publications as a BibTeX (.bib) document."""
    entries = [_format_entry(pub) for pub in publications]
    return "\n\n".join(entries) + "\n" if entries else ""


def _format_entry(pub: Publication) -> str:
    entry_type = _ENTRY_TYPE_MAP.get(pub.pub_type or "", "misc")
    key = pub.cite_key()

    fields: list[tuple[str, str]] = []
    fields.append(("title", _escape(pub.title)))

    if pub.authors:
        fields.append(("author", _escape(" and ".join(pub.authors))))

    if pub.year:
        fields.append(("year", str(pub.year)))

    if pub.venue:
        venue_field = "journal" if entry_type == "article" else "booktitle"
        fields.append((venue_field, _escape(pub.venue)))

    if pub.doi:
        fields.append(("doi", pub.doi))

    if pub.url:
        fields.append(("url", pub.url))

    field_lines = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields)
    return f"@{entry_type}{{{key},\n{field_lines}\n}}"


def _escape(text: str) -> str:
    """Escape characters BibTeX treats specially.

    Deliberately conservative: this handles the common cases (ampersands,
    percent signs, underscores in titles) without trying to be a full LaTeX
    encoder, since publication metadata is rarely more exotic than that.
    """
    result = text
    for char in _FIELDS_NEEDING_ESCAPE:
        result = result.replace(char, f"\\{char}")
    return result
