export const STORAGE_KEY = "bedrock-chat-conversations-v1";

function makeId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createConversation(overrides = {}) {
  const timestamp = overrides.createdAt ?? new Date().toISOString();
  return {
    id: overrides.id ?? makeId(),
    title: overrides.title ?? "New conversation",
    messages: overrides.messages ?? [],
    createdAt: timestamp,
    updatedAt: overrides.updatedAt ?? timestamp,
  };
}

export function deriveTitle(content) {
  const normalized = content.replace(/\s+/g, " ").trim();
  if (normalized.length <= 42) {
    return normalized;
  }
  return `${normalized.slice(0, 41).trimEnd()}...`;
}

export function loadConversations(storage = globalThis.localStorage) {
  try {
    const parsed = JSON.parse(storage.getItem(STORAGE_KEY));
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (conversation) =>
        conversation &&
        typeof conversation.id === "string" &&
        typeof conversation.title === "string" &&
        Array.isArray(conversation.messages),
    );
  } catch {
    return [];
  }
}

export function saveConversations(
  conversations,
  storage = globalThis.localStorage,
) {
  storage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}
