from citesync.formatters.markdown import format_markdown
from citesync.models import Publication


def test_publications_grouped_by_year_headings():
    pubs = [
        Publication(title="Newer Paper", year=2026, authors=["A B"]),
        Publication(title="Older Paper", year=2024, authors=["C D"]),
    ]
    md = format_markdown(pubs)
    assert "## 2026" in md
    assert "## 2024" in md
    assert md.index("## 2026") < md.index("## 2024")


def test_entry_includes_title_authors_venue_and_link():
    pub = Publication(
        title="HQC-Orch",
        authors=["Kundan Sharma", "A. Researcher"],
        year=2026,
        venue="IEEE Access",
        url="https://doi.org/10.1109/access.2026.1111111",
        doi="10.1109/access.2026.1111111",
    )
    md = format_markdown([pub])
    assert "[HQC-Orch](https://doi.org/10.1109/access.2026.1111111)" in md
    assert "Kundan Sharma, A. Researcher" in md
    assert "*IEEE Access*" in md
    assert "doi.org/10.1109/access.2026.1111111" in md


def test_entry_without_url_still_shows_bold_title():
    pub = Publication(title="No Link Paper", year=2023)
    md = format_markdown([pub])
    assert "**No Link Paper**" in md
    assert "[No Link Paper]" not in md


def test_undated_publications_grouped_separately():
    pubs = [Publication(title="Mystery Paper", year=None)]
    md = format_markdown(pubs)
    assert "## Undated" in md


def test_empty_list_produces_placeholder_message():
    md = format_markdown([])
    assert "No publications found" in md


def test_custom_page_title_used_as_h1():
    md = format_markdown([Publication(title="X", year=2024)], page_title="Kundan's Papers")
    assert md.startswith("# Kundan's Papers")
