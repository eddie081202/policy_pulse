from __future__ import annotations

import re
import uuid
from statistics import mean
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..entities import JudgeEntity

PreferenceMode = Literal["price", "policy", "no_preference"]


class JudgeWeights(BaseModel):
    price_score: float
    policy_utilization_score: float
    coverage_score: float
    relative_policy_quality_score: float


class ScoreBreakdown(BaseModel):
    price_score: float
    policy_utilization_score: float
    coverage_score: float
    relative_policy_quality_score: float


class JudgeSource(BaseModel):
    file_name: str | None = None
    category: str | None = None


class DeltaVsCurrent(BaseModel):
    final_score_delta: float
    premium_delta: float | None = None
    deductible_delta: float | None = None
    coverage_gap_delta: float | None = None


class SourceReference(BaseModel):
    source_file: str
    source_path: str
    chunk_id: str


class CurrentPolicyResult(BaseModel):
    policy_id: str | None = None
    policy_name: str | None = None
    source: JudgeSource
    score_breakdown: ScoreBreakdown
    final_weighted_score: float
    verdict: Literal["excellent_fit", "good_fit", "needs_attention", "poor_fit"]
    key_findings: list[str]


class AlternativeResult(BaseModel):
    rank: int
    policy_id: str
    policy_name: str
    category: str | None = None
    final_weighted_score: float
    score_breakdown: ScoreBreakdown
    delta_vs_current: DeltaVsCurrent
    why_better: list[str]
    source_references: list[SourceReference]


class JudgeRecommendation(BaseModel):
    mode: PreferenceMode
    summary: str
    actions: list[str]


class JudgeExplanations(BaseModel):
    methodology: str
    confidence: float
    limitations: list[str]


class JudgeResult(BaseModel):
    request_id: str
    preference: PreferenceMode
    total_score: float
    weights: JudgeWeights
    current_policy: CurrentPolicyResult
    alternatives: list[AlternativeResult]
    recommendation: JudgeRecommendation
    explanations: JudgeExplanations


class CandidatePolicy(BaseModel):
    policy_id: str
    policy_name: str
    category: str | None = None
    premium_monthly: float | None = None
    deductible_individual: float | None = None
    coverage_keywords: list[str] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)


class JudgeInput(BaseModel):
    parser_payload: dict[str, Any]
    rag_payload: dict[str, Any]
    preference: PreferenceMode = "no_preference"


