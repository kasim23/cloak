# tests/test_pipeline_with_spacy.py
import pytest

# Skip the whole module if spaCy/model not available
def _spacy_ready() -> bool:
    try:
        import spacy  # type: ignore
        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not _spacy_ready(), reason="spaCy or en_core_web_sm not installed")


def test_pipeline_regex_plus_spacy(tmp_path):
    """
    Integration: regex should pick EMAIL; spaCy should pick PERSON/ORG/LOC.
    The merge logic should keep structured regex types if any overlaps occur.
    """
    from cloak.config import CloakConfig
    from cloak.engine.pipeline import Pipeline

    # Minimal config with spaCy enabled
    cfg = CloakConfig.model_validate({
        "detectors": {
            "regex": True,
            "spacy": {"enabled": True, "model": "en_core_web_sm"},
            "hf": {"enabled": False}
        }
    })

    text = (
        "Alice (alice@example.com) met Bob from Acme Corp in Seattle on January 5, 2024. "
        "Reach her at alice@example.com."
    )
    # Write to a temp file to exercise scan_path() vs scan_text()
    p = tmp_path / "sample.txt"
    p.write_text(text)

    pipe = Pipeline(cfg)
    result = pipe.scan_path(p)

    assert result.files == 1
    assert len(result.findings) == 1
    spans = result.findings[0].spans
    labels = {s.type for s in spans}
    texts = {s.text for s in spans}

    # Regex hits
    assert "EMAIL" in labels
    assert any("@" in t for t in texts), "Expected an email from regex detector"

    # spaCy hits
    assert "PERSON" in labels, "Expected a PERSON (Alice or Bob)"
    assert "ORG" in labels, "Expected an ORG (Acme Corp)"
    assert "LOC" in labels, "Expected a LOC (Seattle)"

    # Merge policy check: if an entity overlaps with parts of the email, the structured EMAIL should win
    # (We don't assert exact boundaries, just that EMAIL still present after merge)
    assert any(s.type == "EMAIL" for s in spans), "EMAIL should remain after merging"

