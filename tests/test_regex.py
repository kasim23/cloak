from cloak.detect.regex_backend import RegexBackend

def test_email_detect():
    rb = RegexBackend()
    spans = rb.detect("Contact me at alice@example.com please.")
    assert any(s.type == "EMAIL" for s in spans)
