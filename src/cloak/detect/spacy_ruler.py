"""
spaCy EntityRuler backend for deterministic NER patterns.

What this does
--------------
- Adds rule-based patterns to a spaCy pipeline via `EntityRuler`.
- Targets domain-ish phrases ML may miss or mislabel (ADDRESS-like tokens, MRN hints,
  'SSN' words, very loose US passport shapes).
- Emits Span(start, end, text, type, confidence).

Why this exists
---------------
Bridges the gap between pure regex (great for structure) and pure ML (great for
names/places) with lightweight, explainable patterns that improve recall.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass
class Span:
    """Unified detection record consumed by the pipeline."""
    start: int
    end: int
    text: str
    type: str
    confidence: float


class SpacyRulerBackend:
    """
    Wrapper for spaCy's EntityRuler.

    Parameters
    ----------
    model : str
        spaCy model name to load (e.g., 'en_core_web_sm').
    address_patterns : bool
        Include light patterns that hint at addresses (street/avenue/road).
    id_patterns : bool
        Include ID-ish cues (MRN, SSN words, loose 9-digit passport).
    """

    def __init__(
        self,
        model: str = "en_core_web_sm",
        address_patterns: bool = True,
        id_patterns: bool = True,
    ) -> None:
        try:
            import spacy
            from spacy.pipeline import EntityRuler
        except Exception as e:
            raise RuntimeError(
                "spaCy not installed. Install extras or run: uv pip install spacy"
            ) from e

        self.nlp = spacy.load(model)
        ruler = self.nlp.add_pipe("entity_ruler", config={"overwrite_ents": False})

        patterns = []

        if address_patterns:
            # Conservative address-ish cues. These are *hints*, not full address parsers.
            # We keep them intentionally minimal to reduce false positives.
            patterns += [
                # e.g., "Main Street", "Market Street", "Broadway"
                {"label": "ADDRESS", "pattern": [{"IS_TITLE": True}, {"LOWER": {"IN": ["street", "st.", "st", "avenue", "ave.", "ave", "road", "rd.", "rd"]}}]},
                # e.g., "10 Main"
                {"label": "ADDRESS", "pattern": [{"IS_DIGIT": True}, {"IS_TITLE": True}]},
            ]

        if id_patterns:
            patterns += [
                # US passport often 9 digits (supplemental; main detection via regex pack)
                {"label": "PASSPORT", "pattern": [{"SHAPE": "ddddddddd"}]},
                # MRN cue words (very heuristic, improves recall in clinical texts)
                {"label": "MRN", "pattern": [{"LOWER": {"IN": ["mrn", "medical", "record"]}}]},
                # 'SSN' cue words (not the number)
                {"label": "SSN_WORD", "pattern": [{"LOWER": {"IN": ["ssn", "social", "security", "number"]}}]},
            ]

        ruler.add_patterns(patterns)

    def detect(self, text: str) -> List[Span]:
        """Run the EntityRuler and emit spans for our custom labels."""
        doc = self.nlp(text)
        out: List[Span] = []
        for ent in doc.ents:
            if ent.label_ in {"ADDRESS", "PASSPORT", "MRN", "SSN_WORD"}:
                out.append(
                    Span(
                        start=ent.start_char,
                        end=ent.end_char,
                        text=text[ent.start_char : ent.end_char],
                        type=ent.label_,
                        confidence=0.8,  # rule-based; lower than regex, higher than guessy ML
                    )
                )
        return out