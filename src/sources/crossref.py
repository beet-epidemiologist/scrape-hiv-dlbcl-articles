from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

import requests

from src.models import Article


def build_crossref_query(terms: Dict[str, List[str]]) -> str:
    hiv = " OR ".join(terms.get("HIV_TERMS", [])[:4])
    dlbcl = " OR ".join(terms.get("DLBCL_TERMS", [])[:4])
    return f"({hiv}) ({dlbcl})"


def fetch_crossref(terms: Dict[str, List[str]], mailto: str, lookback_days: int = 30, timeout: int = 30) -> List[Article]:
    if not mailto:
        return []
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    query = build_crossref_query(terms)
    resp = requests.get(
        "https://api.crossref.org/works",
        params={
            "query": query,
            "filter": f"from-created-date:{start},type:journal-article",
            "rows": 100,
            "mailto": mailto,
            "select": "DOI,title,author,container-title,published-print,published-online,URL,abstract",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    items = resp.json().get("message", {}).get("items", [])

    articles: List[Article] = []
    for item in items:
        title_list = item.get("title", [])
        article_title = title_list[0] if title_list else ""
        authors = []
        for a in item.get("author", []):
            name = " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x)
            if name:
                authors.append(name)
        journal_list = item.get("container-title", [])
        pub_date = _extract_date(item)

        articles.append(
            Article(
                title=article_title,
                authors=authors,
                journal=journal_list[0] if journal_list else "",
                publication_date=pub_date,
                doi=item.get("DOI", ""),
                abstract=(item.get("abstract", "") or "").replace("<jats:p>", "").replace("</jats:p>", ""),
                url=item.get("URL", ""),
                source_database="Crossref",
            )
        )
    return articles


def _extract_date(item: Dict) -> str:
    for key in ["published-print", "published-online"]:
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            return "-".join(str(x) for x in parts[0])
    return ""
