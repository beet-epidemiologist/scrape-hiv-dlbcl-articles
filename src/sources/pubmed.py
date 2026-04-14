from __future__ import annotations

from typing import Dict, List
from xml.etree import ElementTree as ET


from src.models import Article


ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_pubmed(queries: Dict[str, str], timeout: int = 30) -> List[Article]:
    import requests
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

    fetch_resp = requests.get(EFETCH_URL, params={"db": "pubmed", "id": id_str, "retmode": "xml", "rettype": "abstract"}, timeout=timeout)
    fetch_resp.raise_for_status()
    abstracts_by_pmid = _parse_abstracts_from_efetch_xml(fetch_resp.text)

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
                abstract=abstracts_by_pmid.get(pmid, ""),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                source_database="PubMed",
            )
        )
    return articles


def _parse_abstracts_from_efetch_xml(xml_text: str) -> Dict[str, str]:
    abstracts: Dict[str, str] = {}
    root = ET.fromstring(xml_text)

    for article in root.findall('.//PubmedArticle'):
        pmid_node = article.find('.//MedlineCitation/PMID')
        if pmid_node is None or not pmid_node.text:
            continue
        pmid = pmid_node.text.strip()

        abstract_nodes = article.findall('.//MedlineCitation/Article/Abstract/AbstractText')
        segments: List[str] = []
        for node in abstract_nodes:
            label = (node.attrib.get("Label", "") or "").strip()
            section_text = "".join(node.itertext()).strip()
            if not section_text:
                continue
            if label:
                segments.append(f"{label}: {section_text}")
            else:
                segments.append(section_text)
        abstracts[pmid] = " ".join(segments).strip()

    return abstracts
