import pytest
from cloak.detect.regex_backend import RegexBackend

@pytest.fixture
def backend():
    # load all packs
    return RegexBackend(use_pii=True, use_secrets=True, use_network=True)

def test_detects_email(backend):
    text = "Contact us at alice@example.com"
    spans = backend.detect(text)
    assert any(s.type == "EMAIL" for s in spans)

def test_detects_phone(backend):
    text = "Call me at +1 202-555-0147"
    spans = backend.detect(text)
    assert any(s.type == "PHONE" for s in spans)

def test_detects_credit_card(backend):
    text = "My Visa is 4111-1111-1111-1111"
    spans = backend.detect(text)
    assert any(s.type == "CREDIT_CARD" for s in spans)

def test_detects_ssn(backend):
    text = "SSN: 123-45-6789"
    spans = backend.detect(text)
    assert any(s.type == "SSN" for s in spans)

def test_detects_ip(backend):
    text = "Server IP 192.168.0.1"
    spans = backend.detect(text)
    assert any(s.type == "IP" for s in spans)

def test_detects_iban(backend):
    text = "IBAN DE89 3704 0044 0532 0130 00"
    spans = backend.detect(text)
    assert any(s.type == "IBAN" for s in spans)
