from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List



PUNCT_PATTERN = re.compile(r"[^\w\s]")
SPACE_PATTERN = re.compile(r"\s+")


def load_yaml(path: str | Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("PyYAML is required to read YAML config files.") from exc
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def normalize_title(title: str) -> str:
    lowered = title.lower().strip()
    no_punct = PUNCT_PATTERN.sub(" ", lowered)
    return SPACE_PATTERN.sub(" ", no_punct).strip()


def load_seen_ids(path: str | Path) -> Dict[str, List[str]]:
    p = Path(path)
    if not p.exists():
        return {"doi": [], "pmid": [], "pmcid": [], "title": []}
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for key in ["doi", "pmid", "pmcid", "title"]:
        data.setdefault(key, [])
    return data


def save_seen_ids(path: str | Path, data: Dict[str, List[str]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_publication_date(raw: str) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    candidates = [text.split(";")[0].split(" ")[0], text]
    for c in candidates:
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                dt = datetime.strptime(c, fmt).date()
                return dt
            except ValueError:
                continue
    return None


def is_within_days(raw_date: str, days: int, today: date | None = None) -> bool:
    parsed = parse_publication_date(raw_date)
    if parsed is None:
        return False
    now = today or date.today()
    lower = now.fromordinal(now.toordinal() - days)
    return lower <= parsed <= now
