# src/cloak/engine/pipeline.py
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from ..config import CloakConfig
from ..detect.regex_backend import RegexBackend
from ..detect.spacy_backend import SpacyBackend
from ..detect.spacy_ruler import SpacyRulerBackend


# Structured types that should win overlap conflicts
_STRUCTURED: set[str] = {
    "EMAIL", "PHONE", "IP", "IPV6", "MAC", "URL",
    "SSN", "CREDIT_CARD", "IBAN", "PASSPORT", "MRN",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "API_KEY", "SECRET",
}


@dataclass
class Span:
    """Unified span record used throughout the pipeline."""
    start: int
    end: int
    text: str
    type: str
    confidence: float


@dataclass
class FileFinding:
    path: str
    spans: List[Span]


@dataclass
class ScanResult:
    files: int
    entities: int
    findings: List[FileFinding]


class Pipeline:
    """
    Orchestrates multiple detectors (regex, spaCy, etc.), merges their spans,
    and applies policy actions for scrubbing.
    """

    def __init__(self, cfg: CloakConfig, mode: str = "pseudonymize") -> None:
        self.cfg = cfg
        self.mode = mode

        # --- Backends (toggle via .cloak.yaml) ---
        self.regex = (
            RegexBackend(
                use_pii=cfg.detectors.regex_packs.pii,
                use_secrets=cfg.detectors.regex_packs.secrets,
                use_network=cfg.detectors.regex_packs.network,
            )
            if cfg.detectors.regex
            else None
        )

        self.spacy = (
            SpacyBackend(
                model=cfg.detectors.spacy.model,
                min_confidence=cfg.detectors.spacy.min_confidence,
            )
            if cfg.detectors.spacy.enabled
            else None
        )

        self.spacy_ruler = (
            SpacyRulerBackend(
                model=cfg.detectors.spacy.model,
                address_patterns=cfg.detectors.spacy_ruler.address_patterns,
                id_patterns=cfg.detectors.spacy_ruler.id_patterns,
            )
            if cfg.detectors.spacy_ruler.enabled
            else None
        )

    # ---------------- Public API ----------------

    def scan_text(self, text: str) -> List[Span]:
        """Run all enabled detectors on a single string and merge the results."""
        spans: List[Span] = []
        if self.regex:
            spans.extend(self._adapt(self.regex.detect(text)))
        if self.spacy:
            spans.extend(self._adapt(self.spacy.detect(text)))
        if self.spacy_ruler:
            spans.extend(self._adapt(self.spacy_ruler.detect(text)))
        return self._merge(spans)

    def scan_path(self, src: Path) -> ScanResult:
        """Scan a file or an entire directory tree."""
        findings: List[FileFinding] = []
        files = 0
        entities = 0
        for p in self._iter_files(src):
            files += 1
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            spans = self.scan_text(text)
            entities += len(spans)
            if spans:
                findings.append(FileFinding(str(p), spans))
        return ScanResult(files=files, entities=entities, findings=findings)

    def scrub_path(self, src: Path, out: Path) -> None:
        """Produce a sanitized mirror of the source tree in `out/`."""
        out.mkdir(parents=True, exist_ok=True)
        for p in self._iter_files(src):
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            spans = self.scan_text(text)
            sanitized = self._apply_actions(text, spans)
            dest = out / p.relative_to(src) if not src.is_file() else out / p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(sanitized)

    # --------------- Internals ------------------

    def _iter_files(self, src: Path) -> Iterable[Path]:
        if src.is_file():
            yield src
            return
        for p in src.rglob("*"):
            if p.is_file():
                yield p

    @staticmethod
    def _adapt(spans: Sequence[Span]) -> List[Span]:
        """
        Ensure spans from all backends are the same dataclass shape.
        (Backends already return compatible Span objects; this is here for symmetry.)
        """
        return list(spans)

    def _merge(self, spans: List[Span]) -> List[Span]:
        """
        Merge spans from different detectors.

        Rules:
        - Keep everything by default.
        - On overlap:
            * If one is structured and the other isn't -> keep structured.
            * If both structured or both unstructured -> keep higher (confidence, length).
        """
        if not spans:
            return []

        spans = sorted(spans, key=lambda s: (s.start, -s.end))
        kept: List[Span] = []

        def overlaps(a: Span, b: Span) -> bool:
            return not (a.end <= b.start or b.end <= a.start)

        for s in spans:
            drop_s = False
            to_remove: List[Span] = []
            for k in kept:
                if not overlaps(s, k):
                    continue

                s_struct = s.type in _STRUCTURED
                k_struct = k.type in _STRUCTURED

                if s_struct != k_struct:
                    # Structured beats unstructured.
                    if s_struct:
                        to_remove.append(k)
                    else:
                        drop_s = True
                        break
                else:
                    # Same class: prefer higher confidence, then longer span.
                    s_key = (s.confidence, s.end - s.start)
                    k_key = (k.confidence, k.end - k.start)
                    if s_key > k_key:
                        to_remove.append(k)
                    else:
                        drop_s = True
                        break

            if not drop_s:
                if to_remove:
                    kept = [x for x in kept if x not in to_remove]
                kept.append(s)

            # continue scanning remaining kept items for other overlaps

        return kept

    def _apply_actions(self, text: str, spans: List[Span]) -> str:
        """
        Minimal scrubber: uses policy later; for now, mask emails and redact others.
        Replace from the end to keep indices valid.
        """
        if not spans:
            return text
        s = list(text)
        for sp in sorted(spans, key=lambda x: x.start, reverse=True):
            if sp.type == "EMAIL":
                replacement = self._mask_email(sp.text)
            else:
                replacement = "[REDACTED]"
            s[sp.start:sp.end] = list(replacement)
        return "".join(s)

    @staticmethod
    def _mask_email(email: str) -> str:
        try:
            user, domain = email.split("@", 1)
            if len(user) <= 1:
                return f"*@{domain}"
            return f"{user[0]}***@{domain}"
        except Exception:
            return "[REDACTED]"