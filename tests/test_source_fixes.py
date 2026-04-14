from src.sources.europe_pmc import _in_window, build_europe_pmc_query
from src.sources.pubmed import _chunked, _parse_abstracts_from_efetch_xml
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


def test_pubmed_chunked_batches() -> None:
    chunks = list(_chunked([str(i) for i in range(7)], 3))
    assert chunks == [["0", "1", "2"], ["3", "4", "5"], ["6"]]
