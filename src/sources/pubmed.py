from __future__ import annotations

import time
from typing import Dict, Iterable, List
from xml.etree import ElementTree as ET

from src.models import Article


ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _window_for_query_name(query_name: str) -> int:
    name = (query_name or "").lower()
    if "review" in name or "guideline" in name:
        return 60
    if "therapy" in name or "ddi" in name:
        return 30
    return 14


def _chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _request_with_retry(
    requests_module,
    url: str,
    params: Dict[str, str],
    timeout: int,
    max_retries: int = 3,
):
    for attempt in range(max_retries + 1):
        resp = requests_module.get(url, params=params, timeout=timeout)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        if attempt >= max_retries:
            resp.raise_for_status()
        retry_after = resp.headers.get("Retry-After")
        delay = float(retry_after) if retry_after else min(8.0, 1.5 * (2**attempt))
        print(f"[WARN] PubMed rate-limited (429) at {url}; retry {attempt + 1}/{max_retries} in {delay:.1f}s")
        time.sleep(delay)
    raise RuntimeError("PubMed request retries exhausted")


def fetch_pubmed(queries: Dict[str, str], timeout: int = 30, batch_size: int = 100) -> List[Article]:
    import requests

    pmids: set[str] = set()
    pmid_window_days: Dict[str, int] = {}
    for name, query in queries.items():
        resp = _request_with_retry(
            requests,
            ESEARCH_URL,
            {"db": "pubmed", "term": query, "retmode": "json", "retmax": 200},
            timeout=timeout,
        )
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        pmids.update(ids)
        window_days = _window_for_query_name(name)
        for pmid in ids:
            pmid_window_days[pmid] = max(window_days, pmid_window_days.get(pmid, 0))
        print(f"[INFO] PubMed query '{name}': +{len(ids)} PMIDs (unique total: {len(pmids)})")

    if not pmids:
        return []

    summary: Dict[str, Dict] = {}
    abstracts_by_pmid: Dict[str, str] = {}
    pmid_list = sorted(pmids)
    for idx, batch in enumerate(_chunked(pmid_list, batch_size), start=1):
        id_str = ",".join(batch)
        print(f"[INFO] PubMed batch {idx}: requesting {len(batch)} records")

        summary_resp = _request_with_retry(
            requests,
            ESUMMARY_URL,
            {"db": "pubmed", "id": id_str, "retmode": "json"},
            timeout=timeout,
        )
        summary.update(summary_resp.json().get("result", {}))

        fetch_resp = _request_with_retry(
            requests,
            EFETCH_URL,
            {"db": "pubmed", "id": id_str, "retmode": "xml", "rettype": "abstract"},
            timeout=timeout,
        )
        abstracts_by_pmid.update(_parse_abstracts_from_efetch_xml(fetch_resp.text))

    articles: List[Article] = []
    for pmid in pmid_list:
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
                category=f"pubmed_window_{pmid_window_days.get(pmid, 14)}d",
            )
        )
    return articles


def _iter_pubmed_records(root: ET.Element) -> Iterable[ET.Element]:
    yield from root.findall(".//PubmedArticle")
    yield from root.findall(".//PubmedBookArticle")


def _parse_abstracts_from_efetch_xml(xml_text: str) -> Dict[str, str]:
    abstracts: Dict[str, str] = {}
    root = ET.fromstring(xml_text)

    for record in _iter_pubmed_records(root):
        pmid_node = record.find(".//MedlineCitation/PMID")
        if pmid_node is None or not pmid_node.text:
            continue
        pmid = pmid_node.text.strip()

        abstract_nodes = record.findall(".//MedlineCitation/Article/Abstract/AbstractText")
        segments: List[str] = []
        for node in abstract_nodes:
            label = (node.attrib.get("Label", "") or "").strip()
            section_text = "".join(node.itertext()).strip()
            if not section_text:
                continue
            segments.append(f"{label}: {section_text}" if label else section_text)
        abstracts[pmid] = " ".join(segments).strip()

    return abstracts
