"""Shared data model for CiteSync.

A `Publication` is the normalized representation every fetcher produces and
every formatter consumes. Fetchers (ORCID, Scholar) are responsible for
mapping their source-specific payloads into this shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceType(str, Enum):
    ORCID = "orcid"
    SCHOLAR = "scholar"
    MANUAL = "manual"


@dataclass
class Publication:
    """Normalized metadata for a single publication."""

    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    pub_type: str | None = None  # e.g. "journal-article", "conference-paper"
    source: SourceType = SourceType.MANUAL
    raw_id: str | None = None  # source-native identifier (ORCID put-code, etc.)

    def cite_key(self) -> str:
        """Generate a BibTeX-style citation key, e.g. `sharma2026citesync`.

        Falls back gracefully when authors/year are missing so callers never
        have to special-case an empty key.
        """
        last_name = "unknown"
        if self.authors:
            first_author = self.authors[0].strip()
            # Handle "Last, First" and "First Last" author formats.
            if "," in first_author:
                last_name = first_author.split(",")[0]
            else:
                last_name = first_author.split()[-1] if first_author.split() else "unknown"
        last_name = "".join(ch for ch in last_name.lower() if ch.isalnum()) or "unknown"

        year_part = str(self.year) if self.year else "nd"

        first_word = "untitled"
        for word in self.title.split():
            cleaned = "".join(ch for ch in word.lower() if ch.isalnum())
            if cleaned:
                first_word = cleaned
                break

        return f"{last_name}{year_part}{first_word}"

    def dedup_key(self) -> str:
        """A normalized key used purely for identifying duplicates across
        sources (DOI when available, else normalized title+year).

        NOT used for display or BibTeX — see `cite_key` for that.
        """
        if self.doi:
            return f"doi:{self.doi.strip().lower()}"
        normalized_title = "".join(ch.lower() for ch in self.title if ch.isalnum())
        return f"title:{normalized_title}:{self.year or ''}"
