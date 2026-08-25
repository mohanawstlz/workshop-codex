# Tutorial: Understand Chat Session State Management

## Learning goal

By the end of this tutorial, you will be able to:

- identify where chat state lives in the terminal and web applications;
- trace a message from the browser to Bedrock and back;
- explain why failed model calls do not corrupt completed history; and
- verify session behavior with offline tests.

This tutorial is for Python or JavaScript developers who know basic HTTP and
can read small React and FastAPI examples. You do not need AWS credentials
because every exercise uses a fake client or transport.

## Prerequisites

From the repository root, install the development dependencies described in
the README. The commands below assume the Python virtual environment is
`.venv` and the frontend dependencies are already installed.

Verify the starting point:

```bash
.venv/bin/python -m pytest tests/test_client.py tests/test_api.py -q
cd frontend && npm test -- src/lib/conversations.test.js && cd ..
```

Expected result: both commands pass without making a network request.

## 1. Build the mental model

The project has two session models:

| Interface | Source of truth | Lifetime |
|---|---|---|
| Terminal | `BedrockChatClient.history` | One Python process |
| Web | React `conversations`, persisted in browser `localStorage` | Until the browser data is cleared |

The web API is deliberately stateless. It does not store sessions, issue
session IDs, or use a conversation database. The browser sends the complete
active conversation with each request.

```text
Browser localStorage
        |
        v
React conversations state
        |
        | POST /api/chat with every message in the active conversation
        v
FastAPI creates a fresh BedrockChatClient
        |
        | seeds prior turns, then sends the latest user turn
        v
Bedrock Responses API
        |
        v
React appends the assistant reply and saves the conversation
```

This distinction matters: `BedrockChatClient` can remember turns, but the web
server creates a new instance for every request. Browser state provides web
continuity; client instance reuse provides terminal continuity.

### Checkpoint

Before continuing, answer these questions:

1. Does restarting FastAPI erase web conversations?
2. Does opening the terminal application create a new conversation?

Answers:

1. No. Existing web conversations remain in that browser's `localStorage`.
2. Yes. The terminal creates a new `BedrockChatClient` with empty in-memory
   history.

## 2. Observe the client's transactional update

Open `bedrock_chat/client.py` and find `BedrockChatClient.send`. Its state
transition has three stages:

1. Build `pending_input` from completed history plus the new user message.
2. Call the transport and extract a non-empty assistant reply.
3. Append both the user message and assistant reply to `history`.

The key line is conceptually:

```python
pending_input = [*self.history, user_message]
```

This creates a new request list without changing `self.history`. The method
commits the two new messages only after the transport and response parsing
succeed. That makes a completed user/assistant pair the unit of state.

Run this offline demonstration:

```bash
.venv/bin/python - <<'PY'
import json

from bedrock_chat.client import BedrockChatClient
from bedrock_chat.config import Settings

calls = []
replies = iter(["Paris.", "About 2.1 million."])


def fake_transport(url, headers, body):
    calls.append(json.loads(body))
    reply = next(replies)
    return {
        "output": [{
            "type": "message",
            "content": [{"type": "output_text", "text": reply}],
        }]
    }


client = BedrockChatClient(Settings(), transport=fake_transport)
client.send("What is the capital of France?")
client.send("What is its population?")

print(json.dumps(calls[1]["input"], indent=2))
PY
```

Expected result: the second request contains the first completed exchange,
followed by the second user message:

```json
[
  {
    "role": "user",
    "content": "What is the capital of France?"
  },
  {
    "role": "assistant",
    "content": "Paris."
  },
  {
    "role": "user",
    "content": "What is its population?"
  }
]
```

The second assistant reply is not in that request. It is appended only after
the response arrives.

### Checkpoint

Run the focused contract test:

```bash
.venv/bin/python -m pytest \
  tests/test_client.py::test_send_includes_completed_history_on_later_turns -q
```

Expected result: `1 passed`.

## 3. See why failed turns roll back

Because the new user message is kept in `pending_input`, transport errors,
interruptions, malformed responses, and empty replies leave `history`
unchanged.

Run the failure tests:

```bash
.venv/bin/python -m pytest tests/test_client.py \
  -k "failure_leaves_history_unchanged or empty_text_response" -q
```

Expected result: the selected tests pass.

This behavior prevents a later request from containing a user question for
which no assistant answer was recorded. It also means callers can retry
without first repairing the client's history.

### Exercise

Predict the value of `client.history` after this sequence:

1. `send("first")` returns `"answer"`.
2. `send("second")` raises a transport error.

Answer:

```python
[
    {"role": "user", "content": "first"},
    {"role": "assistant", "content": "answer"},
]
```

Only completed exchanges become durable client state.

## 4. Trace one web request

Now follow the browser path in `frontend/src/App.jsx`.

### Step 4.1: Append the user message

`submitMessage` trims the draft and creates:

```javascript
const userMessage = { role: "user", content };
const messages = [...activeConversation.messages, userMessage];
```

React immediately stores this new list in the active conversation. This is an
optimistic update: the user sees their message before the model replies.

### Step 4.2: Send the complete conversation

`sendConversation` posts that same `messages` list:

