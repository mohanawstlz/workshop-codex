import {
  ArrowUp,
  Bot,
  Braces,
  Check,
  Code2,
  Copy,
  Eraser,
  Lightbulb,
  Menu,
  MessageSquare,
  Moon,
  PanelLeftClose,
  Plus,
  RotateCcw,
  Sparkles,
  Square,
  Sun,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";

import {
  createConversation,
  deriveTitle,
  loadConversations,
  saveConversations,
} from "./lib/conversations";

const SUGGESTIONS = [
  {
    icon: Code2,
    title: "Build a feature",
    prompt: "Help me design a resilient API for a new application feature.",
    tone: "coral",
  },
  {
    icon: Braces,
    title: "Review code",
    prompt: "Review this code for correctness, security, and maintainability.",
    tone: "blue",
  },
  {
    icon: Lightbulb,
    title: "Explore an idea",
    prompt: "Turn my rough product idea into a clear technical approach.",
    tone: "yellow",
  },
  {
    icon: MessageSquare,
    title: "Explain a concept",
    prompt: "Explain Amazon Bedrock and when I should use it.",
    tone: "green",
  },
];

const CONVERSATION_CLEARED = "conversation-cleared";
const MESSAGE_ENTRANCE_DURATION_MS = 240;
const THEME_STORAGE_KEY = "bedrock-chat-theme";

function getInitialTheme() {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === "light" || storedTheme === "dark") {
    return storedTheme;
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function updateConversation(conversations, id, updater) {
  return conversations.map((conversation) =>
    conversation.id === id ? updater(conversation) : conversation,
  );
}

async function readError(response) {
  try {
    const body = await response.json();
    return body.detail || "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}

function App() {
  const [conversations, setConversations] = useState(() => {
    const stored = loadConversations();
    return stored.length > 0 ? stored : [createConversation()];
  });
  const [activeId, setActiveId] = useState(() => conversations[0].id);
  const [draft, setDraft] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pending, setPending] = useState(null);
  const [failure, setFailure] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [enteringMessage, setEnteringMessage] = useState(null);
  const [theme, setTheme] = useState(getInitialTheme);
  const [config, setConfig] = useState({
    model: "OpenAI GPT",
    region: "Amazon Bedrock",
  });
  const textareaRef = useRef(null);
  const messagesEndRef = useRef(null);

  const activeConversation = useMemo(
    () =>
      conversations.find((conversation) => conversation.id === activeId) ??
      conversations[0],
    [activeId, conversations],
  );

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "dark" ? "#17191b" : "#ffffff");
  }, [theme]);

  useEffect(() => {
    fetch("/api/config")
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (body) {
          setConfig(body);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConversation?.messages, pending]);

  useEffect(() => {
    if (!enteringMessage) {
      return undefined;
    }
    const timeout = window.setTimeout(() => {
      setEnteringMessage((current) =>
        current === enteringMessage ? null : current,
      );
    }, MESSAGE_ENTRANCE_DURATION_MS);
    return () => window.clearTimeout(timeout);
  }, [enteringMessage]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [draft]);

  const beginNewConversation = useCallback(() => {
    pending?.controller.abort();
    const conversation = createConversation();
    setConversations((current) => [conversation, ...current]);
    setActiveId(conversation.id);
    setDraft("");
    setFailure(null);
    setPending(null);
    setSidebarOpen(false);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [pending]);

  const removeConversation = useCallback(
    (event, conversationId) => {
      event.stopPropagation();
      if (pending?.conversationId === conversationId) {
        pending.controller.abort();
        setPending(null);
      }
      setFailure((current) =>
        current?.conversationId === conversationId ? null : current,
      );
      setConversations((current) => {
        const remaining = current.filter(
          (conversation) => conversation.id !== conversationId,
        );
        if (remaining.length === 0) {
          const replacement = createConversation();
          setActiveId(replacement.id);
          return [replacement];
        }
        if (activeId === conversationId) {
          setActiveId(remaining[0].id);
        }
        return remaining;
      });
    },
    [activeId, pending],
  );

  const clearConversation = useCallback(() => {
    if (!activeConversation) {
      return;
    }
    if (pending?.conversationId === activeConversation.id) {
      pending.controller.abort(CONVERSATION_CLEARED);
      setPending(null);
    }
    setConversations((current) =>
      updateConversation(current, activeConversation.id, (conversation) => ({
        ...conversation,
        title: "New conversation",
        messages: [],
        updatedAt: new Date().toISOString(),
      })),
    );
    setFailure((current) =>
      current?.conversationId === activeConversation.id ? null : current,
    );
    setCopiedId(null);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [activeConversation, pending]);

  const sendConversation = useCallback(async (conversationId, messages) => {
    const controller = new AbortController();
    setPending({ conversationId, controller });
    setFailure(null);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages }),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(await readError(response));
      }
      const body = await response.json();
      setEnteringMessage(`${conversationId}:${messages.length}`);
      setConversations((current) =>
        updateConversation(current, conversationId, (conversation) => ({
          ...conversation,
          messages: [...conversation.messages, body.message],
          updatedAt: new Date().toISOString(),
        })),
      );
    } catch (error) {
      const wasCleared =
        error.name === "AbortError" &&
        controller.signal.reason === CONVERSATION_CLEARED;
      if (!wasCleared) {
        setFailure({
          conversationId,
          message:
            error.name === "AbortError"
              ? "Response stopped."
              : error.message || "The model request failed.",
        });
      }
    } finally {
      setPending((current) =>
        current?.conversationId === conversationId ? null : current,
      );
    }
  }, []);

  const submitMessage = useCallback(
    (event) => {
      event?.preventDefault();
      const content = draft.trim();
      if (!content || pending || !activeConversation) {
        return;
      }
      const userMessage = { role: "user", content };
      const messages = [...activeConversation.messages, userMessage];
      const conversationId = activeConversation.id;
      setEnteringMessage(`${conversationId}:${messages.length - 1}`);
      setConversations((current) =>
        updateConversation(current, conversationId, (conversation) => ({
          ...conversation,
          title:
            conversation.messages.length === 0
              ? deriveTitle(content)
              : conversation.title,
          messages,
          updatedAt: new Date().toISOString(),
        })),
      );
      setDraft("");
      sendConversation(conversationId, messages);
    },
    [activeConversation, draft, pending, sendConversation],
  );

  const retry = useCallback(() => {
    if (!activeConversation || pending) {
      return;
    }
    sendConversation(activeConversation.id, activeConversation.messages);
  }, [activeConversation, pending, sendConversation]);

  const selectConversation = (conversationId) => {
    setActiveId(conversationId);
    setFailure(null);
    setSidebarOpen(false);
  };

  const useSuggestion = (prompt) => {
    setDraft(prompt);
    requestAnimationFrame(() => textareaRef.current?.focus());
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  };

  const stopResponse = () => {
    pending?.controller.abort();
  };

  const dismissFailure = () => {
    if (!activeConversation) {
      return;
    }
    setConversations((current) =>
      updateConversation(current, activeConversation.id, (conversation) => ({
        ...conversation,
        messages:
          conversation.messages.at(-1)?.role === "user"
            ? conversation.messages.slice(0, -1)
            : conversation.messages,
        updatedAt: new Date().toISOString(),
      })),
    );
    setFailure(null);
  };

  const copyMessage = async (content, index) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(index);
    window.setTimeout(() => setCopiedId(null), 1400);
  };

  const hasUnansweredMessage =
    activeConversation?.messages.at(-1)?.role === "user" && !pending;

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close conversations"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`sidebar ${sidebarOpen ? "is-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true">
            <Sparkles size={18} strokeWidth={2.25} />
          </div>
          <div>
            <strong>Bedrock Chat</strong>
            <span>OpenAI on AWS</span>
          </div>
          <button
            className="icon-button sidebar-close"
            aria-label="Close conversations"
            title="Close conversations"
            onClick={() => setSidebarOpen(false)}
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        <button className="new-chat-button" onClick={beginNewConversation}>
          <Plus size={17} />
          New conversation
        </button>

        <div className="conversation-label">Recent</div>
        <nav className="conversation-list" aria-label="Conversations">
          {conversations.map((conversation) => (
            <div
              className={`conversation-item ${
                conversation.id === activeConversation?.id ? "active" : ""
              }`}
              key={conversation.id}
            >
              <button
                className="conversation-select"
                onClick={() => selectConversation(conversation.id)}
              >
                <MessageSquare size={16} aria-hidden="true" />
                <span>{conversation.title}</span>
              </button>
              <button
                className="delete-conversation"
                title="Delete conversation"
                aria-label={`Delete ${conversation.title}`}
                onClick={(event) => removeConversation(event, conversation.id)}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          <div>
            <strong>Connected through AWS</strong>
            <span>{config.region}</span>
          </div>
        </div>
      </aside>

      <main className="chat-panel">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Open conversations"
            title="Open conversations"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div className="model-identity">
            <Bot size={18} aria-hidden="true" />
            <div>
              <strong>{config.model}</strong>
              <span>{config.region}</span>
            </div>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-button theme-toggle"
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              onClick={() =>
                setTheme((current) => (current === "light" ? "dark" : "light"))
              }
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <button
              className="icon-button clear-chat"
              aria-label="Clear conversation"
              title="Clear conversation"
              disabled={!activeConversation?.messages.length}
              onClick={clearConversation}
            >
              <Eraser size={18} />
            </button>
            <button
              className="icon-button mobile-new-chat"
              aria-label="New conversation"
              title="New conversation"
              onClick={beginNewConversation}
            >
              <Plus size={20} />
            </button>
          </div>
        </header>

        <section className="chat-content" aria-live="polite">
          {activeConversation?.messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-mark" aria-hidden="true">
                <Sparkles size={28} />
              </div>
              <h1>Start a conversation</h1>
              <p>Ask a question, work through code, or develop an idea.</p>
              <div className="suggestion-grid">
                {SUGGESTIONS.map(
                  ({ icon: SuggestionIcon, title, prompt, tone }) => (
                    <button
                      className={`suggestion-card ${tone}`}
                      key={title}
                      onClick={() => useSuggestion(prompt)}
                    >
                      <SuggestionIcon size={19} aria-hidden="true" />
                      <span>
                        <strong>{title}</strong>
                        <small>{prompt}</small>
                      </span>
                      <ArrowUp size={16} className="suggestion-arrow" />
                    </button>
                  ),
                )}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {activeConversation.messages.map((message, index) => (
                <article
                  className={`message-row ${message.role} ${
                    enteringMessage === `${activeConversation.id}:${index}`
                      ? "message-entering"
                      : ""
                  }`}
                  key={`${message.role}-${index}`}
                >
                  <div className="message-avatar" aria-hidden="true">
                    {message.role === "assistant" ? (
                      <Sparkles size={17} />
                    ) : (
                      <UserRound size={17} />
                    )}
                  </div>
                  <div className="message-body">
                    <div className="message-author">
                      {message.role === "assistant" ? "Bedrock Chat" : "You"}
                    </div>
                    {message.role === "assistant" ? (
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    ) : (
                      <p>{message.content}</p>
                    )}
                    {message.role === "assistant" && (
                      <button
                        className="message-action"
                        title="Copy response"
                        aria-label="Copy response"
                        onClick={() => copyMessage(message.content, index)}
                      >
                        {copiedId === index ? (
                          <Check size={15} />
                        ) : (
                          <Copy size={15} />
                        )}
                      </button>
                    )}
                  </div>
                </article>
              ))}

              {pending?.conversationId === activeConversation.id && (
                <article className="message-row assistant">
                  <div className="message-avatar thinking" aria-hidden="true">
                    <Sparkles size={17} />
                  </div>
                  <div className="message-body">
                    <div className="message-author">Bedrock Chat</div>
                    <div className="thinking-line">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </article>
              )}

              {failure?.conversationId === activeConversation.id && (
                <div className="error-strip" role="alert">
                  <span>{failure.message}</span>
                  <button onClick={retry}>
                    <RotateCcw size={15} />
                    Retry
                  </button>
                  <button
                    className="dismiss-error"
                    aria-label="Dismiss error"
                    title="Discard failed message"
                    onClick={dismissFailure}
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </section>

        <div className="composer-region">
          <form className="composer" onSubmit={submitMessage}>
            <textarea
              ref={textareaRef}
              value={draft}
              rows={1}
              maxLength={50_000}
              aria-label="Message Bedrock Chat"
              placeholder={
                hasUnansweredMessage
                  ? "Retry the last message before continuing"
                  : "Message Bedrock Chat"
              }
              disabled={hasUnansweredMessage}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleKeyDown}
            />
            {pending ? (
              <button
                type="button"
                className="send-button stop"
                aria-label="Stop response"
                title="Stop response"
                onClick={stopResponse}
              >
                <Square size={15} fill="currentColor" />
              </button>
            ) : (
              <button
                type="submit"
                className="send-button"
                aria-label="Send message"
                title="Send message"
                disabled={!draft.trim() || hasUnansweredMessage}
              >
                <ArrowUp size={19} strokeWidth={2.5} />
              </button>
            )}
          </form>
          <p className="composer-note">
            Responses may be inaccurate. Verify important information.
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
