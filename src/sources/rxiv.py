from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List


from src.models import Article


def fetch_rxiv(terms: Dict[str, List[str]], lookback_days: int = 14, timeout: int = 30) -> List[Article]:
    import requests
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()
    results: List[Article] = []
    for server in ["medrxiv", "biorxiv"]:
        url = f"https://api.biorxiv.org/details/{server}/{start}/{end}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        collection = resp.json().get("collection", [])
        for item in collection:
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            category = item.get("category", "")
            if not _match_topic(title, abstract, category, terms):
                continue
            results.append(
                Article(
                    title=title,
                    authors=[item.get("authors", "")],
                    journal=server,
                    publication_date=item.get("date", ""),
                    doi=item.get("doi", ""),
                    abstract=abstract,
                    url=f"https://doi.org/{item.get('doi', '')}" if item.get("doi") else "",
                    source_database=server,
                    is_preprint=True,
                    category=category,
                )
            )
    return results


def _match_topic(title: str, abstract: str, category: str, terms: Dict[str, List[str]]) -> bool:
    text = f"{title} {abstract} {category}".lower()
    hiv_hit = any(t.lower() in text for t in terms.get("HIV_TERMS", []))
    dlbcl_hit = any(t.lower() in text for t in terms.get("DLBCL_TERMS", []))
    return hiv_hit and dlbcl_hit
