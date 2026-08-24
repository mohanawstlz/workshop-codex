// @vitest-environment jsdom

import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { STORAGE_KEY } from "./lib/conversations";

beforeEach(() => {
  const values = new Map();
  vi.stubGlobal("localStorage", {
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  });
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("submits a user message and renders the assistant response", async () => {
    let resolveChat;
    const fetchMock = vi.fn((url, options) => {
      if (url === "/api/config") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              model: "openai.test-model",
              region: "us-test-1",
            }),
        });
      }
      if (url === "/api/chat") {
        return new Promise((resolve) => {
          resolveChat = () =>
            resolve({
              ok: true,
              json: () =>
                Promise.resolve({
                  message: {
                    role: "assistant",
                    content: "**Test response** from Bedrock.",
                  },
                  model: "openai.test-model",
                  region: "us-test-1",
                }),
            });
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const composer = screen.getByLabelText("Message Bedrock Chat");
    fireEvent.change(composer, { target: { value: "Hello model" } });
    fireEvent.click(screen.getByLabelText("Send message"));

    const userMessage = await screen.findByText("Hello model", {
      selector: ".message-body p",
    });
    expect(userMessage.closest("article").classList).toContain(
      "message-entering",
    );

    await act(async () => resolveChat());

    const assistantMessage = await screen.findByText("Test response");
    expect(assistantMessage.closest("article").classList).toContain(
      "message-entering",
    );
    await waitFor(() =>
      expect(screen.getByText("openai.test-model")).toBeTruthy(),
    );

    const chatCall = fetchMock.mock.calls.find(([url]) => url === "/api/chat");
    expect(JSON.parse(chatCall[1].body)).toEqual({
      messages: [{ role: "user", content: "Hello model" }],
    });
  });

  it("clears the active conversation history", async () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        {
          id: "chat-1",
          title: "Existing conversation",
          messages: [
            { role: "user", content: "Saved question" },
            { role: "assistant", content: "Saved answer" },
          ],
          createdAt: "2026-08-24T12:00:00.000Z",
          updatedAt: "2026-08-24T12:01:00.000Z",
        },
      ]),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(null),
        }),
      ),
    );

    render(<App />);
    fireEvent.click(screen.getByLabelText("Clear conversation"));

    expect(screen.queryByText("Saved question")).toBeNull();
    expect(screen.queryByText("Saved answer")).toBeNull();
    expect(screen.getByText("Start a conversation")).toBeTruthy();
    expect(screen.getByLabelText("Clear conversation").disabled).toBe(true);

    await waitFor(() => {
      const [stored] = JSON.parse(localStorage.getItem(STORAGE_KEY));
      expect(stored.messages).toEqual([]);
      expect(stored.title).toBe("New conversation");
    });
  });
});
