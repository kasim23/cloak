"""
Lightweight validators and normalizers used by the regex backend.

Why this file exists
--------------------
Regex by itself often matches *too much* (e.g., any long digit string looks like a
credit card or an IBAN). These functions provide cheap, deterministic checks that
dramatically reduce false positives without requiring ML models.

Design principles
-----------------
- **Pure functions**: easy to test and reason about.
- **Fast**: O(n) over the candidate string; safe for large inputs.
- **Composable**: the regex backend can apply 0..N normalizers *then* 0..N validators.
"""

from __future__ import annotations


def _digits_only(s: str) -> str:
    """
    Return only the digit characters from a string.

    Used by Luhn so that inputs like "4111-1111 1111-1111" normalize to "4111111111111111".
    """
    return "".join(ch for ch in s if ch.isdigit())


def normalize_spaces_dashes(s: str) -> str:
    """
    Remove spaces and dashes from a string.

    Normalization step used before validation so rules can accept user-friendly
    formats (e.g., hyphenated credit card numbers or spaced IBANs) while validators
    operate on a canonical representation.
    """
    return s.replace(" ", "").replace("-", "")


def luhn_ok(s: str) -> bool:
    """
    Validate a string using the Luhn checksum (a.k.a. "mod 10").

    Luhn is used by most credit card numbers. It rejects the overwhelming majority
    of random digit strings. This is a *huge* false-positive reducer when paired
    with permissive digit-matching regex.

    Args:
        s: Candidate string (may include spaces/dashes).

    Returns:
        True if the digits pass Luhn; False otherwise.
    """
    n = _digits_only(s)
    # Typical card lengths: 13..19 digits.
    if not (13 <= len(n) <= 19):
        return False

    total = 0
    # Process digits from right to left; double every second digit.
    for i, ch in enumerate(reversed(n)):
        d = ord(ch) - 48  # '0' -> 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9  # sum of digits for doubled value (e.g., 8*2 -> 16 -> 1+6 -> 7)
        total += d

    return (total % 10) == 0


def iban_ok(s: str) -> bool:
    """
    Validate an IBAN using the official mod-97 algorithm.

    Steps:
      1) Strip spaces and uppercase.
      2) Move the first 4 chars to the end.
      3) Replace letters A..Z with 10..35.
      4) Interpret the result as a big integer and compute mod 97.
      5) A valid IBAN yields remainder 1.

    This rejects random alphanumeric strings that *look* like IBANs.

    Args:
        s: Candidate string (may include spaces).

    Returns:
        True if IBAN is valid; False otherwise.
    """
    s = s.replace(" ", "").upper()
    # IBAN lengths vary by country; global min/max bounds below.
    if not (15 <= len(s) <= 34):
        return False

    # Rotate first four characters to the end per ISO 13616.
    rearr = s[4:] + s[:4]

    # Convert letters to numbers (A=10, B=11, ..., Z=35).
    conv_chunks = []
    for ch in rearr:
        if ch.isdigit():
            conv_chunks.append(ch)
        elif ch.isalpha():
            conv_chunks.append(str(ord(ch) - 55))  # ord('A') == 65 -> 10
        else:
            # Disallow punctuation or other characters.
            return False

    num = "".join(conv_chunks)

    # Compute mod 97 in manageable chunks to avoid huge integers.
    # We carry the remainder forward in decimal string form.
    rem = 0
    for i in range(0, len(num), 9):
        rem = int(str(rem) + num[i : i + 9]) % 97

    return rem == 1