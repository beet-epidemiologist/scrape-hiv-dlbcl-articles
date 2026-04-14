from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Dict, List

from src.models import Article


def _sort_key(article: Article) -> tuple:
    return (article.publication_date or "", article.relevance_score)


def _bucket(articles: List[Article]) -> Dict[str, List[Article]]:
    buckets = {"high": [], "medium": [], "low": []}
    for a in articles:
        if a.relevance_score >= 8:
            buckets["high"].append(a)
        elif a.relevance_score >= 5:
            buckets["medium"].append(a)
        else:
            buckets["low"].append(a)
    for k in buckets:
        buckets[k] = sorted(buckets[k], key=_sort_key, reverse=True)
    return buckets


def generate_reports(articles: List[Article], failed_sources: List[str]) -> tuple[Path, Path]:
    today = date.today().isoformat()
    md_path = Path(f"reports/daily_{today}.md")
    csv_path = Path(f"reports/daily_{today}.csv")
    md_path.parent.mkdir(parents=True, exist_ok=True)

    published = [a for a in articles if not a.is_preprint]
    preprints = [a for a in articles if a.is_preprint]

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# HIV / DLBCL 每日文献监测日报（{today}）\n\n")
        if failed_sources:
            f.write("## 数据源异常\n")
            for s in failed_sources:
                f.write(f"- {s} 抓取失败（已跳过，不影响其他数据源）\n")
            f.write("\n")

        for section_name, subset in [("正式发表论文", published), ("预印本", preprints)]:
            f.write(f"## {section_name}\n\n")
            buckets = _bucket(subset)
            for label, key in [("高相关（score >= 8）", "high"), ("中相关（score 5-7）", "medium"), ("低相关（score < 5）", "low")]:
                f.write(f"### {label}\n\n")
                if not buckets[key]:
                    f.write("- 无\n\n")
                    continue
                for a in buckets[key]:
                    f.write(f"#### {a.title}\n")
                    f.write(f"- authors: {', '.join(a.authors)}\n")
                    f.write(f"- journal/source: {a.journal}\n")
                    f.write(f"- publication date: {a.publication_date}\n")
                    f.write(f"- DOI: {a.doi}\n")
                    f.write(f"- PMID/PMCID: {a.pmid} / {a.pmcid}\n")
                    f.write(f"- abstract: {a.abstract}\n")
                    f.write(f"- url: {a.url}\n")
                    f.write(f"- source database: {a.source_database}\n")
                    f.write(f"- relevance_score: {a.relevance_score}\n")
                    f.write(f"- tags: {', '.join(a.tags)}\n\n")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title", "authors", "journal", "publication_date", "doi", "pmid", "pmcid",
                "abstract", "url", "source_database", "is_preprint", "relevance_score", "tags"
            ],
        )
        writer.writeheader()
        for a in sorted(articles, key=_sort_key, reverse=True):
            writer.writerow(
                {
                    "title": a.title,
                    "authors": "; ".join(a.authors),
                    "journal": a.journal,
                    "publication_date": a.publication_date,
                    "doi": a.doi,
                    "pmid": a.pmid,
                    "pmcid": a.pmcid,
                    "abstract": a.abstract,
                    "url": a.url,
                    "source_database": a.source_database,
                    "is_preprint": a.is_preprint,
                    "relevance_score": a.relevance_score,
                    "tags": ";".join(a.tags),
                }
            )

    return md_path, csv_path
