import pytest
from cloak.detect.regex_backend import RegexBackend

@pytest.fixture
def backend():
    return RegexBackend(use_pii=True, use_secrets=True, use_network=True)

def test_detects_api_key(backend):
    # Must be AKIA + 16 uppercase alnum chars:
    text = "API_KEY=AKIA1234567890ABCDEF"
    spans = backend.detect(text)
    assert any(s.type == "AWS_ACCESS_KEY_ID" for s in spans)

def test_detects_secret(backend):
    # 40 base64-like chars (example shape for AWS secret)
    secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # length 40
    text = f"aws_secret={secret}"
    spans = backend.detect(text)
    assert any(s.type == "SECRET" for s in spans)

def test_detects_url(backend):
    text = "Visit https://example.com/page"
    spans = backend.detect(text)
    assert any(s.type == "URL" for s in spans)

def test_detects_ipv6(backend):
    text = "IPv6 address: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    spans = backend.detect(text)
    assert any(s.type == "IPV6" for s in spans)

def test_detects_mac(backend):
    text = "MAC address: 00:1A:2B:3C:4D:5E"
    spans = backend.detect(text)
    assert any(s.type == "MAC" for s in spans)
