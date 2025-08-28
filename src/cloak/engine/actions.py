"""
Policy-driven text transformations for detected entities.

This module is responsible for the *second* stage of the pipeline:

  1) DETECT  — Find spans of sensitive data (regex, spaCy, transformers etc.)
  2) ACT     — Transform those spans using a *policy*:
               - mask         -> hide value but keep placeholder
               - drop         -> remove entirely
               - hash         -> irreversible, deterministic fingerprint
               - pseudonymize -> stable, human-friendly alias (e.g., Person_8F21B3C2)
               - none         -> do not modify

Why not put this into the detectors?
- Detectors focus on *what* exists in the text (span/type/confidence).
- Actions decide *how* to rewrite it, which is orthogonal and often user-configurable.

Security notes:
- 'hash' is *not* reversible. It's for linking identical values without exposing them.
- 'pseudonymize' generates non-reversible aliases using an HMAC with a salt.
  If you set CLOAK_SALT, aliases are stable across runs (good for referential integrity).
- 'drop' irreversibly removes the span (safest for secrets).
- 'mask' keeps text shape readable but hides the sensitive value.

Implementation detail:
- Replacements are applied from **right to left** (reverse-sorted by start index),
  so earlier replacements don't invalidate later character indices.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from typing import Callable, Dict, List

from ..config import Policy
from .pseudonymizer import pseudonymizer_from_env

# NOTE: We reference `Span` only for type hints. If you ever see circular-import issues,
# you can avoid importing and just use quoted type names thanks to
# `from __future__ import annotations`.
from ..engine.pipeline import Span  # reuse the unified Span dataclass


# ------------------------------
# Masking helpers (per-entity)
# ------------------------------

MaskToken = "[REDACTED]"


def _mask_email(s: str) -> str:
    """
    Mask the *user* part of an email, keep domain intact.
    Examples:
      'alice@example.com' -> 'a***@example.com'
      'x@d.com'           -> '*@d.com'
    Rationale:
      Keeps context (which domain) without revealing identity.
    """
    if "@" not in s:
        return MaskToken
    user, domain = s.split("@", 1)
    if not user:
        return f"* @{domain}"
    if len(user) <= 1:
        return f"*@{domain}"
    return f"{user[0]}***@{domain}"


def _mask_phone(s: str) -> str:
    """
    Mask all phone digits except the last two. Preserve punctuation/spacing.
    Example:
      '+1 202-555-0147' -> '+* ***-***-**47'
    Rationale:
      Keeps format and approximate length without revealing the number.
    """
    digits = [c for c in s if c.isdigit()]
    if not digits:
        return MaskToken

    keep_tail = 2
    tail_start = max(0, len(digits) - keep_tail)

    out = []
    seen = 0
    for ch in s:
        if ch.isdigit():
            if seen < tail_start:
                out.append("*")
            else:
                # Map the last N digits 1:1 from the tail we kept
                idx_in_tail = seen - tail_start
                out.append(digits[tail_start + idx_in_tail])
            seen += 1
        else:
            out.append(ch)
    return "".join(out)


def _mask_ip(s: str) -> str:
    """
    Simple IPv4 masking: blank the last octet.
    Example:
      '192.168.0.42' -> '192.168.0.x'
    """
    parts = s.split(".")
    if len(parts) == 4:
        parts[-1] = "x"
        return ".".join(parts)
    # For IPv6 or unknown forms use generic token;
    # specialized IPv6 masking could be added later.
    return MaskToken


def _mask_generic(_: str) -> str:
    """
    Generic mask when we don't have a smarter strategy for the type.
    """
    return MaskToken


# ------------------------------
# Hashing & pseudonymization
# ------------------------------

def _hash_value(entity_type: str, s: str, salt: str | None = None) -> str:
    """
    Produce a deterministic, irreversible fingerprint of the value.

    We use: SHA-256 over (salt | entity_type | raw_value), truncated for readability.
    - Deterministic: same input -> same output.
    - Cross-run stability: set CLOAK_SALT (or pass `salt`) to link identical values
      across executions *without* storing the original.

    Output looks like: 'hash_3a5f09b1d2ab'
    """
    salt = salt or os.getenv("CLOAK_SALT", "")
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(b"|")
    h.update(entity_type.encode("utf-8"))
    h.update(b"|")
    h.update(s.encode("utf-8"))
    return f"hash_{h.hexdigest()[:12]}"


# ------------------------------
# ActionEngine
# ------------------------------

@dataclass
class ActionEngine:
    """
    Apply policy-defined actions to detected spans.

    Typical usage:
        engine = ActionEngine(policy=cfg.policy)
        new_text = engine.apply(text, spans)

    The engine:
      - Chooses the transformation per span (based on span.type and policy.actions[type]).
      - Applies replacements from right to left to keep indices valid.
      - Uses per-type maskers where appropriate (email/phone/ip).
      - Uses pseudonymization (HMAC+salt) for stable, human-readable aliases.
    """
    policy: Policy
    salt: str | None = None  # optional override; CLOAK_SALT env var is preferred

    def __post_init__(self) -> None:
        # Pseudonymizer: aliases like 'Person_8F21B3C2', non-reversible.
        # If CLOAK_SALT is set, aliases are stable across runs. If not, they
        # are deterministic within the process (using a random default salt).
        self._pseudonymizer = pseudonymizer_from_env(default_salt=(self.salt or "").encode("utf-8"))

        # Per-type masking strategies. These preserve some structure while hiding sensitive parts.
        # You can add more specialized maskers over time (e.g., partial IBAN mask).
        self._maskers: Dict[str, Callable[[str], str]] = {
            "EMAIL": _mask_email,
            "PHONE": _mask_phone,
            "IP": _mask_ip,
            "IPV6": _mask_generic,       # TODO: IPv6-specific strategy if needed
            "CREDIT_CARD": _mask_generic,
            "SSN": _mask_generic,
            "IBAN": _mask_generic,
            "SECRET": _mask_generic,
            "API_KEY": _mask_generic,
        }

    def _replacement_for(self, sp: Span) -> str | None:
        """
        Decide the replacement for a single span according to the policy.

        Returns:
            - A string replacement (possibly empty string for 'drop')
            - None -> action 'none' (keep original text)

        Policy precedence:
          - none         : leave as-is (useful for DATE/URL, etc.)
          - mask         : obscure the value, keep context
          - drop         : remove entirely (strongest; good for secrets)
          - hash         : irreversible fingerprint (link equal values)
          - pseudonymize : stable alias, human-friendly
        """
        action = self.policy.actions.get(sp.type, "none")

        if action == "none":
            return None

        if action == "mask":
            fn = self._maskers.get(sp.type, _mask_generic)
            return fn(sp.text)

        if action == "drop":
            return ""  # remove all characters of the span

        if action == "hash":
            return _hash_value(sp.type, sp.text, self.salt)

        if action == "pseudonymize":
            # Produces EntType_HASH like 'Person_8F21B3C2'
            return self._pseudonymizer.alias(sp.type, sp.text)

        # Unknown action keyword: be conservative and hide the value
        return MaskToken

    def apply(self, text: str, spans: List[Span]) -> str:
        """
        Apply the policy actions to all spans within `text`.

        Implementation detail:
        - Replacements happen from rightmost to leftmost span to keep indices valid.
        - If action == 'none' for a span, we skip it (the original text remains).

        Args:
            text: Original input string
            spans: List of detected spans (start/end indices refer to `text`)

        Returns:
            A new string with all policy-driven transformations applied.
        """
        if not spans:
            return text

        # Convert to a list for in-place slice replacement (efficient for many edits).
        buff = list(text)

        # Sort by start descending so earlier edits don't shift later indices.
        for sp in sorted(spans, key=lambda s: s.start, reverse=True):
            repl = self._replacement_for(sp)
            if repl is None:
                # Action 'none' -> keep original text
                continue
            # Replace the slice [start:end) with the replacement characters.
            buff[sp.start:sp.end] = list(repl)

        return "".join(buff)
