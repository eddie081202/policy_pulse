from __future__ import annotations

from auditor.entities import Bill, Exclusion, LineItem, Policy
from auditor.services.base_service import MatchResult


class KeywordSemanticMatcher:
    """
    Fast deterministic matcher for hackathon scaffolding.
    Replace this with an LLM-backed matcher when API keys are ready.
    """

    def match_line(self, line_item: LineItem, bill: Bill, policy: Policy) -> MatchResult:
        item_text = _normalize(line_item.item_name)
        item_tokens = set(item_text.split())

        exclusion = _find_exclusion_match(item_tokens, policy.exclusions)
        if exclusion is not None:
            return MatchResult(
                category_id=None,
                exclusion_id=exclusion.id,
                confidence=0.95,
                reason=f"Item matches exclusion: {exclusion.name}.",
            )

        best_category_id = None
        best_score = -1
        for category in policy.coverage_categories:
            candidate_text = _normalize(
                f"{category.name} {category.description} {line_item.category_hint}"
            )
            score = _token_overlap_score(item_text, candidate_text)
            if score > best_score:
                best_score = score
                best_category_id = category.id

        if best_category_id is None or best_score <= 0:
            return MatchResult(
                category_id=None,
                exclusion_id=None,
                confidence=0.2,
                reason="No strong policy category match found.",
            )

        confidence = min(0.99, 0.45 + (best_score * 0.15))
        return MatchResult(
            category_id=best_category_id,
            exclusion_id=None,
            confidence=confidence,
            reason=f"Best keyword similarity match score: {best_score}.",
        )


def _find_exclusion_match(item_tokens: set[str], exclusions: list[Exclusion]) -> Exclusion | None:
    for exclusion in exclusions:
        corpus = _normalize(f"{exclusion.name} {exclusion.text}")
        exclusion_tokens = set(corpus.split())
        overlap_tokens = item_tokens & exclusion_tokens
        # Reduce false positives by requiring stronger evidence for exclusions.
        if _is_strong_exclusion_match(overlap_tokens):
            return exclusion
    return None


def _token_overlap_score(a: str, b: str) -> int:
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    # Keep short medical acronyms like CT/MRI while still removing single letters.
    a_tokens = {t for t in a_tokens if len(t) > 1}
    b_tokens = {t for t in b_tokens if len(t) > 1}
    return len(a_tokens & b_tokens)


def _normalize(value: str) -> str:
    cleaned = []
    for ch in value.lower():
        cleaned.append(ch if ch.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def _is_strong_exclusion_match(overlap_tokens: set[str]) -> bool:
    if not overlap_tokens:
        return False
    stopwords = {
        "and",
        "for",
        "the",
        "with",
        "care",
        "service",
        "services",
        "medical",
        "hospital",
        "treatment",
    }
    informative = {t for t in overlap_tokens if t not in stopwords}
    if len(informative) >= 2:
        return True
    return any(len(t) >= 7 for t in informative)
