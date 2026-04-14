from __future__ import annotations

import time
from typing import Dict, Iterable, List
from xml.etree import ElementTree as ET

from src.models import Article


ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_BATCH_SIZE = 100
RETRY_WAIT_SECONDS = [2, 5, 10]
INTER_REQUEST_SLEEP_SECONDS = 0.34


def _chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _request_with_retry(url: str, params: Dict[str, str], timeout: int):
    import requests

    last_error: Exception | None = None
    for attempt in range(len(RETRY_WAIT_SECONDS) + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                resp.raise_for_status()
            return resp
        except requests.RequestException as exc:  # 网络波动、429、5xx 都会进入重试
            last_error = exc
            if attempt >= len(RETRY_WAIT_SECONDS):
                break
            wait = RETRY_WAIT_SECONDS[attempt]
            print(f"[WARN] PubMed request retry {attempt + 1}/{len(RETRY_WAIT_SECONDS)} in {wait}s: {url}")
            time.sleep(wait)
    raise RuntimeError(f"PubMed request failed after retries: {url}") from last_error


def fetch_pubmed(queries: Dict[str, str], timeout: int = 30) -> List[Article]:
    pmids: set[str] = set()
    for _, query in queries.items():
        resp = _request_with_retry(
            ESEARCH_URL,
            {"db": "pubmed", "term": query, "retmode": "json", "retmax": 200},
            timeout,
        )
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        pmids.update(ids)
        time.sleep(INTER_REQUEST_SLEEP_SECONDS)

    if not pmids:
        return []

    all_articles: List[Article] = []
    for pmid_batch in _chunked(sorted(pmids), PUBMED_BATCH_SIZE):
        id_str = ",".join(pmid_batch)

        summary_resp = _request_with_retry(
            ESUMMARY_URL,
            {"db": "pubmed", "id": id_str, "retmode": "json"},
            timeout,
        )
        summary = summary_resp.json().get("result", {})
        time.sleep(INTER_REQUEST_SLEEP_SECONDS)

        fetch_resp = _request_with_retry(
            EFETCH_URL,
            {"db": "pubmed", "id": id_str, "retmode": "xml", "rettype": "abstract"},
            timeout,
        )
        abstracts_by_pmid = _parse_abstracts_from_efetch_xml(fetch_resp.text)
        time.sleep(INTER_REQUEST_SLEEP_SECONDS)

        for pmid in pmid_batch:
            item = summary.get(pmid, {})
            doi = ""
            for aid in item.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value", "")
            pmcid = ""
            for aid in item.get("articleids", []):
                if aid.get("idtype") == "pmc":
                    pmcid = aid.get("value", "")

            all_articles.append(
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

    return all_articles


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
