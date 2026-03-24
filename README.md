# CiteSync

Keep your personal website and GitHub README's citations page in sync with
your actual publication record — automatically, in one command.

## Problem

If you publish papers, you've probably got a "Publications" section on your
personal site and maybe a pinned list in a GitHub README. Every time a new
paper comes out, or a preprint gets its DOI, you have to remember to update
both — by hand, in two different formats (a nice-looking list for humans,
and BibTeX for anyone who wants to cite you). It's tedious and it drifts out
of date.

CiteSync pulls your publication metadata from a source of truth you already
maintain — your **ORCID** record — and regenerates a clean Markdown page and
a `.bib` file in one call. Point a GitHub Action or a cron job at it and your
citations page never goes stale again.

**Why ORCID, not Google Scholar?** ORCID has a stable, documented, versioned
public API. Google Scholar has no API at all — anything that reads it is
scraping an HTML page that can change shape without notice and can rate-limit
or block scripted requests. CiteSync treats ORCID as the primary path and
ships a Scholar fetcher as an explicitly opt-in fallback for papers not yet
registered on ORCID (see `src/citesync/fetchers/scholar.py` for the caveats).

## Install

```bash
git clone https://github.com/your-username/citesync.git
cd citesync
pip install -e .

# for running the test suite too:
pip install -e ".[dev]"
```

Requires Python 3.10+.

## CLI usage

```bash
citesync generate --orcid 0009-0000-XXXX-XXXX --output citations.md
```

This writes `citations.md` (grouped by year, human-readable) and, by
default, a sibling `citations.bib` (same basename, `.bib` extension).

Other flags:

```bash
# Add Google Scholar as a fallback/supplement (fragile — see module docstring)
citesync generate --orcid 0009-0000-XXXX-XXXX --scholar-id AbCdEfG --output citations.md

# Send the BibTeX file somewhere else
citesync generate --orcid 0009-0000-XXXX-XXXX --output citations.md --bibtex-output refs.bib

# Markdown only, skip BibTeX entirely
citesync generate --orcid 0009-0000-XXXX-XXXX --output citations.md --no-bibtex

# Custom page heading
citesync generate --orcid 0009-0000-XXXX-XXXX --output citations.md --title "Kundan Sharma — Publications"
```

Records that appear from multiple sources (e.g. both ORCID and Scholar) are
merged rather than duplicated — see `src/citesync/dedup.py`.

## Sample generated output

Given an ORCID record with three works, `citesync generate` produces:

**`citations.md`**

```markdown
# Kundan Sharma — Publications

## 2026

- **[HQC-Orch: Hybrid Quantum-Classical Orchestration](https://doi.org/10.1109/access.2026.1111111)**  
  Kundan Sharma, A. Researcher. *IEEE Access*.  
  DOI: [10.1109/access.2026.1111111](https://doi.org/10.1109/access.2026.1111111)

## 2025

- **FALCON: Federated Adaptive Learning for Cloud Orchestration Networks**  
  Kundan Sharma. *ICCMSE 2025 Proceedings*.

## 2024

- **A Work With No Contributors Listed**
```

**`citations.bib`**

```bibtex
@article{sharma2026hqcorch,
  title = {HQC-Orch: Hybrid Quantum-Classical Orchestration},
  author = {Kundan Sharma and A. Researcher},
  year = {2026},
  journal = {IEEE Access},
  doi = {10.1109/access.2026.1111111},
  url = {https://doi.org/10.1109/access.2026.1111111}
}

@inproceedings{sharma2025falcon,
  title = {FALCON: Federated Adaptive Learning for Cloud Orchestration Networks},
  author = {Kundan Sharma},
  year = {2025},
  booktitle = {ICCMSE 2025 Proceedings}
}

@article{unknown2024a,
  title = {A Work With No Contributors Listed},
  year = {2024}
}
```

## Project structure

```
citesync/
├── pyproject.toml
├── README.md
├── src/citesync/
│   ├── models.py            # Publication dataclass shared by every module
│   ├── fetchers/
│   │   ├── orcid.py         # Primary source: ORCID public API v3.0
│   │   └── scholar.py       # Fallback: Scholar scraping (documented fragility)
│   ├── dedup.py             # Cross-source merge/dedup logic
│   ├── formatters/
│   │   ├── bibtex.py
│   │   └── markdown.py
│   └── cli.py                # `citesync generate ...`
└── tests/                    # pytest, all HTTP calls mocked via `responses`
```

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

No test in this suite hits a live API — ORCID (and, in the fallback fetcher,
Scholar) responses are mocked with the `responses` library against realistic
fixture payloads in `tests/fixtures/`.

## Automating it (e.g. GitHub Actions)

A minimal workflow to regenerate `citations.md` on a schedule and open a PR
if it changed:

```yaml
name: Sync citations
on:
  schedule:
    - cron: "0 6 * * 1"  # weekly, Monday 06:00 UTC
  workflow_dispatch:
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .
      - run: citesync generate --orcid 0009-0000-XXXX-XXXX --output citations.md
      - uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore: sync citations"
          title: "Sync citations from ORCID"
```

## License

MIT