class JudgeService:
    def __init__(self, entity: JudgeEntity):
        self.entity = entity

    def evaluate(self, payload: JudgeInput) -> JudgeResult:
        bill_fields = (payload.parser_payload.get("bill_payload") or {}).get("extracted_fields") or {}
        contract_fields = (payload.parser_payload.get("contract_payload") or {}).get("extracted_fields") or {}
        current_contract_meta = contract_fields.get("meta") or {}
        rag_candidates = self._build_candidates(payload.rag_payload)

        current_policy = self._current_policy_candidate(payload.parser_payload, payload.rag_payload)
        all_candidates = [current_policy] + rag_candidates

        if not all_candidates:
            all_candidates = [current_policy]

        scored_candidates = [
            (candidate, self._score_candidate(candidate, current_policy, bill_fields, contract_fields))
            for candidate in all_candidates
        ]
        scored_candidates.sort(key=lambda item: item[1]["final_weighted_score"], reverse=True)

        current_scored = next((item for item in scored_candidates if item[0].policy_id == current_policy.policy_id), scored_candidates[0])
        current_result = self._build_current_policy_result(current_scored, payload.parser_payload, payload.rag_payload)

        alternatives = self._rank_alternatives(
            scored_candidates=scored_candidates,
            current_policy=current_policy,
            current_final=current_result.final_weighted_score,
            current_meta=current_contract_meta,
            preference=payload.preference,
        )

        recommendation = self._build_recommendation(payload.preference, current_result, alternatives)

        confidence = self._estimate_confidence(payload.rag_payload, alternatives)
        limitations = self._collect_limitations(payload.parser_payload, payload.rag_payload)

        return JudgeResult(
            request_id=str(uuid.uuid4()),
            preference=payload.preference,
            total_score=current_result.final_weighted_score,
            weights=JudgeWeights(
                price_score=self.entity.price_weight,
                policy_utilization_score=self.entity.policy_utilization_weight,
                coverage_score=self.entity.coverage_weight,
                relative_policy_quality_score=self.entity.relative_policy_quality_weight,
            ),
            current_policy=current_result,
            alternatives=alternatives,
            recommendation=recommendation,
            explanations=JudgeExplanations(
                methodology=(
                    "Weighted multi-factor scoring using bill usage signals, current policy fields, "
                    "and vectorstore-matched alternatives."
                ),
                confidence=confidence,
                limitations=limitations,
            ),
        )

    def _current_policy_candidate(self, parser_payload: dict[str, Any], rag_payload: dict[str, Any]) -> CandidatePolicy:
        contract_payload = parser_payload.get("contract_payload") or {}
        fields = contract_payload.get("extracted_fields") or {}
        meta = fields.get("meta") or {}
        source = {
            "source_file": contract_payload.get("file_name") or "uploaded_contract",
            "source_path": contract_payload.get("file_name") or "uploaded_contract",
            "chunk_id": "current",
        }
        return CandidatePolicy(
            policy_id=str(meta.get("policy_number") or meta.get("policy_id") or "current_policy"),
            policy_name=str(meta.get("policy_name") or contract_payload.get("file_name") or "Current Policy"),
            category=self._infer_category(rag_payload),
            premium_monthly=self._to_float(meta.get("premium_monthly")),
            deductible_individual=self._to_float(meta.get("individual_deductible") or meta.get("deductible_individual")),
            coverage_keywords=self._coverage_keywords_from_contract(fields),
            source_references=[SourceReference(**source)],
        )

    def _build_candidates(self, rag_payload: dict[str, Any]) -> list[CandidatePolicy]:
        matches = rag_payload.get("matched_candidates") or []
        if not matches:
            matches = self._fallback_candidates_from_documents(rag_payload.get("matched_documents") or [])

        candidates: list[CandidatePolicy] = []
        for idx, match in enumerate(matches):
            references = []
            for ref in match.get("source_references") or []:
                try:
                    references.append(SourceReference(**ref))
                except Exception:
                    continue
            if not references and match.get("source_file"):
                references.append(
                    SourceReference(
                        source_file=str(match.get("source_file")),
                        source_path=str(match.get("source_path") or match.get("source_file")),
                        chunk_id=str(match.get("chunk_id") or idx),
                    )
                )
            candidates.append(
                CandidatePolicy(
                    policy_id=str(match.get("policy_id") or f"candidate_{idx}"),
                    policy_name=str(match.get("policy_name") or match.get("source_file") or f"Candidate {idx+1}"),
                    category=match.get("category"),
                    premium_monthly=self._to_float(match.get("premium_monthly")),
                    deductible_individual=self._to_float(match.get("deductible_individual")),
                    coverage_keywords=[str(x) for x in (match.get("coverage_keywords") or [])],
                    source_references=references,
                )
            )
        return candidates

    def _fallback_candidates_from_documents(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for doc in docs:
            source_file = str(doc.get("source_file") or "unknown_source")
            key = source_file
            text = str(doc.get("text") or "")
            premium = self._extract_metric(text, r"premium[^0-9]*(\d+(?:\.\d+)?)")
            deductible = self._extract_metric(text, r"deductible[^0-9]*(\d+(?:\.\d+)?)")
            coverage_keywords = self._extract_coverage_keywords(text)
            existing = grouped.setdefault(
                key,
                {
                    "policy_id": key,
                    "policy_name": source_file,
                    "category": doc.get("category"),
                    "premium_monthly_values": [],
                    "deductible_values": [],
                    "coverage_keywords": set(),
                    "source_references": [],
                },
            )
            if premium is not None:
                existing["premium_monthly_values"].append(premium)
            if deductible is not None:
                existing["deductible_values"].append(deductible)
            existing["coverage_keywords"].update(coverage_keywords)
            existing["source_references"].append(
                {
                    "source_file": source_file,
                    "source_path": str(doc.get("source_path") or source_file),
                    "chunk_id": str(doc.get("chunk_id") or ""),
                }
            )

        output = []
        for item in grouped.values():
            output.append(
                {
                    "policy_id": item["policy_id"],
                    "policy_name": item["policy_name"],
                    "category": item["category"],
                    "premium_monthly": mean(item["premium_monthly_values"]) if item["premium_monthly_values"] else None,
                    "deductible_individual": mean(item["deductible_values"]) if item["deductible_values"] else None,
                    "coverage_keywords": sorted(item["coverage_keywords"]),
                    "source_references": item["source_references"],
                }
            )
        return output

    def _score_candidate(
        self,
        candidate: CandidatePolicy,
        current_policy: CandidatePolicy,
        bill_fields: dict[str, Any],
        contract_fields: dict[str, Any],
    ) -> dict[str, float]:
        price_score = self._price_score(candidate, current_policy)
        utilization_score = self._policy_utilization_score(candidate, bill_fields)
        coverage_score = self._coverage_score(candidate, contract_fields)
        relative_quality_score = self._relative_policy_quality_score(candidate, current_policy)
        final = (
            self.entity.price_weight * price_score
            + self.entity.policy_utilization_weight * utilization_score
            + self.entity.coverage_weight * coverage_score
            + self.entity.relative_policy_quality_weight * relative_quality_score
        )
        return {
            "price_score": round(price_score, 4),
            "policy_utilization_score": round(utilization_score, 4),
            "coverage_score": round(coverage_score, 4),
            "relative_policy_quality_score": round(relative_quality_score, 4),
            "final_weighted_score": round(max(0.0, min(1.0, final)), 4),
        }

    def _price_score(self, candidate: CandidatePolicy, current_policy: CandidatePolicy) -> float:
        current = current_policy.premium_monthly
        cand = candidate.premium_monthly
        if current is None or cand is None or current <= 0:
            return 0.5
        ratio = cand / current
        if ratio <= 0.8:
            return 1.0
        if ratio <= 1.0:
            return 0.8 + (1.0 - ratio) * 1.0
        if ratio <= 1.2:
            return max(0.4, 0.8 - (ratio - 1.0) * 2.0)
        return 0.2

    def _policy_utilization_score(self, candidate: CandidatePolicy, bill_fields: dict[str, Any]) -> float:
        line_items = bill_fields.get("line_items") or []
        if not line_items:
            return 0.5
        bill_terms = " ".join(str(item.get("item_name", "")).lower() for item in line_items)
        hits = 0
        for kw in candidate.coverage_keywords:
            if kw and kw.lower() in bill_terms:
                hits += 1
        return max(0.2, min(1.0, hits / max(1, len(candidate.coverage_keywords) or 1)))

    def _coverage_score(self, candidate: CandidatePolicy, contract_fields: dict[str, Any]) -> float:
        current_terms = set(self._coverage_keywords_from_contract(contract_fields))
        candidate_terms = set(kw.lower() for kw in candidate.coverage_keywords if kw)
        if not current_terms and not candidate_terms:
            return 0.5
        if not current_terms:
            return 0.4
        overlap = len(current_terms.intersection(candidate_terms))
        union = len(current_terms.union(candidate_terms)) or 1
        return max(0.2, min(1.0, overlap / union))

    def _relative_policy_quality_score(self, candidate: CandidatePolicy, current_policy: CandidatePolicy) -> float:
        candidate_deductible = candidate.deductible_individual
        current_deductible = current_policy.deductible_individual
        if candidate_deductible is None or current_deductible is None or current_deductible <= 0:
            return 0.5
        ratio = candidate_deductible / current_deductible
        if ratio <= 0.7:
            return 1.0
        if ratio <= 1.0:
            return 0.8 + (1.0 - ratio) * 0.7
        if ratio <= 1.25:
            return max(0.35, 0.8 - (ratio - 1.0) * 1.8)
        return 0.2

    def _build_current_policy_result(
        self,
        current_scored: tuple[CandidatePolicy, dict[str, float]],
        parser_payload: dict[str, Any],
        rag_payload: dict[str, Any],
    ) -> CurrentPolicyResult:
        candidate, score = current_scored
        final = score["final_weighted_score"]
        if final >= 0.8:
            verdict = "excellent_fit"
        elif final >= 0.65:
            verdict = "good_fit"
        elif final >= 0.45:
            verdict = "needs_attention"
        else:
            verdict = "poor_fit"
        findings = [
            f"Weighted score is {final:.2f} using configured judge weights.",
            f"Price sub-score is {score['price_score']:.2f}; coverage sub-score is {score['coverage_score']:.2f}.",
        ]
        if (rag_payload.get("discrepancies") or []):
            findings.append("RAG audit found discrepancies; review recommendation before making policy changes.")
        contract_payload = parser_payload.get("contract_payload") or {}
        return CurrentPolicyResult(
            policy_id=candidate.policy_id,
            policy_name=candidate.policy_name,
            source=JudgeSource(
                file_name=contract_payload.get("file_name"),
                category=self._infer_category(rag_payload),
            ),
            score_breakdown=ScoreBreakdown(
                price_score=score["price_score"],
                policy_utilization_score=score["policy_utilization_score"],
                coverage_score=score["coverage_score"],
                relative_policy_quality_score=score["relative_policy_quality_score"],
            ),
            final_weighted_score=final,
            verdict=verdict,
            key_findings=findings,
        )

    def _rank_alternatives(
        self,
        scored_candidates: list[tuple[CandidatePolicy, dict[str, float]]],
        current_policy: CandidatePolicy,
        current_final: float,
        current_meta: dict[str, Any],
        preference: PreferenceMode,
    ) -> list[AlternativeResult]:
        filtered = [item for item in scored_candidates if item[0].policy_id != current_policy.policy_id]

        def sort_key(item: tuple[CandidatePolicy, dict[str, float]]) -> tuple[float, float]:
            cand, score = item
            if preference == "price":
                premium = cand.premium_monthly if cand.premium_monthly is not None else 10**6
                return (-score["final_weighted_score"], -premium)
            if preference == "policy":
                coverage = score["coverage_score"] + score["relative_policy_quality_score"]
                return (coverage, score["final_weighted_score"])
            return (score["final_weighted_score"], score["coverage_score"])

        reverse = preference != "price"
        filtered.sort(key=sort_key, reverse=reverse)

        output: list[AlternativeResult] = []
        current_premium = self._to_float(current_meta.get("premium_monthly"))
        current_deductible = self._to_float(current_meta.get("individual_deductible") or current_meta.get("deductible_individual"))
        for rank, (candidate, score) in enumerate(filtered[: self.entity.top_alternatives], start=1):
            premium_delta = None
            if current_premium is not None and candidate.premium_monthly is not None:
                premium_delta = round(candidate.premium_monthly - current_premium, 2)
            deductible_delta = None
            if current_deductible is not None and candidate.deductible_individual is not None:
                deductible_delta = round(candidate.deductible_individual - current_deductible, 2)
            why_better = self._why_better(candidate, score, preference, premium_delta, deductible_delta)
            output.append(
                AlternativeResult(
                    rank=rank,
                    policy_id=candidate.policy_id,
                    policy_name=candidate.policy_name,
                    category=candidate.category,
                    final_weighted_score=score["final_weighted_score"],
                    score_breakdown=ScoreBreakdown(
                        price_score=score["price_score"],
                        policy_utilization_score=score["policy_utilization_score"],
                        coverage_score=score["coverage_score"],
                        relative_policy_quality_score=score["relative_policy_quality_score"],
                    ),
                    delta_vs_current=DeltaVsCurrent(
                        final_score_delta=round(score["final_weighted_score"] - current_final, 4),
                        premium_delta=premium_delta,
                        deductible_delta=deductible_delta,
                        coverage_gap_delta=round(score["coverage_score"] - 0.5, 4),
                    ),
                    why_better=why_better,
                    source_references=candidate.source_references,
                )
            )
        return output

    def _build_recommendation(
        self,
        preference: PreferenceMode,
        current: CurrentPolicyResult,
        alternatives: list[AlternativeResult],
    ) -> JudgeRecommendation:
        if not alternatives:
            return JudgeRecommendation(
                mode=preference,
                summary="No strong alternatives found from retrieved contracts.",
                actions=[
                    "Upload more policy documents to improve recommendation quality.",
                    "Review current policy exclusions and deductible manually.",
                ],
            )
        top = alternatives[0]
        if preference == "price":
            summary = f"Best price-oriented option is {top.policy_name} with stronger overall score."
            actions = [
                "Compare monthly premium and out-of-pocket max with your current policy.",
                "Confirm equivalent benefits for your most frequent bill line items.",
            ]
        elif preference == "policy":
            summary = f"Best policy-quality option is {top.policy_name} with better coverage/quality profile."
            actions = [
                "Review exclusions and deductible structure in the top recommendation.",
                "Validate provider network fit before switching.",
            ]
        else:
            summary = f"Top balanced recommendation is {top.policy_name} based on weighted aggregate score."
            actions = [
                "Review score breakdown for current vs top alternatives.",
                "Shortlist the top 2 alternatives for side-by-side policy review.",
            ]
        if top.final_weighted_score <= current.final_weighted_score:
            summary = "Current policy remains competitive against retrieved alternatives."
            actions = [
                "Keep current policy and monitor future bill utilization.",
                "Re-run the judge after uploading additional contract alternatives.",
            ]
        return JudgeRecommendation(mode=preference, summary=summary, actions=actions)

    def _estimate_confidence(self, rag_payload: dict[str, Any], alternatives: list[AlternativeResult]) -> float:
        base = self._to_float(rag_payload.get("confidence")) or 0.6
        if alternatives:
            base = min(1.0, base + 0.1)
        return round(base, 4)

    def _collect_limitations(self, parser_payload: dict[str, Any], rag_payload: dict[str, Any]) -> list[str]:
        notes = []
        bill = parser_payload.get("bill_payload") or {}
        contract = parser_payload.get("contract_payload") or {}
        if (bill.get("validation_warnings") or []):
            notes.append("Bill parser returned validation warnings; some fields may need manual review.")
        if (contract.get("validation_warnings") or []):
            notes.append("Contract parser returned validation warnings; policy field quality may be reduced.")
        if not (rag_payload.get("matched_documents") or []):
            notes.append("No matched documents were retrieved from the vectorstore.")
        if not notes:
            notes.append("No major limitations detected from current inputs.")
        return notes

    def _why_better(
        self,
        candidate: CandidatePolicy,
        score: dict[str, float],
        preference: PreferenceMode,
        premium_delta: float | None,
        deductible_delta: float | None,
    ) -> list[str]:
        reasons = [
            f"Final weighted score: {score['final_weighted_score']:.2f}.",
            f"Coverage score: {score['coverage_score']:.2f}, utilization score: {score['policy_utilization_score']:.2f}.",
        ]
        if premium_delta is not None:
            direction = "lower" if premium_delta < 0 else "higher"
            reasons.append(f"Monthly premium is {abs(premium_delta):.2f} {direction} than current policy.")
        if deductible_delta is not None:
            direction = "lower" if deductible_delta < 0 else "higher"
            reasons.append(f"Deductible is {abs(deductible_delta):.2f} {direction} than current policy.")
        if preference == "price":
            reasons.append("Ranked with price preference while enforcing coverage/utilization signal.")
        elif preference == "policy":
            reasons.append("Ranked with policy-quality preference against deductible/coverage indicators.")
        else:
            reasons.append("Ranked by balanced weighted scoring.")
        return reasons

    def _coverage_keywords_from_contract(self, contract_fields: dict[str, Any]) -> list[str]:
        categories = contract_fields.get("coverage_categories") or []
        keywords = []
        for item in categories:
            if isinstance(item, dict):
                name = item.get("name")
                if name:
                    keywords.append(str(name).lower())
        return sorted(set(keywords))

    def _extract_coverage_keywords(self, text: str) -> list[str]:
        known = [
            "primary care",
            "emergency room",
            "prescription",
            "dental",
            "vision",
            "inpatient",
            "outpatient",
            "specialist",
            "preventive",
        ]
        lower = text.lower()
        return [kw for kw in known if kw in lower]

    def _extract_metric(self, text: str, pattern: str) -> float | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        return self._to_float(match.group(1))

    def _infer_category(self, rag_payload: dict[str, Any]) -> str | None:
        for doc in rag_payload.get("matched_documents") or []:
            category = doc.get("category")
            if category:
                return str(category)
        return None

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).strip().replace(",", "")
        if text.endswith("%"):
            text = text[:-1]
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

