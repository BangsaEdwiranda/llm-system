# llm (practice rig)

. It is a small
"documents → audio" app with the same shape as the real assessment (Python gRPC + SQLAlchemy
backend, React/TypeScript frontend, moonrepo + pnpm) and a handful of seeded issues spanning
security, performance, reliability, and testing.

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
