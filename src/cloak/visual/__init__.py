"""Visual redaction module for creating documents with black boxes over sensitive content."""

from .redactor import (
    VisualRedactor,
    VisualSpan,
    RedactionResult,
    create_redacted_preview,
)

__all__ = [
    "VisualRedactor",
    "VisualSpan", 
    "RedactionResult",
    "create_redacted_preview",
]