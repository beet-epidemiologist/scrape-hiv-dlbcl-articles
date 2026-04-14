from __future__ import annotations

from typing import Dict, List, Set, Tuple

from src.models import Article
from src.utils import normalize_title


SeenSets = Dict[str, Set[str]]


def build_seen_sets(seen_ids: Dict[str, List[str]]) -> SeenSets:
    return {
        "doi": {x.lower().strip() for x in seen_ids.get("doi", []) if x},
        "pmid": {x.strip() for x in seen_ids.get("pmid", []) if x},
        "pmcid": {x.strip() for x in seen_ids.get("pmcid", []) if x},
        "title": {x.strip() for x in seen_ids.get("title", []) if x},
    }


def filter_new_articles(articles: List[Article], seen_ids: Dict[str, List[str]]) -> Tuple[List[Article], Dict[str, List[str]]]:
    seen = build_seen_sets(seen_ids)
    new_articles: List[Article] = []

    for article in articles:
        doi = article.doi.lower().strip() if article.doi else ""
        pmid = article.pmid.strip() if article.pmid else ""
        pmcid = article.pmcid.strip() if article.pmcid else ""
        normalized_title = normalize_title(article.title)

        is_seen = (
            (doi and doi in seen["doi"])
            or (pmid and pmid in seen["pmid"])
            or (pmcid and pmcid in seen["pmcid"])
            or (normalized_title and normalized_title in seen["title"])
        )
        if is_seen:
            continue

        new_articles.append(article)
        if doi:
            seen["doi"].add(doi)
        if pmid:
            seen["pmid"].add(pmid)
        if pmcid:
            seen["pmcid"].add(pmcid)
        if normalized_title:
            seen["title"].add(normalized_title)

    updated = {k: sorted(v) for k, v in seen.items()}
    return new_articles, updated
