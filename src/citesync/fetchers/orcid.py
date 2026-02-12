"""Fetcher for the ORCID public API (v3.0).

This is CiteSync's primary source: ORCID's public API is stable, documented,
requires no auth for public records, and returns structured JSON. Compare
with `scholar.py`, which scrapes an HTML page with no API contract at all.

API shape (relevant bits):

1. GET /v3.0/{orcid-id}/works
   -> list of "groups"; each group represents one logical work that may be
      registered by multiple sources. We take the first work-summary in each
      group as the canonical entry and grab its put-code.

2. GET /v3.0/{orcid-id}/works/{put-code-1},{put-code-2},...
   -> "bulk" endpoint returning full work records (including contributors/
      authors) for the given put-codes, batched to avoid overly long URLs.

Docs: https://info.orcid.org/documentation/api-tutorials/api-tutorial-read-data-on-a-record/
"""

from __future__ import annotations

import re

import requests

from citesync.fetchers.base import Fetcher
from citesync.models import Publication, SourceType

ORCID_API_BASE = "https://pub.orcid.org/v3.0"
DEFAULT_HEADERS = {"Accept": "application/json"}
BULK_BATCH_SIZE = 50  # ORCID recommends keeping bulk requests reasonably sized
REQUEST_TIMEOUT_SECONDS = 15

_ORCID_ID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


class OrcidValidationError(ValueError):
    """Raised when an ORCID iD is malformed before any network call is made."""


class OrcidFetchError(RuntimeError):
    """Raised when the ORCID API returns an error or unexpected payload."""


def validate_orcid_id(orcid_id: str) -> None:
    if not _ORCID_ID_PATTERN.match(orcid_id):
        raise OrcidValidationError(
            f"'{orcid_id}' doesn't look like a valid ORCID iD "
            "(expected format: 0000-0000-0000-0000)"
        )


class OrcidFetcher(Fetcher):
    """Fetches and normalizes publications from a single ORCID record."""

    def __init__(
        self,
        orcid_id: str,
        session: requests.Session | None = None,
        api_base: str = ORCID_API_BASE,
    ) -> None:
        validate_orcid_id(orcid_id)
        self.orcid_id = orcid_id
        self.session = session or requests.Session()
        self.api_base = api_base

    def fetch(self) -> list[Publication]:
        put_codes = self._fetch_put_codes()
        if not put_codes:
            return []

        publications: list[Publication] = []
        for batch in _chunk(put_codes, BULK_BATCH_SIZE):
            bulk_payload = self._fetch_bulk_works(batch)
            for entry in bulk_payload.get("bulk", []):
                work = entry.get("work")
                if work is None:
                    # ORCID returns an "error" object instead of "work" for
                    # put-codes it couldn't resolve (e.g. deleted since the
                    # summary call). Skip rather than fail the whole batch.
                    continue
                pub = self._parse_work(work)
                if pub is not None:
                    publications.append(pub)

        return publications

    def _fetch_put_codes(self) -> list[str]:
        url = f"{self.api_base}/{self.orcid_id}/works"
        payload = self._get_json(url)

        put_codes: list[str] = []
        for group in payload.get("group", []):
            summaries = group.get("work-summary", [])
            if not summaries:
                continue
            # Each group may list the same work as reported by several
            # sources; the first summary is a representative, canonical pick.
            put_code = summaries[0].get("put-code")
            if put_code is not None:
                put_codes.append(str(put_code))

        return put_codes

    def _fetch_bulk_works(self, put_codes: list[str]) -> dict:
        codes_param = ",".join(put_codes)
        url = f"{self.api_base}/{self.orcid_id}/works/{codes_param}"
        return self._get_json(url)

    def _get_json(self, url: str) -> dict:
        try:
            response = self.session.get(
                url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            raise OrcidFetchError(f"Network error calling ORCID API: {exc}") from exc

        if response.status_code == 404:
            raise OrcidFetchError(
                f"ORCID record not found (404) for id in URL: {url}"
            )
        if not response.ok:
            raise OrcidFetchError(
                f"ORCID API returned {response.status_code} for {url}: {response.text[:300]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise OrcidFetchError(f"ORCID API returned non-JSON payload from {url}") from exc

    def _parse_work(self, work: dict) -> Publication | None:
        title = _dig(work, "title", "title", "value")
        if not title:
            return None  # A work with no title isn't usable in any format.

        year_str = _dig(work, "publication-date", "year", "value")
        year = int(year_str) if year_str and year_str.isdigit() else None

        venue = _dig(work, "journal-title", "value")

        doi = None
        url = None
        for ext_id in _dig(work, "external-ids", "external-id") or []:
            id_type = (ext_id.get("external-id-type") or "").lower()
            id_value = ext_id.get("external-id-value")
            id_url = _dig(ext_id, "external-id-url", "value")
            if id_type == "doi" and id_value:
                doi = id_value
            if url is None and id_url:
                url = id_url

        if url is None and doi:
            url = f"https://doi.org/{doi}"

        authors: list[str] = []
        for contributor in _dig(work, "contributors", "contributor") or []:
            credit_name = _dig(contributor, "credit-name", "value")
            if credit_name:
                authors.append(credit_name)

        return Publication(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            pub_type=work.get("type"),
            source=SourceType.ORCID,
            raw_id=str(work.get("put-code")) if work.get("put-code") is not None else None,
        )


def _dig(obj: dict | None, *keys: str):
    """Safely walk a chain of dict lookups, returning None on any miss.

    ORCID payloads are deeply nested with many optional fields, so this
    avoids a wall of `.get(...) or {}` chains at every call site.
    """
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
