# In-Memory Conversation History Implementation Plan

## Implementation status

**Status:** Complete as of August 24, 2026.

- [x] Step 1: Add tests for the expected client behavior.
- [x] Step 2: Make history updates transactional.
- [x] Step 3: Add interactive-loop coverage.
- [x] Step 4: Update documentation.
- [x] Step 5: Run the complete offline suite and review the changes.

Final verification:

```text
25 passed in 0.39s
```

Bytecode compilation and whitespace checks also passed.

## Deviations from the original plan

1. **Conversation history already existed.** The interactive REPL already
   reused one `BedrockChatClient`, and the client already included prior turns
   in later requests. The production change therefore hardened the existing
   behavior instead of introducing a new history mechanism.
2. **No `bedrock_chat/__main__.py` refactor was needed.** The existing entry
   point was testable by replacing `input` and `BedrockChatClient` in
   `tests/test_main.py`, so the optional `run_interactive()` extraction was not
   performed.
3. **Empty text responses now have an explicit policy.** A response with no
   extracted output text raises `ValueError` and does not commit a partial
   conversation turn.
4. **Additional edge-case coverage was added.** Tests cover Unicode,
   multiline, and large messages; interruption during transport; recovery
   after a failed request; and continued REPL operation after an API error.
5. **No explicit single-message mode was added.** The repository does not have
   such a mode; callers remain stateless by creating a fresh client for each
   message, as planned.
6. **No dependencies or configuration files changed.** The existing
   user-owned modification to `codex-config.example.toml` was preserved.

## Original state

The requested behavior is already mostly present:

- `BedrockChatClient` stores history per client instance.
- The interactive REPL creates one client before entering its input loop.
- Each request includes the accumulated history from that client.

The implementation work should therefore focus on verifying multi-turn
behavior, making history updates safe when requests fail, and documenting the
history lifecycle. There is currently no explicit single-message CLI mode.
A caller can remain stateless by creating a fresh client for each request.

## Files to modify or create

### Modify

#### `bedrock_chat/client.py`

- Preserve per-instance in-memory history.
- Build a request from committed history plus the current user message.
- Commit the user and assistant messages only after a successful, valid
  response.
- Ensure a failed transport, malformed response, or response-processing error
  does not leave a partial turn in history.
- Update docstrings to make the history lifecycle explicit.

#### `tests/test_client.py`

- Add multi-turn request and history tests.
- Add tests proving that client instances do not share history.
- Add failure tests proving that incomplete turns are not committed.
- Preserve the existing offline fake-transport pattern.

#### `README.md`

- Explain that interactive sessions remember earlier turns.
- Clarify that history exists only for the lifetime of the process.
- Explain that starting a new client creates a fresh conversation.
- Document the current lack of persistence and automatic history trimming.

### Create

#### `tests/test_main.py`

- Test the interactive loop with fake input and a fake client.
- Verify that one client is constructed and reused for multiple messages.
- Verify that empty input and exit commands are not sent to the client.
- Keep all tests offline.

### Files that should not require changes

- `bedrock_chat/config.py`
- `bedrock_chat/__init__.py`
- `pyproject.toml`
- `requirements.txt`
- `codex-config.example.toml`

`bedrock_chat/__main__.py` should not require a behavior change because it
already creates one client before entering the loop. It should be modified only
if a small extraction or injection point is necessary to test that behavior
cleanly.

## History contract

The implementation and tests should enforce the following rules:

1. History belongs to one `BedrockChatClient` instance.
2. A new client starts with empty history.
3. A request contains all completed earlier exchanges followed by the current
   user message.
4. A successful request commits the user message and assistant reply together.
5. A failed request commits neither message.
6. History is stored only in memory and is not shared or persisted.
7. A caller that creates a fresh client for every request remains stateless.

## Order of changes

### 1. Add tests for the expected client behavior — Completed

Extend `tests/test_client.py` with tests that initially expose any missing or
unsafe behavior:

- The first request contains only the first user message.
- After the first response, history contains the first complete exchange.
- The second request contains:
  `user 1 -> assistant 1 -> user 2`.
- After the second response, history contains both complete exchanges.
- Two clients have independent history lists.
- A transport exception leaves history unchanged.
- A response-processing exception leaves history unchanged.

These tests establish the behavior contract before changing production code.

### 2. Make history updates transactional — Completed

Update `BedrockChatClient.send()` to use a pending request input:

```text
user_message = build current user message
pending_input = committed history + user_message
send pending_input
extract and validate assistant reply
commit user_message and assistant_message
return assistant reply
```

The existing implementation appends the user message before calling the
transport. Moving the commit until after a successful response prevents a
timeout or API error from polluting the next request.

