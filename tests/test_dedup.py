from citesync.dedup import deduplicate
from citesync.models import Publication, SourceType


def test_no_duplicates_returns_all_sorted_by_year_desc():
    pubs = [
        Publication(title="Older Paper", year=2023, source=SourceType.ORCID),
        Publication(title="Newer Paper", year=2026, source=SourceType.ORCID),
    ]
    result = deduplicate(pubs)
    assert [p.title for p in result] == ["Newer Paper", "Older Paper"]


def test_same_doi_across_sources_merges_into_one():
    orcid_pub = Publication(
        title="HQC-Orch",
        year=2026,
        doi="10.1109/access.2026.1111111",
        authors=["Kundan Sharma", "A. Researcher"],
        venue="IEEE Access",
        source=SourceType.ORCID,
    )
    scholar_pub = Publication(
        title="HQC-Orch",
        year=2026,
        doi="10.1109/access.2026.1111111",
        authors=[],
        venue=None,
        source=SourceType.SCHOLAR,
    )
    result = deduplicate([orcid_pub, scholar_pub])
    assert len(result) == 1
    assert result[0].source == SourceType.ORCID
    assert result[0].authors == ["Kundan Sharma", "A. Researcher"]


def test_orcid_fills_gaps_from_scholar_record():
    # ORCID record missing a venue; Scholar happens to have one.
    orcid_pub = Publication(
        title="FALCON",
        year=2025,
        doi="10.1000/falcon",
        venue=None,
        source=SourceType.ORCID,
    )
    scholar_pub = Publication(
        title="FALCON",
        year=2025,
        doi="10.1000/falcon",
        venue="ICCMSE 2025 Proceedings",
        source=SourceType.SCHOLAR,
    )
    result = deduplicate([orcid_pub, scholar_pub])
    assert len(result) == 1
    assert result[0].venue == "ICCMSE 2025 Proceedings"
    assert result[0].source == SourceType.ORCID  # base identity still ORCID


def test_no_doi_falls_back_to_normalized_title_and_year():
    pub_a = Publication(title="  Some Paper: A Study!  ", year=2024)
    pub_b = Publication(title="Some Paper A Study", year=2024, venue="Journal X")
    result = deduplicate([pub_a, pub_b])
    assert len(result) == 1
    assert result[0].venue == "Journal X"


def test_different_years_are_not_merged_even_with_similar_titles():
    pub_a = Publication(title="Same Title", year=2024)
    pub_b = Publication(title="Same Title", year=2025)
    result = deduplicate([pub_a, pub_b])
    assert len(result) == 2


def test_truncated_scholar_title_replaced_by_longer_orcid_title():
    scholar_pub = Publication(
        title="A Very Long Title That Got Cut Off...",
        year=2025,
        doi="10.1/x",
        source=SourceType.SCHOLAR,
    )
    orcid_pub = Publication(
        title="A Very Long Title That Got Cut Off For Display Purposes",
        year=2025,
        doi="10.1/x",
        source=SourceType.ORCID,
    )
    # Feed scholar first to prove base-selection isn't just "first wins".
    result = deduplicate([scholar_pub, orcid_pub])
    assert len(result) == 1
    assert result[0].title == "A Very Long Title That Got Cut Off For Display Purposes"


def test_empty_list_returns_empty_list():
    assert deduplicate([]) == []
