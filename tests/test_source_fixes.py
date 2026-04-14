from src.sources.europe_pmc import _in_window, build_europe_pmc_query
from src.sources.pubmed import _parse_abstracts_from_efetch_xml, _window_for_query_name, fetch_pubmed
from src.sources.rxiv import _match_topic


def test_pubmed_xml_abstract_mapping() -> None:
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>111</PMID>
          <Article>
            <Abstract>
              <AbstractText Label=\"Background\">A</AbstractText>
              <AbstractText>B</AbstractText>
            </Abstract>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>222</PMID>
          <Article><Abstract><AbstractText>C</AbstractText></Abstract></Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    data = _parse_abstracts_from_efetch_xml(xml)
    assert data["111"] == "Background: A B"
    assert data["222"] == "C"


def test_europe_pmc_query_has_date_filter() -> None:
    q = build_europe_pmc_query({"HIV_TERMS": ["HIV"], "DLBCL_TERMS": ["DLBCL"], "THERAPY_TERMS": []}, 14)
    assert "FIRST_PDATE" in q
    assert "TO" in q


def test_rxiv_match_includes_category() -> None:
    terms = {"HIV_TERMS": ["hiv"], "DLBCL_TERMS": ["dlbcl", "diffuse large b-cell lymphoma"]}
    assert _match_topic("", "hiv story", "dlbcl", terms)
    assert _match_topic("hiv", "", "diffuse large b-cell lymphoma", terms)


def test_europe_pmc_in_window() -> None:
    from datetime import date
    assert _in_window(date.today().isoformat(), 14)
    assert not _in_window("2000-01-01", 14)


def test_pubmed_retry_and_batching(monkeypatch) -> None:
    import types
    import sys

    class DummyResp:
        def __init__(self, status_code, payload=None, text="", headers=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.text = text
            self.headers = headers or {}

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"http {self.status_code}")

    calls = {"esearch": 0, "esummary": 0, "efetch": 0}
    first_429 = {"value": True}

    def fake_get(url, params, timeout):
        if "esearch.fcgi" in url:
            calls["esearch"] += 1
            ids = [str(i) for i in range(1, 6)]
            return DummyResp(200, {"esearchresult": {"idlist": ids}})
        if "esummary.fcgi" in url:
            calls["esummary"] += 1
            batch_ids = params["id"].split(",")
            if first_429["value"]:
                first_429["value"] = False
                return DummyResp(429, headers={"Retry-After": "0"})
            result = {pid: {"title": f"T{pid}", "authors": [], "fulljournalname": "", "pubdate": "2026-04-01", "articleids": []} for pid in batch_ids}
            return DummyResp(200, {"result": result})
        calls["efetch"] += 1
        ids = params["id"].split(",")
        xml = "<PubmedArticleSet>" + "".join(
            f"<PubmedArticle><MedlineCitation><PMID>{pid}</PMID><Article><Abstract><AbstractText>A{pid}</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle>"
            for pid in ids
        ) + "</PubmedArticleSet>"
        return DummyResp(200, text=xml)

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr("time.sleep", lambda *_: None)

    articles = fetch_pubmed({"q1": "x"}, batch_size=2)
    assert len(articles) == 5
    assert all(a.category == "pubmed_window_14d" for a in articles)
    assert calls["esummary"] == 4  # 3 batches + 1 retry
    assert calls["efetch"] == 3


def test_pubmed_query_window_mapping() -> None:
    assert _window_for_query_name("pubmed_core_latest") == 14
    assert _window_for_query_name("pubmed_therapy_ddi") == 30
    assert _window_for_query_name("pubmed_reviews_guidelines") == 60
