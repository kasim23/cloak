import pytest

def _spacy_ready():
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not _spacy_ready(), reason="spaCy or model missing")

def test_spacy_entity_ruler_labels():
    from cloak.detect.spacy_ruler import SpacyRulerBackend
    b = SpacyRulerBackend(model="en_core_web_sm", address_patterns=True, id_patterns=True)
    text = "Patient MRN 12345 at 10 Main Street. SSN details discussed."
    spans = b.detect(text)
    labels = {s.type for s in spans}
    assert "MRN" in labels or "SSN_WORD" in labels or "ADDRESS" in labels
