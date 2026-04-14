from src.sources.europe_pmc import build_europe_pmc_query
from src.sources.pubmed import _parse_abstracts_from_efetch_xml
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
    assert "TO *" in q


def test_rxiv_match_includes_category() -> None:
    terms = {"HIV_TERMS": ["hiv"], "DLBCL_TERMS": ["dlbcl"]}
    assert _match_topic("", "hiv story", "dlbcl", terms)
