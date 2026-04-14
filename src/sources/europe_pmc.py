from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List


from src.models import Article


def build_europe_pmc_query(terms: Dict[str, List[str]], lookback_days: int) -> str:
    hiv = " OR ".join(f'"{t}"' for t in terms.get("HIV_TERMS", [])[:6])
    dlbcl = " OR ".join(f'"{t}"' for t in terms.get("DLBCL_TERMS", [])[:6])
    therapy = " OR ".join(f'"{t}"' for t in terms.get("THERAPY_TERMS", [])[:8])
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    base = f"(({hiv}) AND ({dlbcl})) OR (({hiv}) AND ({dlbcl}) AND ({therapy}))"
    return f"({base}) AND FIRST_PDATE:[{start} TO *]"


def fetch_europe_pmc(terms: Dict[str, List[str]], lookback_days: int = 14, timeout: int = 30) -> List[Article]:
    import requests
    query = build_europe_pmc_query(terms, lookback_days)
    resp = requests.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={"query": query, "format": "json", "pageSize": 200, "sort": "DATE_DESC"},
        timeout=timeout,
    )
    resp.raise_for_status()
    results = resp.json().get("resultList", {}).get("result", [])
    articles: List[Article] = []
    for r in results:
        articles.append(
            Article(
                title=r.get("title", ""),
                authors=[r.get("authorString", "")],
                journal=r.get("journalTitle", ""),
                publication_date=r.get("firstPublicationDate", "") or r.get("pubYear", ""),
                doi=r.get("doi", ""),
                pmid=r.get("pmid", ""),
                pmcid=r.get("pmcid", ""),
                abstract=r.get("abstractText", "") or "",
                url=f"https://europepmc.org/article/MED/{r.get('pmid')}" if r.get("pmid") else "",
                source_database="Europe PMC",
            )
        )
    return articles
