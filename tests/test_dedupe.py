from src.dedupe import filter_new_articles
from src.models import Article


def test_doi_dedupe() -> None:
    seen = {"doi": ["10.1000/abc"], "pmid": [], "pmcid": [], "title": []}
    items = [Article(title="a", doi="10.1000/abc"), Article(title="b", doi="10.1000/new")]
    new_items, updated = filter_new_articles(items, seen)
    assert len(new_items) == 1
    assert new_items[0].title == "b"
    assert "10.1000/new" in updated["doi"]


def test_title_normalized_dedupe() -> None:
    seen = {"doi": [], "pmid": [], "pmcid": [], "title": ["hiv dlbcl a case report"]}
    items = [Article(title="HIV-DLBCL: a case report!!")]
    new_items, _ = filter_new_articles(items, seen)
    assert len(new_items) == 0
