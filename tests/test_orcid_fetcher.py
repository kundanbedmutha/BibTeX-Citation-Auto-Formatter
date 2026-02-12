import json
from pathlib import Path

import pytest
import responses

from citesync.fetchers.orcid import (
    ORCID_API_BASE,
    OrcidFetcher,
    OrcidFetchError,
    OrcidValidationError,
)
from citesync.models import SourceType

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ORCID_ID = "0009-0000-1234-5678"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@responses.activate
def test_fetch_returns_normalized_publications():
    responses.add(
        responses.GET,
        f"{ORCID_API_BASE}/{ORCID_ID}/works",
        json=_load_fixture("orcid_works_summary.json"),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{ORCID_API_BASE}/{ORCID_ID}/works/111111,222222,333333",
        json=_load_fixture("orcid_works_bulk.json"),
        status=200,
    )

    fetcher = OrcidFetcher(ORCID_ID)
    pubs = fetcher.fetch()

    assert len(pubs) == 3
    hqc = next(p for p in pubs if "HQC-Orch" in p.title)
    assert hqc.year == 2026
    assert hqc.venue == "IEEE Access"
    assert hqc.doi == "10.1109/access.2026.1111111"
    assert hqc.url == "https://doi.org/10.1109/access.2026.1111111"
    assert hqc.authors == ["Kundan Sharma", "A. Researcher"]
    assert hqc.pub_type == "journal-article"
    assert hqc.source == SourceType.ORCID
    assert hqc.raw_id == "111111"


@responses.activate
def test_fetch_handles_missing_contributors_gracefully():
    responses.add(
        responses.GET,
        f"{ORCID_API_BASE}/{ORCID_ID}/works",
        json=_load_fixture("orcid_works_summary.json"),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{ORCID_API_BASE}/{ORCID_ID}/works/111111,222222,333333",
        json=_load_fixture("orcid_works_bulk.json"),
        status=200,
    )

    fetcher = OrcidFetcher(ORCID_ID)
    pubs = fetcher.fetch()

    no_contrib = next(p for p in pubs if "No Contributors" in p.title)
    assert no_contrib.authors == []
    assert no_contrib.venue is None


@responses.activate
def test_fetch_skips_bulk_entries_with_error_instead_of_work():
    summary = {
        "group": [
            {"work-summary": [{"put-code": 1, "title": {"title": {"value": "Ok"}}}]},
            {"work-summary": [{"put-code": 2, "title": {"title": {"value": "Deleted"}}}]},
        ]
    }
    bulk = {
        "bulk": [
            {
                "work": {
                    "put-code": 1,
                    "type": "journal-article",
                    "title": {"title": {"value": "Ok"}},
                    "publication-date": {"year": {"value": "2023"}},
                    "external-ids": {"external-id": []},
                }
            },
            {"error": {"response-code": "404", "developer-message": "Work not found"}},
        ]
    }
    responses.add(responses.GET, f"{ORCID_API_BASE}/{ORCID_ID}/works", json=summary, status=200)
    responses.add(
        responses.GET, f"{ORCID_API_BASE}/{ORCID_ID}/works/1,2", json=bulk, status=200
    )

    pubs = OrcidFetcher(ORCID_ID).fetch()
    assert len(pubs) == 1
    assert pubs[0].title == "Ok"


@responses.activate
def test_fetch_returns_empty_list_when_no_works():
    responses.add(
        responses.GET,
        f"{ORCID_API_BASE}/{ORCID_ID}/works",
        json={"group": []},
        status=200,
    )
    pubs = OrcidFetcher(ORCID_ID).fetch()
    assert pubs == []


@responses.activate
def test_fetch_raises_on_404():
    responses.add(
        responses.GET,
        f"{ORCID_API_BASE}/{ORCID_ID}/works",
        json={"response-code": 404},
        status=404,
    )
    with pytest.raises(OrcidFetchError):
        OrcidFetcher(ORCID_ID).fetch()


@responses.activate
def test_fetch_raises_on_server_error():
    responses.add(
        responses.GET,
        f"{ORCID_API_BASE}/{ORCID_ID}/works",
        body="Internal Server Error",
        status=500,
    )
    with pytest.raises(OrcidFetchError):
        OrcidFetcher(ORCID_ID).fetch()


@pytest.mark.parametrize(
    "bad_id",
    ["not-an-orcid", "0009-0000-1234", "0009000012345678", ""],
)
def test_invalid_orcid_id_rejected_before_any_network_call(bad_id):
    with pytest.raises(OrcidValidationError):
        OrcidFetcher(bad_id)


def test_valid_orcid_id_with_x_checksum_accepted():
    # ORCID's last character can be 'X' as a checksum digit.
    fetcher = OrcidFetcher("0000-0002-1825-009X")
    assert fetcher.orcid_id == "0000-0002-1825-009X"
