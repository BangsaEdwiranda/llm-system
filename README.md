# llm-refactor-speechify (practice rig)

A self-built practice simulation of the Speechify "Refactoring LLM Assessment" described in
[docs/assessment.md](docs/assessment.md) and [docs/email.md](docs/email.md). It is a small
"documents → audio" app with the same shape as the real assessment (Python gRPC + SQLAlchemy
backend, React/TypeScript frontend, moonrepo + pnpm) and a handful of seeded issues spanning
security, performance, reliability, and testing.

See [docs/plan.md](docs/plan.md) for the design and [docs/answer-key.md](docs/answer-key.md)
for the seeded issues — avoid reading the answer key until after your own practice pass.

## Layout

- `apps/api` — Python 3.12 backend (FastAPI HTTP + gRPC, SQLAlchemy, SQLite)
- `apps/web` — React + TypeScript frontend (Vite)

## Quickstart

```bash
# backend
cd apps/api
python -m venv .venv
.venv/Scripts/activate   # or `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"
python -m speechify_api.seed
uvicorn speechify_api.http_app:app --reload

# frontend (separate shell)
pnpm install
pnpm --filter web dev
```
