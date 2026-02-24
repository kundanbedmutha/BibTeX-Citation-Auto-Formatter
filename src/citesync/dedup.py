"""Deduplicate and merge publications sourced from multiple fetchers.

The same paper often shows up with slightly different metadata across
sources — Scholar might have a truncated title, ORCID might be missing a
venue, etc. Rather than picking one record and discarding the other, we
group matches together and merge field-by-field, preferring the most
complete/trustworthy value for each field.
"""

from __future__ import annotations

from citesync.models import Publication, SourceType

# When two sources disagree on a field, prefer the one from a higher-ranked
# source. ORCID data is structured and author-curated; Scholar is scraped.
_SOURCE_PRIORITY = {
    SourceType.ORCID: 2,
    SourceType.MANUAL: 1,
    SourceType.SCHOLAR: 0,
}


def deduplicate(publications: list[Publication]) -> list[Publication]:
    """Group publications that refer to the same work and merge each group.

    Grouping uses `Publication.dedup_key()` (DOI when available, else a
    normalized title+year). Order of the input list doesn't matter; the
    output is sorted by (year desc, title) for stable, readable results.
    """
    groups: dict[str, list[Publication]] = {}
    for pub in publications:
        groups.setdefault(pub.dedup_key(), []).append(pub)

    merged = [_merge_group(group) for group in groups.values()]
    merged.sort(key=lambda p: (-(p.year or 0), p.title.lower()))
    return merged


def _merge_group(group: list[Publication]) -> Publication:
    if len(group) == 1:
        return group[0]

    # Highest-priority source's record is the base; other records only fill
    # in gaps or offer a longer value for fields where "more info" wins.
    ordered = sorted(group, key=lambda p: -_SOURCE_PRIORITY.get(p.source, -1))
    base = ordered[0]

    title = base.title
    authors = base.authors
    year = base.year
    venue = base.venue
    doi = base.doi
    url = base.url
    pub_type = base.pub_type

    for pub in ordered[1:]:
        if not authors and pub.authors:
            authors = pub.authors
        elif pub.authors and len(pub.authors) > len(authors):
            authors = pub.authors  # a fuller author list is strictly more useful

        year = year or pub.year
        venue = venue or pub.venue
        doi = doi or pub.doi
        url = url or pub.url
        pub_type = pub_type or pub.pub_type

        # Prefer the longer title only if the base title looks truncated
        # (Scholar often ends titles with "..."). Otherwise keep base's,
        # since ORCID titles are the ones we trust most.
        if title.rstrip().endswith("...") and len(pub.title) > len(title):
            title = pub.title

    return Publication(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        pub_type=pub_type,
        source=base.source,
        raw_id=base.raw_id,
    )
