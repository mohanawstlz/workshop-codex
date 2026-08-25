# AGENTS.md — bedrock-chat

Guidance for Codex (and other coding agents) working in this project.

## What this project is

A minimal terminal chat app that talks to GPT models on **Amazon Bedrock**
using Bedrock's OpenAI-compatible **responses** endpoint
(`bedrock-mantle.<region>.api.aws/openai/v1/responses`) with SigV4 auth. This
is the same surface Codex uses — the GPT-5.x models are not served by the
Converse API. It is the sample project for
Part 2 of the OpenAI on AWS workshop.

## Layout

- `bedrock_chat/config.py` — environment-driven `Settings` (model, region, inference params). No AWS calls.
- `bedrock_chat/client.py` — `BedrockChatClient` (conversation history + SigV4-signed responses-API call) and pure helpers `build_message` / `extract_text`. The HTTP transport is injectable for offline tests.
- `bedrock_chat/__main__.py` — interactive REPL: `python -m bedrock_chat`.
- `tests/` — pytest suite. Fully offline: the client accepts an injected fake, helpers are pure.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Talk to Bedrock (needs AWS credentials + model access):
python -m bedrock_chat
```

Config comes from the environment: `BEDROCK_MODEL_ID`, `BEDROCK_REGION`
(falls back to `AWS_REGION` / `AWS_DEFAULT_REGION`), `BEDROCK_MAX_TOKENS`,
`BEDROCK_TEMPERATURE`.

## Test

```bash
pytest
```

Tests must never require live AWS access — keep new tests offline by injecting a
fake client or exercising pure helpers.

## Conventions for changes

- Keep AWS-touching code isolated in `client.py`; keep helpers pure and tested.
- `boto3` is imported lazily so the test suite runs without AWS setup — preserve that.
- Add a test with every behavior change; run `pytest` before finishing.
- Match the existing style: type hints, module docstrings, small focused functions.


# Team Codex Configuration

## Bash commands
- python -m bedrock_chat: Run the chat application
- printf "message\nquit\n" | python -m bedrock_chat: Send scripted input (for testing)
- python -m pytest tests/ -v: Run unit tests
- python -m pytest tests/ -v --tb=short: Run tests with short tracebacks

## Code style
- Use Python 3.11+ with type hints on all function signatures
- Follow PEP 8 style with 100-character line limit
- Use f-strings for string formatting
- IMPORTANT: Always include error handling around API calls
- Add docstrings to all public functions and classes

## Workflow
- Run tests after every change: python -m pytest tests/ -v
- YOU MUST write unit tests for new functions
- Always update README.md when adding new features
- Use descriptive commit messages that explain WHY, not just WHAT

## Repository structure
- bedrock_chat/__main__.py: Main CLI entry point
- bedrock_chat/config.py: Runtime model and region configuration
- tests/: Unit tests (mirror the module structure)

## API patterns
- Use the OpenAI Responses API (client.responses.create)
- Always pass model as a parameter (don't hardcode)
- Handle openai.BadRequestError and openai.NotFoundError explicitly


## Custom Commands

### /add-feature
Add a new feature to the chat application:
1. Create or modify the appropriate module
2. Add type hints and docstrings
3. Write unit tests in tests/
4. Update README.md with usage instructions
5. Run full test suite to verify nothing is broken

### /debug-issue
Debug systematically:
1. Read error logs and identify root cause
2. Search codebase for similar patterns
3. Check git history for related commits
4. Reproduce in minimal test case
5. Implement fix with error handling
6. Write regression test

### /review-code
Review code changes:
1. Check code quality and PEP 8 adherence
2. Verify all new code has tests
3. Look for security vulnerabilities (API key exposure, injection)
4. Ensure proper error handling around API calls
5. Validate type hints are complete
