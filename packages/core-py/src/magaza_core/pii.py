"""Personal data masking applied before anything is written to logs or analytics.

Masks e-mail addresses, Turkish phone numbers, T.C. identity numbers (checksum validated) and payment
card numbers (Luhn validated). Raw text is only kept where the product needs it (session history).
"""

from __future__ import annotations

import logging
import re
from typing import Any

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_TCKN = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
_PHONE = re.compile(r"(?<![\w+])(?:\+?90[\s-]?)?\(?0?[2-5]\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _tckn_ok(n: str) -> bool:
    d = [int(c) for c in n]
    if d[0] == 0:
        return False
    d10 = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    return d10 == d[9] and sum(d[:10]) % 10 == d[10]


def mask_pii(text: str) -> str:
    def card(m: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", m.group())
        return "[kart]" if 13 <= len(digits) <= 19 and _luhn_ok(digits) else m.group()

    def tckn(m: re.Match[str]) -> str:
        return "[tc-kimlik]" if _tckn_ok(m.group()) else m.group()

    text = _EMAIL.sub("[e-posta]", text)
    text = _CARD.sub(card, text)
    text = _TCKN.sub(tckn, text)
    return _PHONE.sub("[telefon]", text)


def mask_payload(value: Any) -> Any:
    """Recursively masks strings inside dicts/lists (analytics payloads)."""
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: mask_payload(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [mask_payload(v) for v in value]
    return value


class PiiMaskingFilter(logging.Filter):
    """Logging filter: renders the message, masks it and drops the args."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_pii(record.getMessage())
        record.args = ()
        return True
