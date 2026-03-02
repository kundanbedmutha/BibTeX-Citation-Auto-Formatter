from citesync.formatters.bibtex import format_bibtex
from citesync.models import Publication, SourceType


def test_journal_article_maps_to_article_entry_with_journal_field():
    pub = Publication(
        title="HQC-Orch: Hybrid Quantum-Classical Orchestration",
        authors=["Kundan Sharma", "A. Researcher"],
        year=2026,
        venue="IEEE Access",
        doi="10.1109/access.2026.1111111",
        url="https://doi.org/10.1109/access.2026.1111111",
        pub_type="journal-article",
        source=SourceType.ORCID,
    )
    bib = format_bibtex([pub])
    assert bib.startswith("@article{sharma2026hqcorch,")
    assert "journal = {IEEE Access}" in bib
    assert "author = {Kundan Sharma and A. Researcher}" in bib
    assert "year = {2026}" in bib
    assert "doi = {10.1109/access.2026.1111111}" in bib
    assert bib.rstrip().endswith("}")


def test_conference_paper_maps_to_inproceedings_with_booktitle():
    pub = Publication(
        title="FALCON",
        authors=["Kundan Sharma"],
        year=2025,
        venue="ICCMSE 2025 Proceedings",
        pub_type="conference-paper",
    )
    bib = format_bibtex([pub])
    assert bib.startswith("@inproceedings{")
    assert "booktitle = {ICCMSE 2025 Proceedings}" in bib
    assert "journal" not in bib


def test_unknown_pub_type_falls_back_to_misc():
    pub = Publication(title="Something Unusual", pub_type="dataset")
    bib = format_bibtex([pub])
    assert bib.startswith("@misc{")


def test_missing_optional_fields_are_simply_omitted():
    pub = Publication(title="Minimal Paper")
    bib = format_bibtex([pub])
    assert "author" not in bib
    assert "journal" not in bib
    assert "booktitle" not in bib
    assert "doi" not in bib
    assert "title = {Minimal Paper}" in bib


def test_special_characters_are_escaped():
    pub = Publication(title="Cats & Dogs: A 50% Study_of_Pets", year=2024)
    bib = format_bibtex([pub])
    assert "Cats \\& Dogs: A 50\\% Study\\_of\\_Pets" in bib


def test_multiple_publications_separated_by_blank_line():
    pubs = [
        Publication(title="Paper One", year=2024, authors=["A B"]),
        Publication(title="Paper Two", year=2025, authors=["C D"]),
    ]
    bib = format_bibtex(pubs)
    assert bib.count("@misc{") == 2
    assert "\n\n@misc{" in bib


def test_empty_list_returns_empty_string():
    assert format_bibtex([]) == ""


def test_cite_key_is_unique_for_same_author_different_title():
    pub_a = Publication(title="Alpha Study", authors=["Kundan Sharma"], year=2024)
    pub_b = Publication(title="Beta Study", authors=["Kundan Sharma"], year=2024)
    bib = format_bibtex([pub_a, pub_b])
    assert "@misc{sharma2024alpha," in bib
    assert "@misc{sharma2024beta," in bib
