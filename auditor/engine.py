"""
Backward-compatible engine exports.

Primary invocation lives in `auditor.main`.
"""

from auditor.main import audit_invoice

__all__ = ["audit_invoice"]
