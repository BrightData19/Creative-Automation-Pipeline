from __future__ import annotations

import re
from typing import Dict, List


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


class PrivacyChecker:
    """Detects and masks PII in text to support data privacy by default."""

    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        if not text:
            return {"emails": [], "phones": [], "ssn": [], "cards": []}
        return {
            "emails": EMAIL_RE.findall(text) or [],
            "phones": PHONE_RE.findall(text) or [],
            "ssn": SSN_RE.findall(text) or [],
            "cards": CREDIT_CARD_RE.findall(text) or [],
        }

    def mask_text(self, text: str) -> str:
        if not text:
            return text
        masked = EMAIL_RE.sub(lambda m: self._mask(m.group(), keep=2), text)
        masked = PHONE_RE.sub(lambda m: self._mask(m.group(), keep=2), masked)
        masked = SSN_RE.sub(lambda m: self._mask(m.group(), keep=0), masked)
        masked = CREDIT_CARD_RE.sub(lambda m: self._mask_digits(m.group()), masked)
        return masked

    def _mask(self, s: str, keep: int = 2) -> str:
        s = s.strip()
        if len(s) <= keep:
            return "*" * len(s)
        return s[:keep] + "*" * (len(s) - keep)

    def _mask_digits(self, s: str) -> str:
        digits = re.sub(r"\D", "", s)
        if len(digits) <= 4:
            return "*" * len(digits)
        return "*" * (len(digits) - 4) + digits[-4:]

    def check_text_privacy(self, text: str) -> Dict[str, object]:
        found = self.detect_pii(text)
        total = sum(len(v) for v in found.values())
        return {
            "pii_found": total > 0,
            "pii_items": found,
            "compliance_score": 1.0 if total == 0 else max(0.6, 1.0 - 0.1 * total),
            "issues": [f"PII detected: {total} item(s)"] if total > 0 else [],
        }

