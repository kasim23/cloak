## Web flow — upload → redact → download

```mermaid
flowchart LR
  U[User (Browser)] -->|Upload PDFs/Docs| FE[Web UI (Next.js)]
  FE -->|POST /jobs| API[FastAPI /cloak serve]
  API -->|enqueue| RQ[Redis Queue]
  RQ --> WRK[Worker (Pipeline + PDF redactor)]
  WRK -->|detect & redact| PIPE[cloak Pipeline]
  PIPE -->|burn-in redactions| PDF[PyMuPDF / OCR fallback]
  WRK -->|store temp| STORE[(Temp Storage / S3)]
  API -->|GET /status| FE
  FE -->|poll/progress| API
  API -->|signed URL / stream| FE
  FE -->|Download redacted ZIP| U
