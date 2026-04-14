from src.models import Article
from src.monitoring_mode import score_and_tag
from src.reporters import generate_reports
from src.utils import parse_publication_date


TERMS = {
    "HIV_TERMS": ["HIV"],
    "AIDS_LYMPHOMA_TERMS": ["HIV-associated lymphoma"],
    "DLBCL_TERMS": ["DLBCL", "diffuse large b-cell lymphoma"],
    "THERAPY_TERMS": ["rituximab", "drug interaction"],
    "OUTCOME_TERMS": ["survival"],
    "REVIEW_GUIDELINE_TERMS": ["review"],
}


def test_relevance_score_basic() -> None:
    article = Article(
        title="HIV related DLBCL with rituximab",
        abstract="improved survival",
    )
    scored = score_and_tag(article, TERMS)
    assert scored.relevance_score >= 8
    assert "treatment" in scored.tags
    assert "prognosis" in scored.tags


def test_empty_result_report() -> None:
    md_path, csv_path = generate_reports([], failed_sources=[])
    assert md_path.exists()
    assert csv_path.exists()


def test_parse_publication_date_variants() -> None:
    assert parse_publication_date("2026 Apr 10").isoformat() == "2026-04-10"
    assert parse_publication_date("2026 Apr").isoformat() == "2026-04-01"
    assert parse_publication_date("2026").isoformat() == "2026-01-01"
    assert parse_publication_date("not-a-date") is None
