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

## N+1 queries in document listing

- **Problem**: `list_documents_with_status` fetches all of a user's documents in one
  query, then accesses `document.conversions` inside the loop to find each document's
  latest conversion — each access is a separate lazy-loaded query, so listing N
  documents issues `1 + N` queries.
- **Severity**: Medium — no data exposure, but query count scales linearly with a
  user's document count on every `GET /documents` call and the equivalent gRPC
  `ListDocuments` RPC, and compounds with request concurrency.
- **Trigger**: Call `GET /documents` (or the gRPC `ListDocuments` RPC) for a user with
  multiple documents; observe one SELECT per document in addition to the initial list
  query.
- **Fix**: Added `.options(selectinload(Document.conversions))` to the query in
  `list_documents_with_status`, batching all conversions for the returned documents
  into a single extra query (`1 + N` → `2` total, regardless of document count).
  Removed the now-stale inline comment describing the N+1. Added a regression test
  (`test_list_documents_uses_most_recent_conversion`) that gives one document two
  `Conversion` rows with different `created_at` values and asserts the endpoint
  returns the most recent one's status/audio_url.
- **Why**: `selectinload` preserves the existing relationship ordering
  (`Conversion.created_at.desc()` on `Document.conversions`), so `conversions[0]`
  still means "latest attempt" with no change to the picking logic itself — only how
  the rows are fetched. That keeps the fix mechanical and low-risk versus rewriting
  the loop around a hand-rolled correlated subquery, which would have to reimplement
  the same tie-break logic and had no existing test coverage to catch a mistake in it
  (the two pre-existing tests only ever exercised documents with zero conversions).

## Unhandled TTS failure leaves conversion stuck at "processing"

- **Problem**: `create_conversion` commits a `Conversion` row as `"processing"`, then
  calls `_run_tts_engine`, which raises `RuntimeError` ~20% of the time to simulate an
  engine timeout/error. Nothing caught that exception, so it propagated up through
  `POST /documents/{id}/convert` as an unhandled 500, and the row was left at
  `"processing"` forever with no way for the client to know the job failed.
- **Severity**: Medium — no data exposure, but every failed conversion is a stuck row
  a client can't distinguish from "still working," and the endpoint returns an opaque
  500 instead of a usable response.
- **Trigger**: Call `POST /documents/{id}/convert` when `_run_tts_engine`'s random
  failure branch fires (`random.random() < 0.2`).
- **Fix**: Wrapped the `_run_tts_engine` call in `try/except RuntimeError`; on failure,
  sets `conversion.status = "failed"`, commits, and returns the conversion instead of
  letting the exception propagate. Added a regression test
  (`test_create_conversion_marks_failed_on_tts_error`) that forces the failure branch
  via `monkeypatch` on `random.random`, mirroring the existing success-path test.
- **Why**: Caught `RuntimeError` specifically rather than a bare `Exception` —
  `_run_tts_engine`'s body has no other code path that can raise, so a broader catch
  would suppress errors this code can't actually produce today. Returning the `"failed"`
  conversion (rather than re-raising) matches the existing caller contract: the HTTP
  route in `http_app.py` already builds `ConversionResponse` straight from whatever
  `create_conversion` returns and treats `status` as a free-form field, so `"failed"`
  slots in as a normal response rather than requiring a new error-handling path.
