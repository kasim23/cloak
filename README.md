## cloak — privacy-first PII scrubber (CLI)

**cloak** finds and removes sensitive data (PII, PHI, secrets, tokens) in text files, datasets, and documents.  
It masks or pseudonymizes them while keeping referential integrity, so the same name or ID always maps to the same placeholder.

> **Status:** early MVP — works locally, tests pass, and growing fast. Expect rough edges.

---

## 🚀 Quick start (dev)

```bash
# install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# setup dev env
cd cloak
uv venv -p 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# run CLI
cloak --help
cloak scan tests/fixtures/sample.txt --report out/report.html

# test & lint
pytest -q
ruff check . && ruff format --check .
mypy src
````

---

## 📦 Install (when released)

```bash
pipx install cloak-privacy
# or
uvx cloak-privacy
# or via Homebrew
brew install cloaksh/tap/cloak
```

---

## 🛠 Commands

* `cloak scan <path>` → detect sensitive items + write HTML report
* `cloak scrub <src> --out <dst>` → create a sanitized copy
* `cloak review <review.jsonl>` → review low-confidence detections in a TUI
* `cloak hook install` → pre-commit hook (safety net)
* `cloak eval <fixtures/>` → evaluate precision/recall

---

## 📂 Repo layout

```
src/cloak/          # package
  cli.py            # Typer CLI entrypoint
  detect/           # detectors (regex, spaCy, more to come)
  engine/           # pipeline + scrub logic
  reporting/        # HTML report generator
  tui/              # TUI for review
tests/              # pytest suite
policies/           # example policies
.github/workflows/  # CI
packaging/homebrew/ # Homebrew formula
```

---

## 📋 License

MIT

---

## 🔮 Future Plans / TODO

* **Better actions**: stable pseudonymization, hashing, drop vs. redact policies
* **Thresholds**: per-detector confidence levels (regex, spaCy, transformers)
* **More detectors**: expand regex packs for secrets, IDs, tokens, and international PII
* **Optional AI backends**: Hugging Face transformers (NER) via Docker
* **Performance**: skip binaries, parallel scanning, batch processing
* **Docs**: full MkDocs site with examples, config, and contributions guide
* **Packaging**: PyPI release (`pipx install cloak-privacy`) + Homebrew tap
* **CI/CD**: GitHub Actions for testing and publishing
* **Telemetry (opt-in)**: anonymous usage stats (files scanned, entities detected)
* **Review UX**: polish the TUI for comfortable human-in-the-loop workflows


