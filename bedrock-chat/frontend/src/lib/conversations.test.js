import { describe, expect, it } from "vitest";

import {
  STORAGE_KEY,
  createConversation,
  deriveTitle,
  loadConversations,
  saveConversations,
} from "./conversations";

function memoryStorage(initialValue = null) {
  let value = initialValue;
  return {
    getItem: () => value,
    setItem: (key, nextValue) => {
      expect(key).toBe(STORAGE_KEY);
      value = nextValue;
    },
  };
}

describe("conversation storage", () => {
  it("creates a new empty conversation", () => {
    const conversation = createConversation({
      id: "chat-1",
      createdAt: "2026-08-24T12:00:00.000Z",
    });

    expect(conversation).toEqual({
      id: "chat-1",
      title: "New conversation",
      messages: [],
      createdAt: "2026-08-24T12:00:00.000Z",
      updatedAt: "2026-08-24T12:00:00.000Z",
    });
  });

  it("derives compact titles from the first message", () => {
    expect(deriveTitle("  Explain   Amazon Bedrock  ")).toBe(
      "Explain Amazon Bedrock",
    );
    expect(deriveTitle("x".repeat(60))).toBe(`${"x".repeat(41)}...`);
  });

  it("round trips valid conversations", () => {
    const storage = memoryStorage();
    const conversations = [createConversation({ id: "chat-1" })];

    saveConversations(conversations, storage);

    expect(loadConversations(storage)).toEqual(conversations);
  });

  it("recovers from missing, malformed, and invalid stored data", () => {
    expect(loadConversations(memoryStorage())).toEqual([]);
    expect(loadConversations(memoryStorage("{broken"))).toEqual([]);
    expect(loadConversations(memoryStorage('[{"id": 1}]'))).toEqual([]);
  });
});
