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
