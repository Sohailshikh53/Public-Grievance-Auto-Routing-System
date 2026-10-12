# PG-ARS — Public Grievance Auto-Routing System

PG-ARS is a civic operations platform that classifies public grievances, routes them to municipal departments, monitors statutory SLAs, and simulates city-scale demand scenarios.

## Highlights

- Citizen grievance intake with live classification and confidence fallback
- Three role-specific workspaces: Citizen, City Operations Officer, and Maharashtra State Head
- City-scoped operations across ten Maharashtra municipal cities
- ML-assisted top-issue extraction and operational priority ranking
- English, Hindi, Marathi, and Roman-Indic civic vocabulary normalization
- Browser voice input and optional GPS coordinates
- Duplicate-grievance detection before submission
- Manual triage with correction feedback for future model training
- Department workflow, audit timeline, reassignment, and citizen reopening
- Automatic background SLA evaluation and two-level escalation
- Leakage-resistant model evaluation with grouped source-template holdout
- Deterministic city digital-twin simulator with six incident presets
- Ward pressure, department utilization, throughput, and escalation visualizations

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Configuration

Environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PGARS_CONFIDENCE_THRESHOLD` | `0.65` | Minimum model confidence for direct routing |
| `PGARS_CLASS_MARGIN_THRESHOLD` | `0.15` | Required lead over the second department |
| `PGARS_ALLOWED_ORIGINS` | Local port 8000 origins | Comma-separated CORS allowlist |
| `PGARS_SLA_SCAN_SECONDS` | `300` | Background SLA scan interval |
| `PGARS_TRACKING_YEAR` | Current UTC year | Optional tracking-token year override |

## Tests

```bash
python -m pytest -q
```

Regenerate the model and its evaluation report with:

```bash
python -m backend.data.prepare_dataset
```

The evaluation uses a department-balanced group holdout: every generated paraphrase of a source complaint stays in the same split. The reported score is therefore intentionally more conservative than the previous random-row split.

## Architecture

```text
Citizen Portal ─┬─> NLP + rule grounding ─┬─> Department queue
                │                         └─> Human triage
                └─> Duplicate search

Department workflow ─> Audit history ─> SLA watchdog ─> Escalation
        │
        └─> Resolution ─> Citizen verification / reopen

Scenario Lab ─> Deterministic event simulation ─> Capacity and SLA metrics
```

Use the **Active workspace** selector in the header to switch between the citizen portal, an assigned-city command dashboard, and the Maharashtra state command center. The role selector is a local demonstration interface; a production deployment should connect these roles to an identity provider and enforce the same city/state scope in authenticated API claims.

SQLite keeps the demonstration self-contained. A production deployment should use PostgreSQL/PostGIS, object storage for evidence, an identity provider for officer RBAC, and a worker queue for notifications and large jobs.
