from __future__ import annotations

from typing import Dict, List

import requests

from src.models import Article


ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_pubmed(queries: Dict[str, str], timeout: int = 30) -> List[Article]:
    pmids: set[str] = set()
    for _, query in queries.items():
        resp = requests.get(ESEARCH_URL, params={"db": "pubmed", "term": query, "retmode": "json", "retmax": 200}, timeout=timeout)
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        pmids.update(ids)

    if not pmids:
        return []

    id_str = ",".join(sorted(pmids))
    summary_resp = requests.get(ESUMMARY_URL, params={"db": "pubmed", "id": id_str, "retmode": "json"}, timeout=timeout)
    summary_resp.raise_for_status()
    summary = summary_resp.json().get("result", {})

    fetch_resp = requests.get(EFETCH_URL, params={"db": "pubmed", "id": id_str, "retmode": "text", "rettype": "abstract"}, timeout=timeout)
    fetch_resp.raise_for_status()
    abstract_raw = fetch_resp.text

    articles: List[Article] = []
    for pmid in pmids:
        item = summary.get(pmid, {})
        doi = ""
        for aid in item.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
        pmcid = ""
        for aid in item.get("articleids", []):
            if aid.get("idtype") == "pmc":
                pmcid = aid.get("value", "")

        articles.append(
            Article(
                title=item.get("title", ""),
                authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
                journal=item.get("fulljournalname", ""),
                publication_date=item.get("pubdate", ""),
                doi=doi,
                pmid=pmid,
                pmcid=pmcid,
                abstract=_extract_abstract_for_pmid(abstract_raw, pmid),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                source_database="PubMed",
            )
        )
    return articles


def _extract_abstract_for_pmid(efetch_text: str, pmid: str) -> str:
    marker = f"PMID: {pmid}"
    idx = efetch_text.find(marker)
    if idx == -1:
        return ""
    block = efetch_text[max(0, idx - 2000):idx]
    return " ".join(block.splitlines()[-8:]).strip()
