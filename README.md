## Cloak — Privacy-First Document Redaction Platform

**Cloak** is a comprehensive document redaction platform that finds and removes sensitive data (PII, PHI, secrets, tokens) from documents while maintaining visual fidelity. Available as both a CLI tool for developers and a web application for non-technical users.

**Key Features:**
- 🎯 **Smart Detection**: Regex patterns, spaCy NER, and entity rulers for comprehensive PII/PHI detection
- 🖤 **Visual Redaction**: Creates documents with black boxes over sensitive content (like official redacted documents)  
- 🗣️ **Natural Language**: Customize redaction with prompts like "don't redact my name, only SSN and phone"
- 🔒 **Privacy-First**: No document storage on servers, immediate deletion after processing
- 🌐 **Multi-Interface**: CLI for developers, web app for everyone
- 📊 **Usage Tracking**: Tiered pricing with free, paid, and enterprise plans

> **Status:** Core CLI complete, Web API functional, Frontend in progress. Ready for beta testing.

---

## 🚀 Quick Start

### CLI Usage
```bash
# Install dependencies
uv venv -p 3.12 && source .venv/bin/activate
uv pip install -e ".[dev,spacy,web]"

# Basic CLI commands
cloak --help
cloak scan tests/fixtures/sample.txt --report out/report.html
cloak scrub tests/fixtures/sample.txt --out out/sanitized/ --mode pseudonymize

# Natural language CLI (new!)
cloak scrub document.txt --out redacted.png --prompt "don't redact names, only SSN and phone"
```

### Web API Usage
```bash
# Start the web server
python -m cloak.web.api
# or
uvicorn cloak.web.api:app --reload

# API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Development
```bash
# Run all tests
pytest -q

# Test specific components
pytest tests/test_visual_redactor.py -v
pytest tests/test_redaction_parser.py -v  
pytest tests/test_web_api.py -v

# Code quality
ruff check . && ruff format --check .
mypy src
```

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

## 🛠 CLI Commands

### Core Commands
* `cloak scan <path>` → detect sensitive items + generate HTML report
* `cloak scrub <src> --out <dst>` → create sanitized copy with visual redaction
* `cloak review <review.jsonl>` → review low-confidence detections in TUI
* `cloak hook install` → add pre-commit hook for repository safety

### Natural Language Interface
* `cloak scrub document.txt --prompt "only redact SSN and credit cards"`
* `cloak scrub data.csv --prompt "don't redact names, hide everything else"`
* `cloak scrub report.pdf --prompt "keep dates but redact all personal info"`

### Web API Endpoints
* `POST /redact` → upload document for redaction
* `GET /profile` → user profile and usage limits  
* `GET /jobs/{id}` → check processing status
* `GET /jobs/{id}/download` → download redacted document
* `GET /suggestions` → get example redaction prompts

---

## 📂 Project Structure

```
src/cloak/
├── cli.py                   # Typer CLI interface
├── config.py               # Pydantic configuration models  
├── detect/                 # Detection engines
│   ├── regex_backend.py    # Pattern-based PII/secrets detection
│   ├── spacy_backend.py    # NLP entity recognition  
│   └── spacy_ruler.py      # Rule-based structured data detection
├── engine/                 # Core processing pipeline
│   ├── pipeline.py         # Orchestrates detectors and span merging
│   ├── actions.py          # Policy-driven text transformations
│   └── pseudonymizer.py    # Consistent pseudonymization
├── nl/                     # Natural language processing
│   ├── parser.py           # CLI command parsing
│   └── redaction_parser.py # Custom redaction prompt parsing  
├── visual/                 # Visual redaction
│   └── redactor.py         # Black box document redaction
├── web/                    # Web application
│   ├── api.py              # FastAPI REST endpoints
│   └── database.py         # SQLAlchemy models and schema
├── reporting/              # Report generation
└── tui/                    # Terminal user interface

tests/                      # Comprehensive test suite
├── test_*_backend.py       # Unit tests for detectors
├── test_pipeline*.py       # Integration tests  
├── test_redaction_parser.py # NL parser tests
├── test_visual_redactor.py # Visual redaction tests
└── test_web_api.py         # API endpoint tests

docs/                       # Documentation
policies/                   # Example redaction policies
packaging/                  # Distribution configs
```

---

## 📋 License

MIT

---

## 🏗️ Architecture Overview

Cloak follows a **modular pipeline architecture** that separates detection, configuration, and action execution:

### Core Components
1. **Detection Layer**: Multiple pluggable detectors (regex, spaCy, entity rulers) run in parallel
2. **Pipeline Orchestrator**: Merges overlapping spans using priority rules (structured > unstructured)  
3. **Natural Language Parser**: Converts user prompts to policy configurations
4. **Action Engine**: Applies configurable transformations (mask, drop, pseudonymize, hash)
5. **Visual Redactor**: Creates documents with black boxes over sensitive content
6. **Web API**: REST endpoints for document processing and user management

### Data Flow
```
Input Document → Multiple Detectors → Span Merging → Policy Application → Visual Redaction → Output
                                                   ↗
                            Natural Language Prompt Processing
```

## 🚀 Current Status & Roadmap

### ✅ **Completed (MVP Ready)**
- **Core CLI**: Full detection and redaction pipeline
- **Visual Redaction**: Black box overlays instead of [REDACTED] text
- **Natural Language**: Parse prompts like "don't redact names, only SSN"
- **Web API**: REST endpoints with authentication and file processing
- **Database Schema**: User management, usage tracking, job status
- **Test Coverage**: Comprehensive test suite across all components

### 🚧 **In Progress**
- **Frontend UI**: React/Next.js web interface with drag-and-drop
- **Document Formats**: PDF, Word, image processing beyond text

### 📋 **Next Up**
- **Authentication**: OAuth integration (Gmail/GitHub signin)
- **Usage Tracking**: Tier-based limits and billing integration
- **Security Pipeline**: Automatic file deletion and privacy compliance
- **Deployment**: Cloud hosting with security measures
- **Enhanced Detectors**: International PII, more secret patterns
- **Performance**: Parallel processing, batch operations

### 🎯 **Future Vision**
- **LLM Integration**: GPT/Claude API for complex prompt understanding (with cost controls)
- **Enterprise Features**: Team management, audit logs, compliance reporting
- **Mobile Apps**: iOS/Android document redaction
- **Integrations**: Slack, Google Drive, Dropbox plugins
- **Advanced AI**: Custom model training for domain-specific PII


