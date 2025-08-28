from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional

Action = Literal["scan", "scrub"]

class NLCommand(BaseModel):
    """
    Normalized command we can execute deterministically.
    """
    action: Action
    src: str = Field(default=".", description="Source file or directory")
    out: Optional[str] = Field(default=None, description="Output path (report path for scan; destination dir/file for scrub)")
    html_report: bool = Field(default=False, description="Generate HTML report (scan)")
    config: Optional[str] = Field(default=None, description="Optional config path (.cloak.yaml)")
    recursive: bool = Field(default=True, description="Directory recursion (always true for now)")
    # Future: include/exclude globs, file types, dry-run etc.
