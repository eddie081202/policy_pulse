"""
Backward-compatible matcher exports.

Primary matcher/service definitions now live in `auditor.services`.
"""

from auditor.services.auditor_agent_service import (
    KeywordSemanticMatcher,
    MatchResult,
    SemanticMatcher,
)

__all__ = ["KeywordSemanticMatcher", "MatchResult", "SemanticMatcher"]