Use a new list for `pending_input` rather than exposing the live history list to
the request payload. Keep all AWS-specific behavior inside `client.py`, and
preserve the lazy `boto3` import and injectable transport.

### 3. Add interactive-loop coverage — Completed

Create `tests/test_main.py` and simulate an interactive session:

1. Return two user messages from a fake input function.
2. Return `exit` or raise `EOFError` to end the loop.
3. Replace `BedrockChatClient` with a fake that records construction and calls.
4. Assert that exactly one client instance handled both messages.
5. Assert that messages were sent in the expected order.
6. Verify that blank messages and exit commands were not sent.

If this cannot be tested cleanly through monkeypatching, extract a small
`run_interactive(client, input_fn=...)` helper from `__main__.py`. Keep the
helper focused and avoid introducing a larger CLI framework.

### 4. Update documentation — Completed

Update `README.md` after the behavior is settled. Document:

- Interactive chat remembers prior turns during the current session.
- Closing the application clears the history.
- History is resent with each request.
- Long conversations may consume more tokens and eventually exceed model
  context limits.
- Stateless use is achieved with a fresh client per message.

### 5. Run verification — Completed

Run the complete offline suite:

```bash
pytest
```

All existing and new tests must pass without AWS credentials or network
access.

## Testing requirements

### Multi-turn behavior

- First request has the correct single-message input.
- Second and later requests include all prior completed turns in exact order.
- Responses are appended after their corresponding user messages.
- Unicode, multiline, and large messages are preserved without transformation.

### Isolation and lifecycle

- New clients start with empty history.
- Separate clients never share history.
- History is lost when the client is discarded.
- Inference settings remain stable across turns.

### Failure behavior

- Transport failures leave history unchanged.
- JSON or response-processing failures leave history unchanged.
- A successful request after a failed request does not include the failed turn.
- Interruptions during a request do not leave a partially committed exchange.

### Interactive behavior

- The REPL reuses one client for multiple turns.
- Empty input does not enter history.
- `exit` and `quit`, regardless of case, do not enter history.
- `EOFError` and `KeyboardInterrupt` end the session cleanly.
- An API error does not terminate the REPL.

### Regression coverage

- Endpoint selection remains unchanged.
- Model and inference parameters remain unchanged.
- Temperature remains omitted by default.
- Response extraction continues to ignore reasoning items and join text blocks.

## Risks and edge cases

### Partial history after failures

Before implementation, the client recorded the user message before making the
network request. This has been resolved: complete exchanges are now committed
only after a successful response is extracted and validated.

### Empty or non-text responses

`extract_text()` returns an empty string when no `output_text` block exists.
This can happen with malformed responses or responses containing only
reasoning or tool items.

The implemented policy treats an empty reply as an error and leaves history
unchanged. This is appropriate for the current text-only client, but it may
need revisiting if tool-only or other non-text response types are supported.

### Unbounded context growth

Every request resends the complete conversation. Long sessions increase:

- Token usage and cost
- Request latency
- Request size
- The risk of exceeding the model context window

Automatic trimming, summarization, and token accounting are outside the
initial scope. The limitation should be documented so a future enhancement can
address it deliberately.

### Ambiguous stateless behavior

No explicit single-message mode exists in the current repository. Stateless
callers must create a fresh client for each request. A future single-message
entry point must avoid reusing a process-global or long-lived client.

### Retry duplication

Bedrock may process a request even if the client receives a timeout. Retrying
could produce a second remote response. Transactional local history prevents
local corruption but cannot provide exactly-once remote execution.

### Concurrency

`BedrockChatClient` is not thread-safe. Simultaneous calls to `send()` could
interleave requests and commits. This is acceptable for the current
single-threaded terminal REPL and should remain outside the initial scope.

### Public mutable history

The public `history` list can be modified by callers, potentially creating
invalid role ordering or message shapes. It can remain public for this sample,
but should be documented or exposed through a read-only copy if the public API
becomes more important.

### Sensitive content

All earlier conversation content remains in process memory and is resent in
subsequent requests. Users should understand that later requests include prior
messages, including any sensitive information entered earlier.

### Model or setting changes during a conversation

Settings are attached to the client when it is created. Reusing history with a
different model or inference configuration would need an explicit policy.
The current application should keep settings fixed for the life of a client.

## Acceptance criteria

The completed work satisfies all acceptance criteria:

- [x] The interactive REPL sends earlier completed turns with each new message.
- [x] Only complete, successful exchanges are committed to history.
- [x] Failed turns never appear in subsequent requests.
- [x] Separate clients remain isolated, and stateless callers can use fresh
  instances.
- [x] The complete test suite passes offline.
- [x] The README accurately describes memory scope and limitations.
