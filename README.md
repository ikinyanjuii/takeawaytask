# FeatureIQ — AI-first Feature Intelligence

FeatureIQ helps product teams turn unstructured feature requests into actionable product decisions. The MVP supports request submission, customer support voting, AI-assisted need/theme extraction, similar-request detection, human-approved consolidation, deterministic prioritisation, and decision briefs.

## Product workflow

1. Capture a feature request with its problem description and customer segment.
2. Analyse it to extract the underlying need, theme, impact, urgency, confidence and rationale.
3. Detect similar requests using OpenAI embeddings when configured, with a local TF-IDF fallback.
4. Review suggested duplicates. A product manager must approve or reject each merge; no automatic merge occurs.
5. Prioritise using a deterministic score combining demand, impact, urgency, strategic fit and effort.
6. Generate a decision brief with ranked evidence and recommendations.

## Stack

- **Frontend:** Next.js, React, TypeScript
- **API:** FastAPI, Pydantic, SQLAlchemy
- **Storage:** SQLite for local demo; PostgreSQL supported through `DATABASE_URL`
- **AI:** OpenAI chat completions and embeddings, with deterministic local fallback
- **Quality:** Pytest and GitHub Actions

## Run locally

Requirements: Python 3.11+, Node.js 20+, npm.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp ../.env.example .env  # optional; set OPENAI_API_KEY for live AI
python -m pytest -q
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

In another terminal:

```bash
cd frontend
npm install
cp ../.env.example .env.local
npm run dev
```

Open http://localhost:3000.

### Demo

Click **Load demo data**, analyse feature requests, review the suggested consolidations, and generate a decision brief.

## Docker

```bash
cp .env.example .env
# Add OPENAI_API_KEY for hosted AI analysis
docker compose up --build
```

Frontend: http://localhost:3000; API docs: http://localhost:8000/docs.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/requests` | Submit a request |
| GET | `/api/requests` | Search and list requests |
| GET | `/api/requests/{id}` | Request details |
| POST | `/api/requests/{id}/vote` | Support a request |
| POST | `/api/requests/{id}/analyse` | Extract needs/themes and find matches |
| GET | `/api/merge-suggestions` | List pending suggestions |
| POST | `/api/merge-suggestions/{id}/decision` | Approve/reject a suggestion |
| GET | `/api/insights` | Dashboard metrics and themes |
| POST | `/api/decision-briefs` | Generate a decision brief |

## Prioritisation model

`Score = 0.35 × Demand + 0.25 × Impact + 0.20 × Urgency + 0.15 × Strategic fit + 0.05 × Effort score`

Demand is capped at 20 votes; impact and urgency map Low/Medium/High to 25/60/100; strategic fit maps 1–5 to 20–100; effort is inverted so lower effort scores higher. Strategy fit and effort use neutral defaults in this MVP and should become explicit product-manager inputs before production use.

## Security and production limitations

**This is an assessment/demo MVP, not production-ready for real customer data.** It currently has no authentication, role-based access control or tenant isolation. The voter key is client-supplied and is not secure identity. Before public deployment, add authentication, authorization, server-verified voter identity, rate limiting, pagination, audit events, PII detection/redaction, data export/deletion, database migrations, encryption, monitoring, backups and a security review. Treat customer-submitted text as untrusted input to AI prompts.

SQLite is intended for local use. Use managed PostgreSQL in hosted environments. Configure HTTPS, managed secrets and an explicit production CORS allowlist.

## Environment variables

See [`.env.example`](.env.example): `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL`.

## Assessment notes

- `CLAUDE.md` contains the prompt-logging instruction.
- `prompts.txt` records the assessment brief and development instruction. Append future Claude Code instructions with timestamps.
- Suggested success metrics (hypotheses, not achieved results): reduce median triage time by 60%, achieve at least 80% precision on approved duplicate suggestions, and reduce time from submission to documented prioritisation decision by 40%. Establish baselines before claiming outcomes.
