# Bedrock Chat API Reference

## Scope

This reference documents the public interfaces in the current Bedrock Chat
source tree:

- Python package exports and public module functions;
- FastAPI application factories, schemas, and HTTP endpoints;
- Order models, in-memory storage, and router factory;
- the terminal entry point; and
- exported React and browser-storage helpers.

Underscore-prefixed helpers, Pydantic validator hooks, React event handlers,
and route-local Python functions are implementation details. Their observable
validation and side effects are documented under the corresponding public
model, endpoint, or component.

Current versions:

| Surface | Version |
|---|---|
| Python package | `0.1.0` |
| FastAPI application | `1.0.0` |
| Frontend package | `1.0.0` |
| Python | 3.11 or later |
| Node.js | 20.19 or later, or 22.12 or later |

## Navigation

- [Root Python exports](#root-python-exports)
- [Configuration](#configuration)
- [Bedrock client](#bedrock-client)
- [FastAPI application](#fastapi-application)
- [HTTP endpoints](#http-endpoints)
- [Order APIs](#order-apis)
- [Terminal entry point](#terminal-entry-point)
- [Browser exports](#browser-exports)
- [Limitations](#limitations)

## Root Python exports

`bedrock_chat.__init__` defines the supported root import surface:

```python
from bedrock_chat import BedrockChatClient, Settings, extract_text
```

The package also exposes:

```python
bedrock_chat.__version__ == "0.1.0"
```

`build_message`, application factories, schemas, and Order APIs remain public
at their module paths but are not re-exported from the package root.

## Configuration

### Constants

**Import**

```python
from bedrock_chat.config import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_REGION,
    DEFAULT_TEMPERATURE,
)
```

| Name | Type | Value |
|---|---|---|
| `DEFAULT_MODEL_ID` | `str` | `"openai.gpt-5.5"` |
| `DEFAULT_REGION` | `str` | `"us-east-2"` |
| `DEFAULT_MAX_TOKENS` | `int` | `1024` |
| `DEFAULT_TEMPERATURE` | `float \| None` | `None` |

### `Settings`

**Import**

```python
from bedrock_chat import Settings
```

**Signature**

```python
Settings(
    model_id: str = "openai.gpt-5.5",
    region: str = "us-east-2",
    max_tokens: int = 1024,
    temperature: float | None = None,
)
```

**Fields**

| Field | Type | Default | Purpose |
|---|---|---|---|
| `model_id` | `str` | `"openai.gpt-5.5"` | Model sent in the Responses API payload |
| `region` | `str` | `"us-east-2"` | Region used in the Bedrock endpoint and SigV4 signing |
| `max_tokens` | `int` | `1024` | Value sent as `max_output_tokens` |
| `temperature` | `float \| None` | `None` | Optional sampling temperature |

`Settings` is a mutable standard-library dataclass. Direct construction does
not validate field ranges or model compatibility.

### `Settings.from_env`

**Signature**

```python
@classmethod
Settings.from_env(
    env: Mapping[str, str] | None = None,
) -> Settings
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `env` | `Mapping[str, str] \| None` | `None` | Source mapping; `None` reads `os.environ` |

**Environment variables**

| Variable | Conversion | Default or fallback |
|---|---|---|
| `BEDROCK_MODEL_ID` | `str` | `"openai.gpt-5.5"` |
| `BEDROCK_REGION` | `str` | Falls back to `AWS_REGION`, then `AWS_DEFAULT_REGION`, then `"us-east-2"` |
| `BEDROCK_MAX_TOKENS` | `int(...)` | `1024` |
| `BEDROCK_TEMPERATURE` | `float(...)` | `None` when absent |

**Returns**

A new `Settings` instance.

**Raises**

- `ValueError` when `BEDROCK_MAX_TOKENS` is not an integer.
- `ValueError` when `BEDROCK_TEMPERATURE` is present but not a float.

**Example**

```python
settings = Settings.from_env(
    {
        "BEDROCK_MODEL_ID": "openai.gpt-5.4",
        "AWS_REGION": "us-west-2",
        "BEDROCK_MAX_TOKENS": "512",
    }
)
```

`temperature` is omitted from model requests when it remains `None`. This is
required by the configured GPT-5.x reasoning models, which reject that
parameter.

## Bedrock client

### `Transport`

**Import**

```python
from bedrock_chat.client import Transport
```

**Type**

```python
Callable[
    [str, dict[str, str], bytes],
    dict[str, Any],
]
```

A transport receives the request URL, HTTP headers, and encoded JSON body. It
returns an already parsed Responses API JSON object. Injecting a transport
allows the client to be used and tested without AWS access.

### `build_message`

**Import**

```python
from bedrock_chat.client import build_message
```

**Signature**

```python
build_message(role: str, text: str) -> dict[str, Any]
```

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `role` | `str` | Yes | Exactly `"user"` or `"assistant"` |
| `text` | `str` | Yes | Message content; no length or blank-value validation is applied |

**Returns**

```python
{"role": role, "content": text}
```

**Raises**

`ValueError` when `role` is not `"user"` or `"assistant"`.

**Side effects**

None.

**Example**

```python
message = build_message("user", "Explain SigV4.")
```

### `extract_text`

**Imports**

```python
from bedrock_chat import extract_text
# or
from bedrock_chat.client import extract_text
```

**Signature**

```python
extract_text(response: dict[str, Any]) -> str
```

**Parameters**

`response` is a parsed Responses API payload. The function examines `output`
items with `type == "message"` and their `content` blocks with
`type == "output_text"`.

**Returns**

All matching `text` values concatenated in payload order. Returns `""` when no
matching output text exists.

**Raises**

No application-specific exception is declared. Structurally malformed values
may raise normal Python mapping or iteration errors.

**Side effects**

None.

**Example**

```python
text = extract_text(
    {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Hello "},
                    {"type": "output_text", "text": "world"},
                ],
            }
        ]
    }
)
assert text == "Hello world"
```

Reasoning items and non-`output_text` blocks are ignored.

### `BedrockChatClient`

**Imports**

```python
from bedrock_chat import BedrockChatClient
# or
from bedrock_chat.client import BedrockChatClient
```

**Constructor**

```python
BedrockChatClient(
    settings: Settings | None = None,
    transport: Transport | None = None,
)
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `settings` | `Settings \| None` | `None` | Uses `Settings.from_env()` when omitted |
| `transport` | `Transport \| None` | `None` | Uses the built-in SigV4 HTTP transport when omitted |

**Public attributes**

| Attribute | Type | Initial value |
|---|---|---|
| `settings` | `Settings` | Supplied or environment-derived settings |
| `url` | `str` | `https://bedrock-mantle.<region>.api.aws/openai/v1/responses` |
| `history` | `list[dict[str, Any]]` | `[]` |

**Raises**

When the default transport is selected, construction raises `RuntimeError` if
the AWS SDK credential chain returns no credentials. Environment conversion
errors from `Settings.from_env()` also propagate.

**Side effects**

The default transport creates a `boto3.Session` and resolves credentials.
Construction does not call the model endpoint.

The built-in transport signs requests for the SigV4 service name `"bedrock"`
and uses a 60-second HTTP timeout.

#### `BedrockChatClient.send`

**Signature**

```python
send(text: str) -> str
```

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `text` | `str` | Yes | New user message; no blank or length validation is applied here |

**Request**

The transport receives a JSON body containing:

```json
{
  "model": "<settings.model_id>",
  "input": "<completed history plus the new user message>",
  "max_output_tokens": 1024
}
```

`temperature` is included only when `settings.temperature` is not `None`.

**Returns**

The assistant output produced by `extract_text`.

**Raises**

- `ValueError` when the response contains no output text.
- Transport, JSON, HTTP, credential, and interruption errors without wrapping.

**Side effects**

After a valid non-empty reply, appends the user message and assistant reply to
`history`. If transport or response processing fails, `history` remains
unchanged.

**Example**

```python
client = BedrockChatClient(Settings(region="us-east-2"))
reply = client.send("What is Amazon Bedrock?")
```

Each instance has independent in-memory history. The full completed history is
resent on later calls.

## FastAPI application

### Schemas

**Imports**

```python
from bedrock_chat.api import (
    AppConfigResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
```

#### `ChatMessage`

| Field | Type | Constraints |
|---|---|---|
| `role` | `Literal["user", "assistant"]` | Required |
| `content` | `str` | Required; 1 to 50,000 characters |

`ChatMessage` alone accepts whitespace-only content. `ChatRequest` rejects it.

#### `ChatRequest`

| Field | Type | Constraints |
|---|---|---|
| `messages` | `list[ChatMessage]` | Required; 1 to 100 messages |

Conversation rules:

1. The first message must have role `"user"`.
2. Roles must alternate between `"user"` and `"assistant"`.
3. The final message must have role `"user"`.
4. Every message must contain non-whitespace content.

Pydantic raises `ValidationError` when construction violates these rules.
FastAPI converts request validation failures to HTTP `422`.

#### `ChatResponse`

| Field | Type | Description |
|---|---|---|
| `message` | `ChatMessage` | Assistant message returned by the model |
| `model` | `str` | Effective model ID |
| `region` | `str` | Effective AWS Region |

#### `AppConfigResponse`

| Field | Type | Description |
|---|---|---|
| `model` | `str` | Effective model ID |
| `region` | `str` | Effective AWS Region |

### `ClientFactory`

**Type**

```python
Callable[[Settings], BedrockChatClient]
```

Factories used with `create_app` must accept one `Settings` argument and return
an object compatible with `BedrockChatClient`, including a writable `history`
attribute and `send(text)` method.

### `create_app`

**Import**

```python
from bedrock_chat.api import create_app
```

**Signature**

```python
create_app(
    settings: Settings | None = None,
    client_factory: ClientFactory = BedrockChatClient,
    static_dir: pathlib.Path | None = None,
) -> fastapi.FastAPI
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `settings` | `Settings \| None` | `None` | Fixed settings for this app instance |
| `client_factory` | `ClientFactory` | `BedrockChatClient` | Creates a fresh chat client per `/api/chat` request |
| `static_dir` | `Path \| None` | `None` | React build directory; defaults to `frontend/dist` |

**Returns**

A configured `FastAPI` application with chat, configuration, health, Order,
CORS, and optional static frontend routes.

CORS permits `http://localhost:5173` and `http://127.0.0.1:5173`, the methods
`DELETE`, `GET`, `PATCH`, `POST`, and `PUT`, and the `Content-Type` header.
Credentials are disabled.

**Side effects and lifecycle**

- Resolves environment settings immediately when `settings` is omitted.
- Creates a new in-memory `OrderStore` for the application.
- Serves the React catch-all route only when `<static_dir>/index.html` exists
  while the application is created.
- Does not create a Bedrock client until `/api/chat` is called.

**Example**

```python
from fastapi.testclient import TestClient

from bedrock_chat.api import create_app
from bedrock_chat.config import Settings

app = create_app(settings=Settings(model_id="openai.test-model"))
client = TestClient(app)
assert client.get("/api/health").json() == {"status": "ok"}
```

### `app`

**Import**

```python
from bedrock_chat.api import app
```

The module-level ASGI application is created by calling `create_app()` during
module import. Run it with:

```bash
uvicorn bedrock_chat.api:app
```

### `DEFAULT_STATIC_DIR`

**Import**

```python
from bedrock_chat.api import DEFAULT_STATIC_DIR
```

A `pathlib.Path` resolving to the repository's `frontend/dist` directory. It
is the default frontend directory used by `create_app`.

## HTTP endpoints

All application endpoints use JSON except the static frontend and the empty
Order delete response. There is no application authentication or server-side
chat session store.

FastAPI also exposes:

- `GET /docs` for Swagger UI;
- `GET /redoc` for ReDoc; and
- `GET /openapi.json` for the OpenAPI schema.

### `GET /api/health`

Returns readiness without creating a Bedrock client or contacting AWS.

**Success: `200 OK`**

```json
{"status": "ok"}
```

### `GET /api/config`

Returns non-secret runtime configuration.

**Success: `200 OK`**

```json
{
  "model": "openai.gpt-5.5",
  "region": "us-east-2"
}
```

### `POST /api/chat`

Sends a complete conversation ending in a new user message.

**Request body**

`ChatRequest`

```json
{
  "messages": [
    {"role": "user", "content": "What is SigV4?"},
    {"role": "assistant", "content": "It is an AWS request signing protocol."},
    {"role": "user", "content": "Why is it needed here?"}
  ]
}
```

**Success: `200 OK`**

`ChatResponse`

```json
{
  "message": {
    "role": "assistant",
    "content": "It authenticates the request to Amazon Bedrock."
  },
  "model": "openai.gpt-5.5",
  "region": "us-east-2"
}
```

**Errors**

| Status | Condition | Response |
|---|---|---|
| `422` | Invalid schema, blank content, role order, or message count | Standard FastAPI validation body |
| `502` | Client construction, Bedrock request, or response extraction fails | `{"detail": "The model request failed. Check AWS credentials and model access."}` |

The backend creates a fresh client for each call, loads all messages except the
last into its temporary `history`, and passes the final user content to
`send`. The browser must resend prior context on every call.

### Static frontend route

When the selected static directory contains `index.html`, non-API paths are
served that file for React client-side routing. An existing `assets`
subdirectory is mounted at `/assets`.

## Order APIs

Order storage is an independent sample API included in the same application.
It is in memory and is cleared when the application is recreated or restarted.

### Order schemas

**Imports**

```python
from bedrock_chat.orders import (
    Order,
    OrderCreate,
    OrderItem,
    OrderReplace,
    OrderStatus,
    OrderUpdate,
)
```

#### `OrderStatus`

A string enum with these exact values:

```text
pending
processing
shipped
delivered
cancelled
```

#### `OrderItem`

| Field | Type | Constraints |
|---|---|---|
| `sku` | `str` | Required; trimmed; 1 to 100 characters; not blank |
| `quantity` | `int` | Required; 1 to 10,000 |

#### `OrderCreate`

| Field | Type | Constraints |
|---|---|---|
| `customer_id` | `str` | Required; trimmed; 1 to 100 characters; not blank |
| `items` | `list[OrderItem]` | Required; 1 to 100 items |
| `shipping_address` | `str` | Required; trimmed; 1 to 500 characters; not blank |

#### `OrderUpdate`

| Field | Type | Default | Constraints |
|---|---|---|---|
| `customer_id` | `str \| None` | `None` | 1 to 100 characters when supplied |
| `items` | `list[OrderItem] \| None` | `None` | 1 to 100 items when supplied |
| `shipping_address` | `str \| None` | `None` | 1 to 500 characters when supplied |
| `status` | `OrderStatus \| None` | `None` | One supported status |

At least one field must be supplied. Explicit `null` values are rejected.

#### `OrderReplace`

Includes all required `OrderCreate` fields plus:

| Field | Type | Constraints |
|---|---|---|
| `status` | `OrderStatus` | Required |

#### `Order`

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Generated order identifier |
| `customer_id` | `str` | Customer identifier |
| `items` | `list[OrderItem]` | Ordered products |
| `shipping_address` | `str` | Shipping destination |
| `status` | `OrderStatus` | Current lifecycle status |
| `created_at` | `datetime` | UTC creation timestamp |
| `updated_at` | `datetime` | UTC last-update timestamp |

### `OrderStore`

**Import**

```python
from bedrock_chat.orders import OrderStore
```

**Constructor**

```python
OrderStore()
```

Creates an empty, thread-safe, in-memory store.

All returned `Order` values are deep copies. Mutating a returned model does not
mutate the stored value.

#### `OrderStore.create`

```python
create(payload: OrderCreate) -> Order
```

Creates an Order with a generated UUID, `pending` status, and equal UTC
`created_at` and `updated_at` timestamps.

#### `OrderStore.list`

```python
list() -> list[Order]
```

Returns all Orders sorted by creation timestamp, then UUID.

#### `OrderStore.get`

```python
get(order_id: UUID) -> Order | None
```

Returns the matching Order or `None`.

#### `OrderStore.update`

```python
update(order_id: UUID, payload: OrderUpdate) -> Order | None
```

Updates only supplied fields, refreshes `updated_at`, and preserves
`created_at`. Returns `None` when the identifier is missing.

#### `OrderStore.replace`

```python
replace(order_id: UUID, payload: OrderReplace) -> Order | None
```

Replaces every mutable field, refreshes `updated_at`, and preserves `id` and
`created_at`. Returns `None` when the identifier is missing.

#### `OrderStore.delete`

```python
delete(order_id: UUID) -> bool
```

Returns `True` when an Order was deleted and `False` when it did not exist.

### `create_order_router`

**Import**

```python
from bedrock_chat.orders import create_order_router
```

**Signature**

```python
create_order_router(
    store: OrderStore | None = None,
) -> fastapi.APIRouter
```

Creates an Order CRUD router under `/api/orders`. When `store` is omitted, the
router owns a new `OrderStore`.

**Example**

```python
from fastapi import FastAPI

from bedrock_chat.orders import OrderStore, create_order_router

store = OrderStore()
app = FastAPI()
app.include_router(create_order_router(store))
```

### Order HTTP endpoints

| Method and path | Request | Success | Missing Order |
|---|---|---|---|
| `POST /api/orders` | `OrderCreate` | `201`, `Order`, and `Location` header | Not applicable |
| `GET /api/orders` | None | `200`, `list[Order]` | Not applicable |
| `GET /api/orders/{order_id}` | None | `200`, `Order` | `404` |
| `PATCH /api/orders/{order_id}` | `OrderUpdate` | `200`, updated `Order` | `404` |
| `PUT /api/orders/{order_id}` | `OrderReplace` | `200`, replaced `Order` | `404` |
| `DELETE /api/orders/{order_id}` | None | `204`, empty body | `404` |

Invalid UUIDs and request bodies return FastAPI `422` validation responses.
Missing Orders return:

```json
{"detail": "Order not found"}
```

**Create example**

```bash
curl -X POST http://127.0.0.1:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "customer-123",
    "items": [{"sku": "keyboard", "quantity": 1}],
    "shipping_address": "100 Main Street"
  }'
```

## Terminal entry point

### `main`

**Import**

```python
from bedrock_chat.__main__ import main
```

**Signature**

```python
main() -> int
```

**Behavior**

1. Resolves `Settings` from the environment.
2. Creates one `BedrockChatClient`.
3. Reads terminal input until `exit`, `quit`, EOF, or `KeyboardInterrupt`.
4. Ignores blank input.
5. Prints each assistant reply.
6. Reports model-call errors and continues reading.

**Returns**

| Value | Condition |
|---|---|
| `0` | Normal exit |
| `1` | Client construction failed |

Settings conversion errors occur before the setup `try` block and therefore
propagate instead of returning `1`.

**Command**

```bash
python -m bedrock_chat
```

History is held in the single client instance and is discarded when the
process exits.

## Browser exports

### Conversation data shape

The browser helpers use plain JavaScript objects:

```javascript
{
  id: "string",
  title: "string",
  messages: [
    { role: "user", content: "Hello" },
    { role: "assistant", content: "Hi" },
  ],
  createdAt: "ISO timestamp",
  updatedAt: "ISO timestamp",
}
```

These helpers perform only the validation explicitly described below. FastAPI
remains the validation boundary for messages submitted to `/api/chat`.

### `STORAGE_KEY`

**Import**

```javascript
import { STORAGE_KEY } from "./lib/conversations";
```

**Value**

```javascript
"bedrock-chat-conversations-v1"
```

### `createConversation`

**Signature**

```javascript
createConversation(overrides = {}) => Conversation
```

**Parameters**

`overrides` may provide `id`, `title`, `messages`, `createdAt`, or
`updatedAt`. Values are accepted without runtime validation.

**Returns**

A conversation with these defaults:

- `id`: `crypto.randomUUID()` when available, otherwise a timestamp/random
  fallback;
- `title`: `"New conversation"`;
- `messages`: `[]`;
- `createdAt`: the current ISO timestamp; and
- `updatedAt`: `createdAt`.

**Side effects**

Reads the current time and may read `globalThis.crypto`. It does not write to
storage.

**Example**

```javascript
const conversation = createConversation({ title: "Bedrock questions" });
```

### `deriveTitle`

**Signature**

```javascript
deriveTitle(content) => string
```

Collapses whitespace and trims the result. Normalized content of 42 characters
or fewer is returned unchanged. Longer content returns the first 41
characters, with trailing whitespace removed, followed by `"..."`.

The function expects a value with a string-compatible `.replace()` method.

### `loadConversations`

**Signature**

```javascript
loadConversations(storage = globalThis.localStorage) => Conversation[]
```

Parses `storage.getItem(STORAGE_KEY)`. Returns `[]` when:

- the stored value is missing or contains malformed JSON;
- the parsed value is not an array; or
- reading or parsing throws.

Within an array, entries are retained only when they have a string `id`, a
string `title`, and an array `messages`. Message contents and timestamps are
not validated by this helper.

**Side effects**

Reads one storage value. All read and parse errors are swallowed.

### `saveConversations`

**Signature**

```javascript
saveConversations(
  conversations,
  storage = globalThis.localStorage,
) => undefined
```

Serializes `conversations` with `JSON.stringify` and writes it under
`STORAGE_KEY`.

Storage access and serialization errors propagate to the caller.

**Example**

```javascript
const conversations = [createConversation()];
saveConversations(conversations);
```

### `App`

**Import**

```javascript
import App from "./App";
```

**Signature**

```javascript
App() => ReactElement
```

The root component accepts no props. It reads browser globals including
`localStorage`, `matchMedia`, `fetch`, `AbortController`, and clipboard APIs.
It calls:

- `GET /api/config` during initial rendering; and
- `POST /api/chat` when a message is submitted or retried.

Conversation state is persisted through the helpers above. Theme state uses
the separate key `"bedrock-chat-theme"`.

## Limitations

- No public interface in this project is marked deprecated or experimental.
- The Python package is version `0.1.0`; compatibility guarantees are not
  declared beyond the source and tests.
- The web chat is stateless on the server. Clients must resend complete
  history.
- Browser conversations are local to one browser profile and are not
  encrypted by the application.
- Terminal and `BedrockChatClient` history is process-local memory.
- Order data is process-local memory.
- Long chat histories increase request size and token usage and may exceed the
  model context window.
- The client does not trim, summarize, or persist conversation history.

For a guided explanation of chat state flow, see
[`chat-session-state-management.md`](./chat-session-state-management.md).
