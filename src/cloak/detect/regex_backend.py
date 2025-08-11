from __future__ import annotations

from dataclasses import dataclass
from typing import List
import re
import yaml
from importlib import resources

@dataclass
class Span:
    start: int
    end: int
    text: str
    type: str
    confidence: float

class RegexBackend:
    def __init__(self) -> None:
        # Load YAML rules from package data
        data = resources.files("cloak.detect.rulesets").joinpath("default.yaml").read_text()
        cfg = yaml.safe_load(data)
        self.patterns = [(etype, re.compile(pat, re.I)) for etype, pat in cfg.get("patterns", {}).items()]

    def detect(self, text: str) -> List[Span]:
        spans: List[Span] = []
        for etype, pat in self.patterns:
            for m in pat.finditer(text):
                spans.append(Span(start=m.start(), end=m.end(), text=m.group(0), type=etype, confidence=0.99))
        return spans
