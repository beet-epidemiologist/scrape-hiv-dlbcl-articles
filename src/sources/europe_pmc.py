from __future__ import annotations

from typing import Dict, List

import requests

from src.models import Article


def build_europe_pmc_query(terms: Dict[str, List[str]]) -> str:
    hiv = " OR ".join(f'"{t}"' for t in terms.get("HIV_TERMS", [])[:6])
    dlbcl = " OR ".join(f'"{t}"' for t in terms.get("DLBCL_TERMS", [])[:6])
    therapy = " OR ".join(f'"{t}"' for t in terms.get("THERAPY_TERMS", [])[:8])
    return f"(({hiv}) AND ({dlbcl})) OR (({hiv}) AND ({dlbcl}) AND ({therapy}))"


def fetch_europe_pmc(terms: Dict[str, List[str]], timeout: int = 30) -> List[Article]:
    query = build_europe_pmc_query(terms)
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
