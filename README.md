# cloak — privacy‑first PII scrubber (CLI)

**cloak** detects PII/PHI/secrets in datasets & documents and masks/pseudonymizes them while preserving referential integrity. Ships with reports and a review TUI. Optional RAG helpers.

> Status: scaffold / MVP. You can install locally and run `cloak --help`.

## Quick start (dev)

```bash
# using uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
cd cloak
uv venv -p 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# run
cloak --help
cloak scan tests/fixtures/sample.txt --report out/report.html

# tests & lint
pytest -q
ruff check . && ruff format --check .
mypy src
```

## Install (once released)
```bash
pipx install cloak-privacy
# or
uvx cloak-privacy
# or Homebrew
brew install cloaksh/tap/cloak
```

## Commands
- `cloak scan <path>`: dry-run detect + HTML report
- `cloak scrub <src> --out <dst>`: write sanitized mirror
- `cloak review <review.jsonl>`: TUI for low-confidence items
- `cloak hook install`: add pre-commit hook (safety net)
- `cloak eval <fixtures/>`: evaluation harness (precision/recall)

## Repo layout
```
src/cloak/          # package
  cli.py            # Typer CLI entrypoint
  __main__.py       # console_script target
  config.py         # Pydantic models & loading
  detect/           # detectors (regex/NER stubs)
  engine/           # pipeline & decisions
  reporting/        # HTML report
  tui/              # Textual review app (stub)
tests/              # pytest
policies/           # example policies
.github/workflows/  # CI
packaging/homebrew/ # brew formula template
```

## License
MIT
