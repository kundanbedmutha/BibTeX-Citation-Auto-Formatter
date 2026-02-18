"""Fallback fetcher that scrapes a public Google Scholar profile page.

READ THIS BEFORE USING THIS MODULE.

Google Scholar has no public API. This fetcher works by parsing the HTML of
a public profile page, which means:

  - It WILL break whenever Google changes their markup. No SLA, no versioning.
  - Scholar actively rate-limits and sometimes CAPTCHAs scripted requests.
    Hitting it repeatedly/on a schedule (e.g. CI, cron) is likely to get you
    blocked.
  - Author lists on Scholar are often truncated ("A Sharma, B Lee... ") and
    venues/years are sometimes approximate.
  - This may be against Google Scholar's Terms of Service depending on your
    use — you're responsible for checking that for your situation.

Use ORCID (`fetchers/orcid.py`) whenever possible. Use this module only:
  - as a one-off supplement for publications not yet registered on ORCID, or
  - when you don't have an ORCID iD to work with at all.

This fetcher is deliberately NOT wired into the CLI's default path — it
requires an explicit `--scholar-id` flag (see `cli.py`) precisely so nobody
depends on it unknowingly.
"""

from __future__ import annotations

import re

import requests

from citesync.fetchers.base import Fetcher
from citesync.models import Publication, SourceType

SCHOLAR_PROFILE_URL = "https://scholar.google.com/citations"
REQUEST_TIMEOUT_SECONDS = 15
DEFAULT_HEADERS = {
    # A plain, honest UA. We don't try to impersonate a browser to dodge
    # blocking — if Scholar blocks scripted access, that's a signal to fall
    # back to ORCID or manual entry, not to fight harder.
    "User-Agent": "CiteSync/0.1 (fallback fetcher; see fetchers/scholar.py)"
}

_ROW_PATTERN = re.compile(
    r'<tr class="gsc_a_tr">.*?class="gsc_a_at"[^>]*>(?P<title>.*?)</a>'
    r'.*?class="gsc_a_h gsc_a_hc gs_ibl">(?P<year>\d{4})?</span>',
    re.DOTALL,
)
_TAG_STRIP_PATTERN = re.compile(r"<[^>]+>")


class ScholarFetchError(RuntimeError):
    pass


class ScholarFetcher(Fetcher):
    """Best-effort scraper for a public Google Scholar author page.

    Only extracts title + year reliably; author/venue extraction from the
    profile list view is too unreliable to trust for BibTeX output, so those
    fields are left None and the caller/formatter should treat entries from
    this source as needing manual review.
    """

    def __init__(
        self,
        scholar_user_id: str,
        session: requests.Session | None = None,
    ) -> None:
        self.scholar_user_id = scholar_user_id
        self.session = session or requests.Session()

    def fetch(self) -> list[Publication]:
        html = self._fetch_html()
        publications: list[Publication] = []
        for match in _ROW_PATTERN.finditer(html):
            raw_title = match.group("title")
            title = _TAG_STRIP_PATTERN.sub("", raw_title).strip()
            if not title:
                continue
            year_str = match.group("year")
            publications.append(
                Publication(
                    title=title,
                    authors=[],
                    year=int(year_str) if year_str else None,
                    venue=None,
                    doi=None,
                    url=None,
                    pub_type=None,
                    source=SourceType.SCHOLAR,
                    raw_id=None,
                )
            )
        return publications

    def _fetch_html(self) -> str:
        params = {"user": self.scholar_user_id, "hl": "en", "sortby": "pubdate"}
        try:
            response = self.session.get(
                SCHOLAR_PROFILE_URL,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise ScholarFetchError(f"Network error calling Google Scholar: {exc}") from exc

        if not response.ok:
            raise ScholarFetchError(
                f"Google Scholar returned {response.status_code}. This scraper is "
                "fragile by design (see module docstring) — consider using ORCID "
                "instead, or check whether Scholar is rate-limiting/blocking you."
            )
        return response.text
