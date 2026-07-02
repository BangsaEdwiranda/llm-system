# Findings

## IDOR on document access

- **Problem**: `document_service.get_document()` fetched a document by ID with no
  ownership check, used by `GET /documents/{id}`, `POST /documents/{id}/convert`,
  `GET /documents/{id}/audio`, and the gRPC `GetDocument` RPC.
- **Severity**: High — any authenticated user could read, convert, or download the
  audio of any other user's document by guessing/enumerating sequential document IDs.
- **Trigger**: Authenticate as any user, call one of the four endpoints with a
  `document_id` belonging to another user.
- **Fix**: Added an `owner_id` parameter to `get_document()` and scoped the query
  with `Document.owner_id == owner_id`; threaded the caller's `user.id` through all
  4 call sites (3 HTTP routes + gRPC `GetDocument`). Added a regression test
  asserting a non-owner gets `None`.
- **Why**: Matches the existing pattern already used by `list_documents_with_status`,
  which filters by `owner_id`. Scoping at the query level (vs. fetch-then-check) keeps
  the fix in one place and prevents any future call site from forgetting the check.

## JWT secret env var mismatch

- **Problem**: `.env.example` documented the signing-secret variable as `JWT_SECRET`,
  but `config.py` reads `JWT_SECRET_KEY`. The two names never matched.
- **Severity**: Medium — anyone following `.env.example` to configure a deployment
  sets a variable the app never reads, so it silently keeps the hardcoded
  `"change-me-in-prod"` fallback instead of the operator's real secret, with no error
  raised anywhere.
- **Trigger**: Copy `.env.example` to `.env`, set `JWT_SECRET` to a real random value,
  deploy. `config.py` still reads `os.environ.get("JWT_SECRET_KEY", ...)`, gets nothing,
  and falls back to the hardcoded default — tokens end up signed with a well-known
  string.
- **Fix**: Renamed the key in `.env.example` from `JWT_SECRET` to `JWT_SECRET_KEY` so
  it matches what `config.py` actually reads.
- **Why**: `config.py` is the single source of truth other code depends on (`jwt_secret_key`
  is referenced elsewhere in the auth flow); `.env.example` is just a template with no
  other consumers (confirmed via repo-wide search — only these two files mention the
  variable), so fixing the template is the lower-risk, one-line change versus renaming
  the code's env var.
