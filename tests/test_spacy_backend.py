# tests/test_spacy_backend.py
import importlib
import pytest

try:
    import spacy  # type: ignore
    SPACY_AVAILABLE = True
except Exception:
    SPACY_AVAILABLE = False


def _model_available(name: str = "en_core_web_sm") -> bool:
    if not SPACY_AVAILABLE:
        return False
    try:
        spacy.load(name)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _model_available(), reason="spaCy or en_core_web_sm not installed")
def test_spacy_backend_core_entities():
    """
    Validates that SpacyBackend can extract common NER labels we care about:
    PERSON, ORG, LOC/GPE, DATE. We use fuzzy checks (>=1 found) because
    small model behavior can vary slightly across versions.
    """
    from cloak.detect.spacy_backend import SpacyBackend

    text = (
        "On January 5, 2024, Alice Johnson from Acme Corp flew to Seattle to meet "
        "with Bob and the product team. They discussed plans for Q2."
    )

    b = SpacyBackend(model="en_core_web_sm")
    spans = b.detect(text)

    # Collect sets for easy membership assertions
    types = {s.type for s in spans}
    values = {s.text for s in spans}

    # Core expectations (fuzzy):
    assert "PERSON" in types, "Expected a PERSON entity (e.g., Alice Johnson or Bob)"
    assert "ORG" in types, "Expected an ORG entity (e.g., Acme Corp)"
    assert "LOC" in types, "Expected a location (LOC/GPE mapped to LOC, e.g., Seattle)"
    assert "DATE" in types or any("2024" in v for v in values), "Expected a date-like entity"

    # Sanity: confidences should be present (we set 0.99 in the backend)
    assert all(0.0 <= s.confidence <= 1.0 for s in spans)

    # Spot-check that PERSON captures at least one of our names
    person_texts = {s.text for s in spans if s.type == "PERSON"}
    assert any(name in person_texts for name in ("Alice Johnson", "Bob")), "Expected a named person"


@pytest.mark.skipif(not _model_available(), reason="spaCy or en_core_web_sm not installed")
def test_spacy_backend_no_false_email_capture():
    """
    Ensure spaCy doesn't wrongly classify a pure email as PERSON/ORG.
    EMAIL is handled by regex; spaCy should generally leave it alone.
    """
    from cloak.detect.spacy_backend import SpacyBackend

    text = "Contact us at alice@example.com for details."
    b = SpacyBackend(model="en_core_web_sm")
    spans = b.detect(text)

    # It’s okay if spaCy returns OTHER or nothing, but it shouldn't call the email PERSON/ORG/LOC.
    bad_labels = {"PERSON", "ORG", "LOC"}
    assert not any(s.type in bad_labels and "@" in s.text for s in spans)

