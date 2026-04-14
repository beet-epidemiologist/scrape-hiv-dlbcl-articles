from __future__ import annotations

from typing import Dict, List

from src.models import Article


def _contains_any(text: str, terms: List[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def score_and_tag(article: Article, terms: Dict[str, List[str]]) -> Article:
    title = article.title or ""
    abstract = article.abstract or ""
    full_text = f"{title} {abstract}".lower()

    hiv_terms = terms.get("HIV_TERMS", []) + terms.get("AIDS_LYMPHOMA_TERMS", [])
    dlbcl_terms = terms.get("DLBCL_TERMS", [])
    therapy_terms = terms.get("THERAPY_TERMS", [])
    outcome_terms = terms.get("OUTCOME_TERMS", [])
    review_terms = terms.get("REVIEW_GUIDELINE_TERMS", [])

    score = 0
    tags: set[str] = set()

    if _contains_any(title, hiv_terms):
        score += 4
    if _contains_any(title, dlbcl_terms):
        score += 4
    if _contains_any(abstract, hiv_terms):
        score += 2
    if _contains_any(abstract, dlbcl_terms):
        score += 2
    if _contains_any(full_text, therapy_terms):
        score += 2
        tags.add("treatment")
    if _contains_any(full_text, ["drug interaction", "drug-drug interaction", "pharmacokinetic", "cyp3a"]):
        tags.add("drug_interaction")
    if _contains_any(full_text, outcome_terms):
        score += 1
        tags.add("prognosis")
    if _contains_any(full_text, ["incidence", "prevalence", "epidemiology"]):
        tags.add("epidemiology")
    if _contains_any(full_text, review_terms):
        score += 1
        tags.add("review_guideline")

    if "lymphoma" in full_text and not _contains_any(full_text, dlbcl_terms):
        score -= 3

    animal_terms = ["murine", "mouse", "mice", "canine", "dog", "feline"]
    human_terms = ["patient", "human", "cohort", "case", "trial"]
    if _contains_any(full_text, animal_terms) and not _contains_any(full_text, human_terms):
        score -= 3

    if article.is_preprint:
        tags.add("preprint")

    article.relevance_score = score
    article.tags = sorted(tags)
    return article
