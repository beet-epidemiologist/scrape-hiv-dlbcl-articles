from __future__ import annotations

from typing import List

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
from src.utils import load_seen_ids, save_seen_ids


def run() -> int:
    settings = load_settings()
    terms = load_search_terms()
    queries = load_queries()

    all_articles: List[Article] = []
    failed_sources: List[str] = []

    source_jobs = [
        ("PubMed", lambda: fetch_pubmed(queries)),
        ("Europe PMC", lambda: fetch_europe_pmc(terms, lookback_days=settings.lookback_days)),
        ("Crossref", lambda: fetch_crossref(terms, settings.crossref_mailto, lookback_days=settings.lookback_days)),
        ("Rxiv", lambda: fetch_rxiv(terms, lookback_days=settings.lookback_days)),
    ]

    for name, job in source_jobs:
        try:
            all_articles.extend(job())
        except Exception as exc:
            print(f"[WARN] {name} failed: {exc}")
            failed_sources.append(name)

    seen_ids = load_seen_ids("data/seen_ids.json")
    new_articles, updated_seen = filter_new_articles(all_articles, seen_ids)

    scored = [score_and_tag(a, terms) for a in new_articles]
    scored.sort(key=lambda x: (x.relevance_score, x.publication_date), reverse=True)

    md_path, _ = generate_reports(scored, failed_sources)
    save_seen_ids("data/seen_ids.json", updated_seen)

    try:
        sent = send_email_if_configured(settings, md_path)
        if sent:
            print("[INFO] Email notification sent.")
    except Exception as exc:
        print(f"[WARN] Email send failed: {exc}")

    print(f"[INFO] Completed. New articles: {len(scored)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
