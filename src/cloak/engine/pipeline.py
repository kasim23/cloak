from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Iterable
import json

from ..config import CloakConfig
from ..detect.regex_backend import RegexBackend


@dataclass
class Span:
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
    def __init__(self, cfg: CloakConfig, mode: str = "pseudonymize") -> None:
        self.cfg = cfg
        self.mode = mode
        self.regex = RegexBackend()

    def scan_text(self, text: str) -> List[Span]:
        spans = self.regex.detect(text)
        # TODO: chain NER/LLM backends
        return spans

    def _iter_files(self, src: Path) -> Iterable[Path]:
        if src.is_file():
            yield src
        else:
            for p in src.rglob("*"):
                if p.is_file():
                    yield p

    def scan_path(self, src: Path) -> ScanResult:
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

    def _apply_actions(self, text: str, spans: List[Span]) -> str:
        # Minimal implementation: mask emails by replacing user part with ***.
        # (Proper pseudonymization/mapping will come later.)
        if not spans:
            return text
        # Replace from the end to keep indices valid
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
