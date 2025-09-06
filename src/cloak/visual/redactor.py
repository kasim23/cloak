"""
Visual redaction engine that creates documents with black boxes over sensitive content.

This module provides visual redaction capabilities for different document formats:
- PDF: Direct coordinate-based redaction with black rectangles
- Images: Pixel-based black box overlay 
- Text-to-visual: Render text with redacted areas as black boxes

The visual redactor maintains the original document layout while replacing
sensitive content with black boxes, similar to official government redactions.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Union
import tempfile
import logging

# PDF processing
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Image processing  
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Text-to-image rendering
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from ..engine.pipeline import Span

logger = logging.getLogger(__name__)


@dataclass
class VisualSpan:
    """A span with visual coordinates for redaction."""
    start: int
    end: int  
    text: str
    type: str
    confidence: float
    # Visual coordinates (page-relative)
    page: int
    x0: float
    y0: float 
    x1: float
    y1: float


@dataclass 
class RedactionResult:
    """Result of visual redaction operation."""
    success: bool
    output_path: str
    error_message: str = ""
    redacted_count: int = 0
    file_size_bytes: int = 0


def create_redacted_preview(
    original_spans: List[Span],
    text: str,
    max_width: int = 80
) -> str:
    """
    Create a text preview showing what will be redacted with █ blocks.
    
    This is useful for the web UI preview functionality before final processing.
    """
    # Sort spans by position
    sorted_spans = sorted(original_spans, key=lambda s: s.start)
    
    result = []
    last_end = 0
    
    for span in sorted_spans:
        # Add text before this span
        result.append(text[last_end:span.start])
        
        # Add redaction block (█ characters matching length)
        redaction_length = span.end - span.start
        result.append('█' * redaction_length)
        
        last_end = span.end
    
    # Add remaining text
    result.append(text[last_end:])
    
    preview_text = ''.join(result)
    
    # Add line breaks for readability
    if len(preview_text) > max_width:
        lines = []
        for i in range(0, len(preview_text), max_width):
            lines.append(preview_text[i:i + max_width])
        return '\n'.join(lines)
    
    return preview_text


class VisualRedactor:
    """
    Visual redaction engine for creating documents with black boxes.
    
    Supports multiple formats and provides a unified interface for
    visual redaction across different document types.
    """
    
    def __init__(self):
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check for required dependencies and log warnings."""
        if not HAS_PYMUPDF:
            logger.warning("PyMuPDF not available - PDF redaction disabled")
        if not HAS_PIL:
            logger.warning("Pillow not available - image redaction disabled") 
        if not HAS_MATPLOTLIB:
            logger.warning("Matplotlib not available - text-to-image disabled")
    
    def redact_document(
        self,
        input_path: Union[str, Path, io.BytesIO],
        spans: List[Span],
        output_path: Union[str, Path],
        file_type: str = None
    ) -> RedactionResult:
        """
        Redact a document with visual black boxes.
        
        Args:
            input_path: Path to input document or BytesIO buffer
            spans: List of text spans to redact
            output_path: Path for redacted output
            file_type: File type hint ('pdf', 'png', 'txt', etc.)
            
        Returns:
            RedactionResult with success status and metadata
        """
        try:
            # Determine file type
            if file_type is None:
                if isinstance(input_path, (str, Path)):
                    file_type = Path(input_path).suffix.lower().lstrip('.')
                else:
                    raise ValueError("file_type required for BytesIO input")
            
            # Route to appropriate redaction method
            if file_type == 'txt':
                return self._redact_text_to_image(input_path, spans, output_path)
            else:
                return RedactionResult(
                    success=False,
                    output_path="",
                    error_message=f"Unsupported file type: {file_type}. Currently only 'txt' is supported."
                )
                
        except Exception as e:
            logger.exception(f"Redaction failed: {e}")
            return RedactionResult(
                success=False,
                output_path="",
                error_message=str(e)
            )
    
    def _redact_text_to_image(
        self,
        input_path: Union[str, Path, io.BytesIO],
        spans: List[Span],
        output_path: Union[str, Path]
    ) -> RedactionResult:
        """Convert text file to image with visual redaction."""
        if not HAS_MATPLOTLIB:
            return RedactionResult(
                success=False,
                output_path="",
                error_message="Matplotlib not available for text-to-image"
            )
        
        # Read text content
        if isinstance(input_path, io.BytesIO):
            text = input_path.getvalue().decode('utf-8')
        else:
            text = Path(input_path).read_text()
        
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(8.5, 11))  # Letter size
        ax.axis('off')
        
        # Split text into lines
        lines = text.split('\n')
        line_height = 0.03
        char_width = 0.008
        
        # Render text line by line with redactions
        for line_idx, line in enumerate(lines):
            y_pos = 0.95 - (line_idx * line_height)
            
            # Check if this line contains any spans to redact
            line_start = sum(len(l) + 1 for l in lines[:line_idx])  # +1 for newline
            
            current_x = 0.05
            char_pos = line_start
            
            for char in line:
                # Check if current character is in a redacted span
                in_redacted_span = any(
                    span.start <= char_pos < span.end for span in spans
                )
                
                if in_redacted_span:
                    # Draw black rectangle instead of character
                    rect = patches.Rectangle(
                        (current_x, y_pos - 0.01),
                        char_width, line_height * 0.8,
                        linewidth=0, facecolor='black'
                    )
                    ax.add_patch(rect)
                else:
                    # Draw normal character
                    ax.text(current_x, y_pos, char, fontsize=10, fontfamily='monospace')
                
                current_x += char_width
                char_pos += 1
        
        # Save as image
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        file_size = Path(output_path).stat().st_size
        
        return RedactionResult(
            success=True,
            output_path=str(output_path),
            redacted_count=len(spans),
            file_size_bytes=file_size
        )