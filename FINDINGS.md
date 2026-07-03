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

  **Update**: there is a follow up commit to fix a regression duplicate data for unit tests causing by the fix above.

## Missing indexes on owner_id/created_at

- **Problem**: `list_documents_with_status` filters `Document` rows by `owner_id`
  and sorts by `created_at` on every call (`GET /documents` and the gRPC
  `ListDocuments` RPC), but neither column was indexed — every call does a full
  table scan of `documents` plus an in-memory sort.
- **Severity**: Medium — no data exposure, but this is the query hit on every
  page load, and its cost grows linearly with total document count across *all*
  users (not just the caller's), since there's no index to prune the scan.
- **Trigger**: Call `GET /documents` once `documents` has enough rows that a full
  scan + sort becomes measurable (thousands+ rows).
- **Fix**: Added a composite index `(owner_id, created_at)` via
  `__table_args__ = (Index("ix_documents_owner_id_created_at", "owner_id", "created_at"),)`
  on `Document`.
- **Why**: The issue as originally scoped suggested two independent
  single-column indexes (`index=True` on each column). A composite index on
  `(owner_id, created_at)` is strictly better for this specific access pattern —
  it lets the query planner satisfy both the `WHERE owner_id = ?` filter and the
  `ORDER BY created_at DESC` in a single index traversal, with no separate sort
  step. Two standalone indexes would force the planner to use one and still sort
  the matching rows in memory. `get_document`'s `owner_id` filter doesn't need
  its own index — it narrows a row already located by primary key (`id`), so an
  index there wouldn't speed anything up.
- **Migration/scale notes**: This repo has no migration tool — `init_db()` calls
  `Base.metadata.create_all`, which only creates tables/indexes that don't exist
  yet. Editing the model is enough for fresh databases (including the test suite,
  which builds an in-memory SQLite DB from scratch on every run) but does
  **nothing** for an already-deployed database; the index there must be created
  out-of-band with `CREATE INDEX ix_documents_owner_id_created_at ON documents
  (owner_id, created_at);`.
  - **SQLite (current backend)**: `CREATE INDEX` takes a write lock on the whole
    database file for the build's duration — there's no online/concurrent index
    build. On a massive table this is measurable write downtime; run it in a
    maintenance window, sized from a dry run against a staging copy of the table.
    If growth is expected to reach that point, it's also a signal to move off
    SQLite (single-writer, file-based) rather than rely on maintenance windows
    indefinitely.
  - **Postgres (likely eventual target at scale)**: use `CREATE INDEX
    CONCURRENTLY`, which avoids locking out reads/writes at the cost of a longer
    build; it must run outside a transaction block and can fail partway,
    leaving an invalid index that needs `DROP INDEX` + retry — so this needs a
    real migration tool (e.g. Alembic), not a bare SQL statement, before this
    fix is safe to roll out against a large production table.
  - Ongoing cost is a small per-write B-tree update on every `documents`
    insert/update — negligible until write throughput itself is "massive," but
    worth noting as a tradeoff rather than a free win.

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

## Order-dependent test in test_document_service.py

- **Problem**: `test_list_documents_only_returns_carols_own_document` never created its
  own test data — it queried for `carol@example.com` assuming
  `test_create_document_for_carol` (declared earlier in the same file) had already
  inserted her into the shared, session-scoped `db_session` fixture.
- **Severity**: Low — no production impact, but it's a latent CI flake: the test fails
  if run in isolation (`pytest -k test_list_documents_only_returns_carols_own_document`),
  under a test-randomization plugin, or if a new test is ever inserted between the two.
- **Trigger**: Run the test alone, or reorder/insert tests ahead of it in the file.
- **Fix**: The test now creates its own user and document instead of depending on the
  previous test's side effect. Used a distinct email (`carol2@example.com`) rather than
  reusing `carol@example.com`, since `db_session` is still shared session-wide and
  `User.email` is unique — reusing the literal would collide with the row
  `test_create_document_for_carol` inserts whenever both tests run in the same session.
- **Why**: Mirrors the self-contained pattern already used by the other tests in the same
  file (`test_list_documents_uses_most_recent_conversion`, `test_get_document_denies_non_owner`),
  and fixes the coupling without touching the shared `db_session`/`client` fixtures in
  `conftest.py`, which `test_conversion_service.py` also depends on — rescoping those
  fixtures would have been a larger, riskier change for a test-only, low-severity bug.
- **Scale**: For better scaffolding, we can have fixture per function instead of per session, since the complexity will grow over the time when unit tests also grow. But for this assessment, since i do not want to rewrite the neighbourhood and keep the fix clean and surgical, so i picked this solution.