```json
{
  "messages": [
    {"role": "user", "content": "First question"},
    {"role": "assistant", "content": "First answer"},
    {"role": "user", "content": "Follow up"}
  ]
}
```

The request contains no browser conversation ID. The ID organizes local UI
state only; the backend needs the ordered messages.

### Step 4.3: Validate and reconstruct temporary client state

In `bedrock_chat/api.py`, `ChatRequest` requires messages to:

- alternate between `user` and `assistant`;
- start and end with `user`; and
- contain non-blank text.

The route then creates a fresh client, seeds all but the final message as
completed history, and sends the final user message:

```python
client = client_factory(resolved_settings)
client.history = [message.model_dump() for message in request.messages[:-1]]
reply = client.send(request.messages[-1].content)
```

Splitting the list avoids duplicating the latest user message. `send` adds it
to `pending_input` exactly once.

### Step 4.4: Commit the assistant reply in the browser

FastAPI returns one assistant message. React appends it to the matching
conversation:

```javascript
messages: [...conversation.messages, body.message]
```

The API client is then discarded. The browser's updated message list remains
the source of truth for the next request.

### Checkpoint

Verify the reconstruction boundary:

```bash
.venv/bin/python -m pytest \
  tests/test_api.py::test_chat_passes_prior_history_and_latest_user_message -q
```

Expected result: `1 passed`. The fake client receives prior turns in
`history` and the final question through `send`.

## 5. Understand browser persistence

Open `frontend/src/lib/conversations.js`. Each stored conversation has this
shape:

```javascript
{
  id: "browser-local-id",
  title: "First question",
  messages: [
    { role: "user", content: "First question" },
    { role: "assistant", content: "First answer" },
  ],
  createdAt: "2026-08-24T12:00:00.000Z",
  updatedAt: "2026-08-24T12:01:00.000Z",
}
```

At startup, `loadConversations` parses the value stored under
`bedrock-chat-conversations-v1`. If no valid conversations exist, React
creates an empty one. After any conversation change, an effect calls
`saveConversations`.

The helper rejects malformed top-level data, but `localStorage` is still
client-controlled persistence. The FastAPI validation boundary must continue
to validate every submitted conversation.

Run the storage tests:

```bash
cd frontend
npm test -- src/lib/conversations.test.js
cd ..
```

Expected result: tests cover creation, title derivation, persistence round
trips, and recovery from malformed stored data.

### Checkpoint

Classify each value as persistent conversation state or temporary UI state:

| Value | Classification |
|---|---|
| `conversations` | Persistent conversation state |
| `activeId` | Temporary UI state |
| `draft` | Temporary UI state |
| `pending` and its `AbortController` | Temporary request state |
| `failure` | Temporary request state |
| Conversation `messages` | Persistent conversation state |

Only `conversations` is written to the conversation storage key.

## 6. Follow stop, retry, dismiss, and clear

Failure handling differs slightly between the core client and browser because
the browser optimistically displays the user message.

- **Stop:** aborts the request. The unanswered user message remains visible.
- **Retry:** resends the active message list, whose last item is that user
  message.
- **Dismiss:** removes the final unanswered user message and clears the error.
- **Clear:** empties the active conversation and aborts its pending request.
- **New conversation:** creates a separate empty local conversation.
- **Delete:** removes one local conversation and creates a replacement if it
  was the last one.

The composer is disabled while an unanswered user message exists. This
preserves the alternating role invariant required by `ChatRequest`.

Run the relevant interface tests:

```bash
cd frontend
npm test -- src/App.test.jsx
cd ..
```

Expected result: the tests verify message submission, assistant response
handling, and clearing persisted history.

## 7. Compare the terminal lifecycle

The terminal entry point in `bedrock_chat/__main__.py` creates one client
before entering its input loop:

```python
client = BedrockChatClient(settings)

while True:
    # Read input...
    reply = client.send(user_input)
```

Reusing that object lets `client.history` accumulate completed turns. Exiting
the process discards the object and its history. There is no `localStorage`,
API reconstruction, or disk persistence in this path.

Verify that the REPL reuses one client:

```bash
.venv/bin/python -m pytest \
  tests/test_main.py::test_main_reuses_one_client_and_ignores_blank_and_exit -q
```

Expected result: `1 passed`.

## Design consequences

The current design is simple and avoids server-side session coordination, but
it has deliberate tradeoffs:

- every web request resends the full conversation;
- token use and latency grow as history grows;
- conversations are available only in the browser that stored them;
- clearing site data removes web history;
- terminal history disappears when the process exits; and
- old turns are not trimmed or summarized automatically.

Adding accounts, cross-device synchronization, shared conversations, or
server-enforced retention would require a server-side conversation store and
an authorization model. Those are not hidden capabilities of the current
session design.

## Summary

You can now trace state through both interfaces:

1. The terminal keeps completed turns in one in-memory client.
2. The web browser owns persistent conversation state and sends it on every
   request.
3. FastAPI validates that state and reconstructs a short-lived client.
4. `BedrockChatClient.send` commits a turn only after receiving valid output.
5. Offline tests verify each boundary without AWS access.
