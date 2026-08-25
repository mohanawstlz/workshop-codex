---
name: fastapi-crud-resource
description: >-
  Add or extend a validated FastAPI CRUD resource in an existing Python
  repository. Use when asked to scaffold REST endpoints, add a resource API,
  implement CRUD operations, or verify a FastAPI resource contract with
  offline tests and documentation.
---

# FastAPI CRUD Resource

Add a resource without replacing the repository's architecture or conventions.

## Workflow

1. Read `AGENTS.md`, dependency files, the application factory, existing routes,
   models, tests, and README.
2. Inspect the worktree and preserve unrelated changes.
3. Read [references/api-contract.md](references/api-contract.md) before choosing
   endpoint semantics.
4. Define create, partial-update, replacement, and response models as needed.
   Validate blank text, collection bounds, numeric ranges, enum values, empty
   updates, and explicit null values.
5. Reuse existing persistence patterns. For in-memory storage, keep state
   app-local, injectable, and safe for FastAPI worker threads.
6. Implement create, list, retrieve, update, replacement, and delete operations
   that fit the repository. Register API routes before any SPA catch-all and
   update CORS methods when required.
7. Translate missing resources into consistent 404 responses. Catch and
   sanitize failures from external APIs or persistence at the route boundary.
8. Read [references/test-matrix.md](references/test-matrix.md), then add focused
   offline tests. Do not require network or cloud credentials.
9. Update the README with endpoints, payload shape, and persistence limits.
10. Run the repository-prescribed test command after each behavior change.
11. Run the route verifier and final repository checks:

```bash
python .codex/skills/fastapi-crud-resource/scripts/verify_routes.py \
  --app package.api:app \
  --prefix /api/resources
```

Use `--without-patch` or `--without-put` only when that operation is
intentionally outside the requested contract.

Do not add a framework or persistence dependency unless the repository already
uses it or the user explicitly requests it.

## Example Prompt

> Use `$fastapi-crud-resource` to add a validated Order CRUD API with offline tests.
