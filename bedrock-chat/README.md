# bedrock-chat

A minimal terminal chat app that talks to GPT models on **Amazon Bedrock**
(via Bedrock's OpenAI-compatible responses API). This is the sample project used throughout
**Part 2** of the OpenAI on AWS workshop.

## Prerequisites

- Python 3.9+
- An AWS account with Amazon Bedrock access and the `openai.gpt-5.4` or
  `openai.gpt-5.5` model enabled in your target Region
- AWS credentials available to the AWS SDK (env vars, `aws configure`, SSO, or a named profile)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m bedrock_chat
```

Then type messages at the `you>` prompt. Type `exit` or `quit` to leave.

### Conversation history

The interactive chat remembers completed user and assistant turns for the
current session. Each new request includes the earlier conversation so the
model can respond in context. Failed requests are not added to the history.

History is held only in memory:

- Closing the process or creating a new `BedrockChatClient` starts a fresh
  conversation.
- Nothing is written to disk or shared between client instances.
- A stateless caller can create a new client for each message.

The complete history is resent with every request. Long conversations therefore
use more tokens, take longer, and may eventually exceed the model's context
window. This sample does not automatically trim or summarize older turns.

### Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `BEDROCK_MODEL_ID` | `openai.gpt-5.5` | Bedrock model id |
| `BEDROCK_REGION` | `us-east-2` | Region (falls back to `AWS_REGION` / `AWS_DEFAULT_REGION`) |
| `BEDROCK_MAX_TOKENS` | `1024` | Max response tokens |
| `BEDROCK_TEMPERATURE` | _(unset)_ | Sampling temperature. Omitted by default — GPT-5.x reasoning models reject it; set only for models that support it. |

## Test

```bash
pytest
```

The test suite runs fully offline — no AWS credentials required.

## Codex + Bedrock

To drive this project with the Codex CLI/App pointed at Bedrock, see
[`codex-config.example.toml`](./codex-config.example.toml) for a starting
`~/.codex/config.toml`, and [`AGENTS.md`](./AGENTS.md) for agent guidance.
