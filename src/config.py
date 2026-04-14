from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from src.utils import load_yaml


@dataclass
class Settings:
    crossref_mailto: str
    email_host: str
    email_port: int
    email_user: str
    email_password: str
    email_to: str
    lookback_days: int = 14
    strict_recent_publication: bool = True


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        crossref_mailto=os.getenv("CROSSREF_MAILTO", ""),
        email_host=os.getenv("EMAIL_HOST", ""),
        email_port=int(os.getenv("EMAIL_PORT", "0") or 0),
        email_user=os.getenv("EMAIL_USER", ""),
        email_password=os.getenv("EMAIL_PASSWORD", ""),
        email_to=os.getenv("EMAIL_TO", ""),
        lookback_days=int(os.getenv("MONITOR_LOOKBACK_DAYS", "14") or 14),
        strict_recent_publication=os.getenv("STRICT_RECENT_PUBLICATION", "true").lower() in {"1", "true", "yes"},
    )


def load_search_terms() -> Dict[str, List[str]]:
    return load_yaml(Path("config/search_terms.yaml"))


def load_queries() -> Dict[str, str]:
    raw = load_yaml(Path("config/queries.yaml"))
    return raw.get("pubmed_queries", {})
