from __future__ import annotations

from collections import Counter
from typing import Dict, List

from src.config import load_queries, load_search_terms, load_settings
from src.dedupe import filter_new_articles
from src.models import Article
from src.monitoring_mode import score_and_tag
from src.notifier import send_email_if_configured
from src.reporters import generate_reports
from src.sources.crossref import fetch_crossref
from src.sources.europe_pmc import fetch_europe_pmc
from src.sources.pubmed import fetch_pubmed
from src.sources.rxiv import fetch_rxiv
from src.utils import is_within_days, load_seen_ids, save_seen_ids


def _basic_filter(articles: List[Article]) -> List[Article]:
    return [a for a in articles if (a.title or "").strip()]




def _publication_window_days(article: Article) -> int:
    tags = set(article.tags)
    if "review_guideline" in tags:
        return 60
    if "treatment" in tags or "drug_interaction" in tags:
        return 30
    return 14


def _filter_recent_publication(articles: List[Article], strict_recent_publication: bool) -> List[Article]:
    if not strict_recent_publication:
        return articles
    kept: List[Article] = []
    for a in articles:
        days = _publication_window_days(a)
        if is_within_days(a.publication_date, days):
            kept.append(a)
    return kept

def run() -> int:
    settings = load_settings()
    terms = load_search_terms()
    queries = load_queries()

    all_articles: List[Article] = []
    failed_sources: List[str] = []
    source_stats: Dict[str, Dict[str, int]] = {}

    source_jobs = [
        ("PubMed", lambda: fetch_pubmed(queries)),
        ("Europe PMC", lambda: fetch_europe_pmc(terms, lookback_days=settings.lookback_days)),
        ("Crossref", lambda: fetch_crossref(terms, settings.crossref_mailto, lookback_days=settings.lookback_days)),
        ("Rxiv", lambda: fetch_rxiv(terms, lookback_days=settings.lookback_days)),
    ]

    for name, job in source_jobs:
        try:
            fetched = job()
            filtered = _basic_filter(fetched)
            all_articles.extend(filtered)
            source_stats[name] = {"fetched": len(fetched), "filtered": len(filtered), "new": 0}
        except Exception as exc:
            print(f"[WARN] Source failed [{name}] {type(exc).__name__}: {exc}")
            failed_sources.append(name)
            source_stats[name] = {"fetched": 0, "filtered": 0, "new": 0}

    seen_ids = load_seen_ids("data/seen_ids.json")
    new_articles, updated_seen = filter_new_articles(all_articles, seen_ids)

    source_name_map = {
        "PubMed": "PubMed",
        "Europe PMC": "Europe PMC",
        "Crossref": "Crossref",
        "medrxiv": "Rxiv",
        "biorxiv": "Rxiv",
    }
    new_counter = Counter(source_name_map.get(a.source_database, a.source_database) for a in new_articles)
    for source_name, stats in source_stats.items():
        stats["new"] = new_counter.get(source_name, 0)
        print(
            f"[INFO] Source={source_name} fetched={stats['fetched']} "
            f"filtered={stats['filtered']} new={stats['new']}"
        )

    scored = [score_and_tag(a, terms) for a in new_articles]
    recent_scored = _filter_recent_publication(scored, settings.strict_recent_publication)
    print(f"[INFO] Recent publication filter strict={settings.strict_recent_publication} kept={len(recent_scored)} dropped={len(scored)-len(recent_scored)}")
    recent_scored.sort(key=lambda x: (x.relevance_score, x.publication_date), reverse=True)

    md_path, _ = generate_reports(recent_scored, failed_sources)
    save_seen_ids("data/seen_ids.json", updated_seen)

    try:
        sent = send_email_if_configured(settings, md_path)
        if sent:
            print("[INFO] Email notification sent.")
    except Exception as exc:
        print(f"[WARN] Email send failed: {exc}")

    print(f"[INFO] Completed. New articles: {len(recent_scored)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
