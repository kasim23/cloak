import pytest

def _spacy_ready() -> bool:
    """Return True iff spaCy + en_core_web_sm can be loaded."""
    try:
        import spacy  # type: ignore
        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not _spacy_ready(), reason="spaCy or en_core_web_sm not installed")


def test_spacy_backend_core_entities():
    """
    Unit-level: SpacyBackend should detect PERSON/ORG/LOC on typical text.
    """
    from cloak.detect.spacy_backend import SpacyBackend

    text = (
        "On January 5, 2024, Alice Johnson from Acme Corp flew to Seattle "
        "to meet with Bob and the product team."
    )
    b = SpacyBackend(model="en_core_web_sm")
    spans = b.detect(text)
    labels = {s.type for s in spans}
    values = {s.text for s in spans}

    assert "PERSON" in labels, "Expected a PERSON (Alice Johnson or Bob)"
    assert "ORG" in labels, "Expected an ORG (Acme Corp)"
    assert "LOC" in labels, "Expected a location (GPE mapped to LOC, e.g., Seattle)"
    # small model lacks scores; we synthesize 0.99 — check range only
    assert all(0.0 <= s.confidence <= 1.0 for s in spans)
    assert any(name in values for name in ("Alice Johnson", "Bob"))


def test_pipeline_regex_plus_spacy_merge_behavior(tmp_path):
    """
    Integration: regex detects EMAIL + CREDIT_CARD; spaCy detects PERSON/ORG/LOC.
    Merge policy should keep structured types (e.g., CREDIT_CARD) even if overlaps occur.
    """
    from cloak.config import CloakConfig
    from cloak.engine.pipeline import Pipeline

    # Config with regex + spaCy enabled (HF off)
    cfg = CloakConfig.model_validate({
        "detectors": {
            "regex": True,
            "regex_packs": {"pii": True, "secrets": True, "network": True},
            "spacy": {"enabled": True, "model": "en_core_web_sm"},
            "spacy_ruler": {"enabled": True, "address_patterns": True, "id_patterns": True},
            "hf": {"enabled": False},
        }
    })

    text = (
        "Alice (alice@example.com) met Bob from Acme Corp in Seattle on 2024-01-05. "
        "Her Visa is 4111-1111-1111-1111."
    )
    p = tmp_path / "doc.txt"
    p.write_text(text)

    pipe = Pipeline(cfg)
    result = pipe.scan_path(p)

    assert result.files == 1
    spans = result.findings[0].spans
    types = {s.type for s in spans}
    sample = [(s.type, s.text) for s in spans]

    # Regex hits
    assert "EMAIL" in types, f"EMAIL missing. spans={sample}"
    assert "CREDIT_CARD" in types, f"CREDIT_CARD missing. spans={sample}"

    # spaCy hits
    assert "PERSON" in types, f"PERSON missing. spans={sample}"
    assert "ORG" in types, f"ORG missing. spans={sample}"
    assert "LOC" in types, f"LOC missing. spans={sample}"

    # Merge policy: structured types must survive
    assert any(s.type == "CREDIT_CARD" and "4111" in s.text for s in spans)
    assert any(s.type == "EMAIL" and "@" in s.text for s in spans)


def test_spacy_does_not_label_email_as_person():
    """
    Sanity: ensure spaCy doesn't misclassify emails as PERSON/ORG/LOC in our adapter.
    EMAIL is handled by regex; spaCy should generally ignore the '@' token span for NER types.
    """
    from cloak.detect.spacy_backend import SpacyBackend

    b = SpacyBackend(model="en_core_web_sm")
    spans = b.detect("Contact alice@example.com for details.")
    assert not any(s.type in {"PERSON", "ORG", "LOC"} and "@" in s.text for s in spans)