from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Article:
    title: str
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    publication_date: str = ""
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    abstract: str = ""
    url: str = ""
    source_database: str = ""
    is_preprint: bool = False
    category: str = ""
    relevance_score: int = 0
    tags: List[str] = field(default_factory=list)
