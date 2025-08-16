"""
Regex-based structured entity detection.

What this does
--------------
- Loads YAML "rule packs" (PII, Secrets, Network) that define regex patterns.
- Compiles those patterns and applies optional **normalizers** (e.g., strip dashes)
  and **validators** (e.g., Luhn for credit cards, IBAN mod-97).
- Emits normalized `Span` records suitable for merging with ML/NLP detectors.

Why a regex backend?
--------------------
Structured identifiers (EMAIL, CREDIT_CARD, IBAN, IP, API keys...) are best found
using deterministic patterns. Paired with cheap validators, this is fast, precise,
and explainable—ideal for privacy/security tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple
import re
import yaml
from importlib import resources

from .validators import luhn_ok, iban_ok, normalize_spaces_dashes


# ---- Data model returned to the pipeline -------------------------------------------------

@dataclass
class Span:
    """
    A detected region in text.

    Offsets (start/end) are character indices into the original text so downstream
    steps can highlight or replace text precisely.

    Attributes:
        start: Start character offset (inclusive).
        end:   End character offset (exclusive).
        text:  Raw matched text slice (pre-normalization).
        type:  Canonical entity type (e.g., 'EMAIL', 'CREDIT_CARD').
        confidence: Backend-assigned confidence (regex defaults are high).
    """
    start: int
    end: int
    text: str
    type: str
    confidence: float


# ---- Registry of named normalizers/validators --------------------------------------------

# Map validator names (as used in YAML) to callables.
_VALIDATORS: Dict[str, Callable[[str], bool]] = {
    "luhn": luhn_ok,  # e.g., CREDIT_CARD
    "iban": iban_ok,  # e.g., IBAN
}

# Map normalizer names (as used in YAML) to callables.
_NORMALIZERS: Dict[str, Callable[[str], str]] = {
    "strip_spaces_dashes": normalize_spaces_dashes,
}


# ---- Backend -----------------------------------------------------------------------------

class RegexBackend:
    """
    Load rule packs and run compiled regex against input text.

    Rule packs live under `cloak/detect/rulesets/` and are selected by the caller
    via constructor flags. Each rule can specify:
      - regex:       the pattern string
      - flags:       optional list of flags ["I", "M", "S"]
      - normalize:   names of normalizers to apply before validation
      - validators:  names of validators to gate the match (reduce FPs)
      - confidence:  float score assigned to matches from this rule
      - priority:    reserved for future use (e.g., override order)
      - type:        override the emitted entity type (defaults to YAML key)
    """

    def __init__(
        self,
        use_pii: bool = True,
        use_secrets: bool = True,
        use_network: bool = True,
    ) -> None:
        self.rules: List[Tuple[str, re.Pattern, Dict[str, Any]]] = []

        # Pick the YAML files to load based on constructor toggles.
        packs: List[Tuple[str, str]] = []
        if use_pii:
            packs.append(("cloak.detect.rulesets", "pii.yaml"))
        if use_secrets:
            packs.append(("cloak.detect.rulesets", "secrets.yaml"))
        if use_network:
            packs.append(("cloak.detect.rulesets", "network.yaml"))

        # Load and compile each pack into a list of (key, compiled_regex, meta) tuples.
        for pkg, fname in packs:
            text = resources.files(pkg).joinpath(fname).read_text()
            data = yaml.safe_load(text) or {}
            for key, spec in (data.get("patterns", {}) or {}).items():
                compiled = self._compile_rule(key, spec)
                if compiled:
                    self.rules.append(compiled)

    # -- Compilation helpers ----------------------------------------------------------------

    def _compile_rule(
        self, key: str, spec: Any
    ) -> Tuple[str, re.Pattern, Dict[str, Any]] | None:
        """
        Turn a YAML rule into a compiled regex and a metadata dict.

        Supports two YAML shapes:
          1) simple string  -> interpreted as the regex, case-insensitive (I)
          2) dict           -> full options (regex/flags/normalize/validators/...)
        """
        # Shorthand: 'PATTERN_NAME: "pattern"'
        if isinstance(spec, str):
            pat = re.compile(spec, re.I)
            meta: Dict[str, Any] = {
                "type": key,
                "validators": [],
                "normalize": [],
                "confidence": 0.99,  # regex matches are deterministic
                "priority": 0,
            }
            return key, pat, meta

        # Full form requires a mapping with a 'regex' field.
        if not isinstance(spec, dict) or "regex" not in spec:
            return None

        # Translate flag letters to Python's re flags.
        flags = 0
        for f in spec.get("flags", ["I"]):
            if f == "I":
                flags |= re.I
            elif f == "M":
                flags |= re.M
            elif f == "S":
                flags |= re.S

        # Compile the pattern once; reuse for all inputs.
        pat = re.compile(spec["regex"], flags)

        # Metadata carried alongside the compiled regex.
        meta = {
            "type": spec.get("type", key),
            "validators": spec.get("validators", []),
            "normalize": spec.get("normalize", []),
            "confidence": float(spec.get("confidence", 0.99)),
            "priority": int(spec.get("priority", 0)),
        }
        return key, pat, meta

    # -- Execution helpers ------------------------------------------------------------------

    def _apply_normalizers(self, text: str, names: List[str]) -> str:
        """
        Apply 0..N normalizers in order. Unknown names are ignored (for forward-compat).
        """
        for n in names:
            func = _NORMALIZERS.get(n)
            if func:
                text = func(text)
        return text

    def _validators_ok(self, text: str, names: List[str]) -> bool:
        """
        Return True only if all requested validators pass. Unknown names are treated as
        absent (i.e., skipped), which keeps rules forward-compatible.
        """
        for name in names:
            fn = _VALIDATORS.get(name)
            if fn and not fn(text):
                return False
        return True

    # -- Public API -------------------------------------------------------------------------

    def detect(self, text: str) -> List[Span]:
        """
        Run all compiled rules against the input text and yield `Span`s.

        Order of operations per match:
          1) regex match -> raw substring (m.group(0))
          2) normalize   -> e.g., strip spaces/dashes
          3) validate    -> e.g., Luhn / IBAN checks; drop if any fail
          4) emit Span   -> with original raw substring and configured type/confidence
        """
        spans: List[Span] = []

        for _, pat, meta in self.rules:
            for m in pat.finditer(text):
                raw = m.group(0)

                # Normalize before validation so checks see canonical forms.
                norm = self._apply_normalizers(raw, meta["normalize"])

                # Validators gate the match; if any fail, skip this candidate.
                if not self._validators_ok(norm, meta["validators"]):
                    continue

                spans.append(
                    Span(
                        start=m.start(),
                        end=m.end(),
                        text=raw,                    # keep the raw slice for display/scrub
                        type=meta["type"],           # canonical type name
                        confidence=meta["confidence"]
                    )
                )

        return spans
