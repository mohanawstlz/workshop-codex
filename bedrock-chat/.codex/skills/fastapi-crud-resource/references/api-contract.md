# FastAPI Resource Contract

Use these defaults unless repository conventions or the user's requirements
specify otherwise.

| Operation | Method | Success response |
|---|---|---|
| Create | `POST` | `201`, resource body, and `Location` header |
| List | `GET` | `200` and an array |
| Retrieve | `GET` | `200`, or `404` when missing |
| Partial update | `PATCH` | `200`; reject empty or null updates |
| Replace | `PUT` | `200`; require all mutable fields |
| Delete | `DELETE` | `204` with an empty body, or `404` |

Use FastAPI's `422` response for request validation failures. Avoid exposing
internal exception details.

For app-local in-memory storage, instantiate the store while creating the app.
Preserve identifiers and creation timestamps during updates, return defensive
copies, and protect shared mutations when synchronous routes may run in worker
threads.
