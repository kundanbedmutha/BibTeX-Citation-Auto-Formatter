import json
from pathlib import Path

import responses

from citesync.cli import main
from citesync.fetchers.orcid import ORCID_API_BASE

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ORCID_ID = "0009-0000-1234-5678"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def _mock_orcid_endpoints():
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


@responses.activate
def test_generate_writes_markdown_and_bibtex(tmp_path):
    _mock_orcid_endpoints()
    output_path = tmp_path / "citations.md"

    exit_code = main(["generate", "--orcid", ORCID_ID, "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    bib_path = output_path.with_suffix(".bib")
    assert bib_path.exists()

    md_text = output_path.read_text()
    assert "# Publications" in md_text
    assert "HQC-Orch" in md_text

    bib_text = bib_path.read_text()
    assert "@article{" in bib_text or "@inproceedings{" in bib_text


@responses.activate
def test_generate_respects_custom_bibtex_output_path(tmp_path):
    _mock_orcid_endpoints()
    md_path = tmp_path / "pubs.md"
    bib_path = tmp_path / "custom.bib"

    exit_code = main(
        [
            "generate",
            "--orcid",
            ORCID_ID,
            "--output",
            str(md_path),
            "--bibtex-output",
            str(bib_path),
        ]
    )

    assert exit_code == 0
    assert bib_path.exists()
    assert not (tmp_path / "pubs.bib").exists()


@responses.activate
def test_generate_no_bibtex_flag_skips_bib_file(tmp_path):
    _mock_orcid_endpoints()
    output_path = tmp_path / "citations.md"

    exit_code = main(
        ["generate", "--orcid", ORCID_ID, "--output", str(output_path), "--no-bibtex"]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert not output_path.with_suffix(".bib").exists()


def test_generate_requires_orcid_or_scholar_id(tmp_path, capsys):
    output_path = tmp_path / "citations.md"
    exit_code = main(["generate", "--output", str(output_path)])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "--orcid or --scholar-id" in captured.err


def test_generate_rejects_malformed_orcid_id(tmp_path, capsys):
    output_path = tmp_path / "citations.md"
    exit_code = main(["generate", "--orcid", "not-valid", "--output", str(output_path)])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "orcid" in captured.err.lower()


@responses.activate
def test_generate_custom_title_appears_in_markdown(tmp_path):
    _mock_orcid_endpoints()
    output_path = tmp_path / "citations.md"

    main(
        [
            "generate",
            "--orcid",
            ORCID_ID,
            "--output",
            str(output_path),
            "--title",
            "Kundan's Research Output",
        ]
    )

    assert "# Kundan's Research Output" in output_path.read_text()


def test_generate_reports_failure_when_orcid_api_errors(tmp_path, capsys):
    output_path = tmp_path / "citations.md"
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            f"{ORCID_API_BASE}/{ORCID_ID}/works",
            status=500,
            body="server error",
        )
        exit_code = main(["generate", "--orcid", ORCID_ID, "--output", str(output_path)])

    assert exit_code == 1
    assert not output_path.exists()
    captured = capsys.readouterr()
    assert "error fetching from ORCID" in captured.err
