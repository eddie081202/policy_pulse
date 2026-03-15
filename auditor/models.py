"""
Backward-compatible model exports.

Primary entity definitions now live in `auditor.entities`.
"""

from auditor.entities import (
    AppliedClause,
    AuditResult,
    AuditStatus,
    AuditSummary,
    Bill,
    CategoryUtilizationScore,
    Clause,
    CoverageCategory,
    Exclusion,
    InvoiceMeta,
    LineAuditResult,
    LineItem,
    PolicyPreference,
    PolicyComparisonReport,
    PolicyOptionScore,
    Policy,
    PolicyMeta,
    UpgradeRecommendation,
    UtilizationReport,
)

__all__ = [
    "AppliedClause",
    "AuditResult",
    "AuditStatus",
    "AuditSummary",
    "Bill",
    "CategoryUtilizationScore",
    "Clause",
    "CoverageCategory",
    "Exclusion",
    "InvoiceMeta",
    "LineAuditResult",
    "LineItem",
    "PolicyPreference",
    "PolicyComparisonReport",
    "PolicyOptionScore",
    "Policy",
    "PolicyMeta",
    "UpgradeRecommendation",
    "UtilizationReport",
]
