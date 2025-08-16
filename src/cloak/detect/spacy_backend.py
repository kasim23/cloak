"""
spaCy NER backend (ML-based) for unstructured entities like PERSON/ORG/LOC.

What this does
--------------
- Loads a spaCy pipeline (default: en_core_web_sm).
- Runs the `ner` component and maps spaCy labels to Cloak's canonical types.
- Emits Span(start, end, text, type, confidence).

Why this exists
---------------
Regex is great for *structured* identifiers (EMAIL, CREDIT_CARD, IBAN...),
but names/organizations/places need an ML model. This backend adds that layer.

Notes on confidence
-------------------
The small English model (`en_core_web_sm`) does not expose per-entity scores.
We return a fixed 0.99 confidence for each entity so downstream code can treat
it uniformly with other detectors. If you switch to a transformer spaCy model
(e.g., `en_core_web_trf`), you can adapt this to use real scores later.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Span:
    """Unified detection record consumed by the pipeline."""
    start: int
    end: int
    text: str
    type: str
    confidence: float


class SpacyBackend:
    """
    Lightweight wrapper around spaCy NER.

    Parameters
    ----------
    model : str
        spaCy model name to load (e.g., 'en_core_web_sm').
    min_confidence : float
        Threshold to keep entities (kept for symmetry; small model uses fixed 0.99).
    """

    def __init__(self, model: str = "en_core_web_sm", min_confidence: float = 0.0) -> None:
        try:
            import spacy  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "spaCy not installed. Install extras or run: uv pip install spacy"
            ) from e

        # Load the model; disable components we don't need for speed.
        # Keep 'ner' active; others can be off for detection-only runs.
        self.nlp = spacy.load(
            model,
            disable=["tagger", "parser", "lemmatizer", "attribute_ruler", "morphologizer"],
        )
        self.min_conf = float(min_confidence)

        # Map spaCy labels to Cloak's canonical schema.
        # GPE (countries/cities) → LOC
        self.label_map: Dict[str, str] = {
            "PERSON": "PERSON",
            "ORG": "ORG",
            "GPE": "LOC",
            "LOC": "LOC",
            "DATE": "DATE",
            # Everything else -> OTHER (we currently filter these out)
        }

    def detect(self, text: str) -> List[Span]:
        """Run NER on text and return mapped spans."""
        doc = self.nlp(text)
        out: List[Span] = []
        for ent in doc.ents:
            mapped = self.label_map.get(ent.label_)
            if not mapped:
                # Skip labels we don't care about (DATE handled by regex; etc.)
                continue
            # Small model doesn't expose scores reliably; use a fixed high value.
            conf = 0.99
            if conf < self.min_conf:
                continue
            out.append(
                Span(
                    start=ent.start_char,
                    end=ent.end_char,
                    text=text[ent.start_char : ent.end_char],
                    type=mapped,
                    confidence=conf,
                )
            )
        return out
