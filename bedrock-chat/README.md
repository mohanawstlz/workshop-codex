# Bedrock Chat

A React and FastAPI chat application for OpenAI GPT models on **Amazon
Bedrock**. It uses Bedrock's OpenAI-compatible Responses API with AWS SigV4
authentication.

## Features

- Responsive React chat interface with Markdown responses, light and dark themes,
  and subtle message animations
- Multiple browser-local conversations with new, clear, delete, stop, retry, and copy actions
- Stateless FastAPI endpoint that validates and forwards conversation history
- In-memory Order CRUD API with validated request and response models
- Model and Region configuration through environment variables
- Production React build served directly by FastAPI
- Fully offline Python and frontend unit tests
- Original interactive terminal client for workshop use

## Prerequisites

- Python 3.11+
- Node.js 20.19+ or 22.12+
- An AWS account with access to the configured OpenAI model in Amazon Bedrock
- AWS credentials available through the standard SDK credential chain

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

## Run for development

Start the FastAPI backend:

```bash
source .venv/bin/activate
uvicorn bedrock_chat.api:app --reload
```

In another terminal, start Vite:

```bash
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` requests to FastAPI at
http://127.0.0.1:8000.

## Run the production build

Build React and start FastAPI:

```bash
cd frontend
npm run build
cd ..
source .venv/bin/activate
uvicorn bedrock_chat.api:app
```

Open http://127.0.0.1:8000. FastAPI serves `frontend/dist` along with the API.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `BEDROCK_MODEL_ID` | `openai.gpt-5.5` | Bedrock model ID |
| `BEDROCK_REGION` | `us-east-2` | Region, falling back to `AWS_REGION` or `AWS_DEFAULT_REGION` |
| `BEDROCK_MAX_TOKENS` | `1024` | Maximum response tokens |
| `BEDROCK_TEMPERATURE` | unset | Optional sampling temperature for models that support it |

GPT-5.x reasoning models reject `temperature`, so the application omits it
unless `BEDROCK_TEMPERATURE` is set.

## API

- `GET /api/health` returns readiness without contacting AWS.
- `GET /api/config` returns the active public model and Region.
- `POST /api/chat` accepts an alternating message history ending in a user
  message and returns the next assistant message.
- `POST /api/orders` creates an Order and returns its generated UUID.
- `GET /api/orders` lists Orders, and `GET /api/orders/{order_id}` returns one.
- `PATCH /api/orders/{order_id}` updates supplied fields on an Order.
- `PUT /api/orders/{order_id}` replaces all mutable fields on an Order.
- `DELETE /api/orders/{order_id}` deletes an Order.
- `/docs` exposes the generated OpenAPI interface while running the backend.

Orders contain a `customer_id`, one or more `{ "sku", "quantity" }` items, and
a `shipping_address`. New Orders start with `pending` status; updates may set
the status to `pending`, `processing`, `shipped`, `delivered`, or `cancelled`.
Order storage is in memory and is cleared whenever the backend restarts.

The browser stores conversations in local storage and sends the active history
with each request. The server does not persist or share chat sessions. Clearing
site data removes browser history. Long conversations resend more context and
can eventually exceed the model's context window.

Use the sun or moon button in the chat header to switch themes. The selected
theme is saved in the browser; new sessions otherwise follow the system color
scheme.

## Terminal client

The original terminal experience remains available:

```bash
source .venv/bin/activate
python -m bedrock_chat
```

Type `exit` or `quit` to leave.

## Test

Run the offline backend suite:

```bash
.venv/bin/python -m pytest tests/ -v
```

Run frontend unit tests and verify the production bundle:

```bash
cd frontend
npm test
npm run build
```

No AWS credentials or network calls are required by either unit test suite.

## Codex + Bedrock

See [`codex-config.example.toml`](./codex-config.example.toml) for a starting
Codex configuration and [`AGENTS.md`](./AGENTS.md) for project guidance.
