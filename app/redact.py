"""PHI redaction at ingest.

The Brain stores rules and resolutions, never patient data. This pass strips the
identifier shapes that could leak in from pasted portal output or case notes:
labeled patient fields, member IDs, DOBs, SSNs, phone numbers. It is deliberately
aggressive — a redacted token costs nothing; a leaked identifier is disqualifying
at a healthcare company. See DATA.md for the full PHI posture.
"""
import re

_RULES: list[tuple[re.Pattern, str]] = [
    # Labeled fields: "Patient: Jane Doe", "Member name - John", "DOB: 01/02/1980"
    (re.compile(r"(?im)^(\s*(?:patient|member)(?:\s*name)?\s*[:\-]\s*).+$"), r"\1[REDACTED-NAME]"),
    (re.compile(r"(?i)\b(dob|date of birth|birth date)\s*[:\-]?\s*\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}"),
     r"\1: [REDACTED-DOB]"),
    # Member/subscriber IDs: "member id ABC123456", "subscriber #: 123456789"
    (re.compile(r"(?i)\b((?:member|subscriber|patient)\s*(?:id|number|#)\s*[:\-]?\s*)[A-Z0-9\-]{6,}"),
     r"\1[REDACTED-ID]"),
    # SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    # US phone numbers
    (re.compile(r"\b(?:\+1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b"), "[REDACTED-PHONE]"),
]


def redact(text: str) -> tuple[str, int]:
    """Return (clean_text, number_of_redactions)."""
    total = 0
    for pattern, repl in _RULES:
        text, n = pattern.subn(repl, text)
        total += n
    return text, total
