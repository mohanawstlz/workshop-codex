# CRUD Test Matrix

Cover the behavior relevant to the requested resource:

- Create response, generated identifier, defaults, timestamps, and `Location`.
- Empty and populated list responses.
- Retrieval of an existing resource.
- `PATCH` preservation of omitted fields.
- Rejection of empty updates, explicit nulls, invalid enums, blank strings,
  empty collections, invalid quantities, and malformed identifiers.
- `PUT` replacement semantics and rejection of incomplete bodies.
- `DELETE` returning `204` with no body.
- Consistent `404` responses from retrieve, update, replace, and delete.
- Isolation between application instances when storage is in memory.
- Sanitized external-service or persistence failures when applicable.

Keep all tests offline and use the repository's existing FastAPI test client
and fixtures.
