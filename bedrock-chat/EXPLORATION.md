# Repository Exploration

## What the project does

`bedrock-chat` is a minimal Python terminal chat application for GPT models
hosted on Amazon Bedrock. It is the sample project for Part 2 of the OpenAI on
AWS workshop.

The application:

1. Reads the model, AWS Region, and inference settings from environment
   variables.
2. Accepts messages through an interactive terminal prompt.
3. Maintains the conversation history in memory.
4. Sends the history to Bedrock's OpenAI-compatible Responses API endpoint:
   `https://bedrock-mantle.<region>.api.aws/openai/v1/responses`.
5. Authenticates requests with AWS Signature Version 4 using the standard AWS
   credential chain.
6. Extracts text from the response and displays it in the terminal.

The project deliberately uses the Responses API rather than the Bedrock
Converse API because the targeted GPT-5.x models are served through that
surface.

## Architecture and important files

### `bedrock_chat/__main__.py`

The executable entry point for:

```bash
python -m bedrock_chat
```

It creates the settings and client, then runs the `you>` / `gpt>` terminal
loop. Empty messages are ignored, `exit` and `quit` end the session, and API
errors are reported without terminating the REPL.

### `bedrock_chat/config.py`

Contains the `Settings` dataclass and environment-variable resolution. The
supported variables are:

- `BEDROCK_MODEL_ID`
- `BEDROCK_REGION`, falling back to `AWS_REGION` and
  `AWS_DEFAULT_REGION`
- `BEDROCK_MAX_TOKENS`
- `BEDROCK_TEMPERATURE`

The default temperature is unset because the targeted GPT-5.x reasoning models
reject that parameter.

This module performs no AWS calls, making it straightforward to test.

### `bedrock_chat/client.py`

Contains the main application behavior:

- `build_message()` validates and constructs Responses API messages.
- `extract_text()` extracts and joins `output_text` blocks while ignoring
  reasoning items.
- `_sigv4_transport()` obtains AWS credentials, signs requests, and sends them
  with `urllib`.
- `BedrockChatClient` maintains conversation history and constructs API
  requests.

The HTTP transport is injectable. Tests can therefore supply a fake transport
without loading AWS credentials or making network requests. `boto3` is also
imported lazily so AWS setup is only required for live use.

### `bedrock_chat/__init__.py`

Defines the package metadata and exposes the main public objects:

- `BedrockChatClient`
- `Settings`
- `extract_text`

### `tests/`

The test suite is fully offline:

- `tests/test_client.py` covers message construction, response extraction,
  endpoint selection, inference parameters, conversation history, and request
  payloads.
- `tests/test_config.py` covers defaults, environment overrides, and AWS Region
  precedence.

### Project metadata and documentation

- `README.md` documents prerequisites, setup, configuration, and usage.
- `pyproject.toml` declares Python 3.9+, the `boto3` dependency, and pytest
  configuration.
- `requirements.txt` installs both the runtime and test dependencies.
- `codex-config.example.toml` provides an example Codex configuration for
  connecting through Amazon Bedrock.
- `AGENTS.md` contains the project-specific instructions that coding agents
  must follow.

## Running locally

Create an environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the terminal application:

```bash
python -m bedrock_chat
```

Live use requires AWS credentials discoverable through the AWS SDK credential
chain and access to the configured model in the selected Region.

## Running tests

```bash
pytest
```

The suite does not require AWS credentials or network access. At the time of
this exploration, all 13 tests passed.

Every behavior change should include a corresponding offline test, and the full
suite should be run before finishing.

## Files to inspect before making a change

For most changes, inspect these files in this order:

1. `AGENTS.md` for repository-specific constraints.
2. `bedrock_chat/client.py` for the request, transport, response, and
   conversation behavior.
3. `tests/test_client.py` for the expected client behavior and testing pattern.
4. `bedrock_chat/config.py` and `tests/test_config.py` for configuration
   changes.
5. `bedrock_chat/__main__.py` for terminal interaction or error-handling
   changes.
6. `README.md`, `pyproject.toml`, and `requirements.txt` when changing setup,
   dependencies, supported Python versions, or documented behavior.

Changes involving AWS should remain isolated in `client.py`. New helper
functions should remain pure where practical, and live AWS access must never be
required by the tests.

## Current working-tree note

During this exploration, `codex-config.example.toml` already contained an
uncommitted modification. That change is user-owned and should be preserved
when making unrelated changes.
