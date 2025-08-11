from __future__ import annotations

from pathlib import Path
from jinja2 import Environment, PackageLoader, select_autoescape
from ..engine.pipeline import ScanResult

def write_report(result: ScanResult, path: Path) -> None:
    env = Environment(
        loader=PackageLoader("cloak.reporting", "templates"),
        autoescape=select_autoescape()
    )
    tmpl = env.get_template("report.html.j2")
    html = tmpl.render(result=result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
