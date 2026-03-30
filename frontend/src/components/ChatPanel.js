import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User } from "lucide-react";

function renderMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>');
}

export default function ChatPanel({ messages, onSend, isLoading, projectStatus }) {
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      const el = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (el) el.scrollTop = el.scrollHeight;
    }
  }, [messages, isLoading]);

  function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput("");
  }

  const canChat = ["INIT", "GATHERING", "COMPLETE", "ERROR"].includes(projectStatus);

  return (
    <div className="flex flex-col h-full" data-testid="chat-panel">
      {/* Chat Header */}
      <div className="px-4 py-3 border-b border-[var(--zap-border)]">
        <h3 className="text-sm font-semibold tracking-tight" style={{ fontFamily: 'var(--font-heading)' }}>
          AI Assistant
        </h3>
        <p className="text-xs text-[var(--zap-text-muted)] mt-0.5">
          {projectStatus === "GATHERING" ? "Gathering requirements..." :
           projectStatus === "COMPLETE" ? "Ready for modifications" :
           ["ARCHITECTING","TRANSFORMING","GENERATING_FRONTEND","GENERATING_BACKEND","REVIEWING"].includes(projectStatus) ?
           "Building your ERP..." : "Describe your ERP system"}
        </p>
      </div>

      {/* Messages */}
      <ScrollArea ref={scrollRef} className="flex-1 px-4 py-3">
        <div className="space-y-3">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-12 animate-fade-in-up" data-testid="chat-empty-state">
              <Bot className="w-8 h-8 text-[var(--zap-text-muted)] mx-auto mb-3" />
              <p className="text-sm text-[var(--zap-text-muted)]">
                Your AI assistant is ready.<br />
                Describe the ERP system you want to build.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={msg.id || i}
              className={`flex gap-2 animate-fade-in-up ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              data-testid={`chat-message-${msg.role}-${i}`}
            >
              {msg.role !== "user" && (
                <div className="w-6 h-6 rounded-sm bg-[var(--zap-accent)]/10 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5 text-[var(--zap-accent)]" />
                </div>
              )}
              <div className={`max-w-[85%] px-3 py-2 text-sm leading-relaxed ${
                msg.role === "user" ? "chat-msg-user" : "chat-msg-assistant"
              }`}>
                <div
                  className="chat-content"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                />
              </div>
              {msg.role === "user" && (
                <div className="w-6 h-6 rounded-sm bg-[var(--zap-primary)] flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5 text-white" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-2 animate-fade-in-up" data-testid="chat-loading-indicator">
              <div className="w-6 h-6 rounded-sm bg-[var(--zap-accent)]/10 flex items-center justify-center shrink-0">
                <Bot className="w-3.5 h-3.5 text-[var(--zap-accent)]" />
              </div>
              <div className="chat-msg-assistant px-3 py-3">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-[var(--zap-border)]">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            data-testid="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={canChat ? "Type your message..." : "Processing..."}
            disabled={!canChat || isLoading}
            className="flex-1 h-9 px-3 text-sm border border-[var(--zap-border)] rounded-sm bg-white
                       focus:outline-none focus:ring-2 focus:ring-[var(--zap-accent)] focus:ring-offset-1
                       disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ fontFamily: 'var(--font-body)' }}
          />
          <Button
            data-testid="chat-send-btn"
            type="submit"
            disabled={!canChat || isLoading || !input.trim()}
            className="h-9 w-9 p-0 bg-[var(--zap-primary)] text-white hover:bg-black/80 rounded-sm
                       disabled:opacity-30"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
