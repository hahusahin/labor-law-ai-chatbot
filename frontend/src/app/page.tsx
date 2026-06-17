"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";

// ---------- types ----------------------------------------------------------

type SourceChunk = {
  law: string;
  article_number: string;
  article_type: string;
  article_title: string | null;
  text: string;
};

type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; sources: SourceChunk[] }
  | { role: "error"; content: string; question: string };

// ---------- constants -------------------------------------------------------

const EXAMPLE_QUESTIONS = [
  "Yıllık izin hakkım kaç gün?",
  "Kıdem tazminatı nasıl hesaplanır?",
  "İhbar süreleri nedir?",
  "Fazla mesai ücreti nasıl ödenir?",
];

// ---------- sub-components --------------------------------------------------

function SourceBadge({
  source,
  isOpen,
  onToggle,
}: {
  source: SourceChunk;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const label = `${source.article_type} ${source.article_number}`;

  return (
    <Badge
      variant="outline"
      className="cursor-pointer select-none hover:bg-zinc-200 hover:border-zinc-400 hover:text-zinc-900 dark:hover:bg-zinc-700 dark:hover:border-zinc-500 transition-all duration-150"
      onClick={onToggle}
    >
      {label}
      <span className="ml-1 opacity-60">{isOpen ? "▲" : "▼"}</span>
    </Badge>
  );
}

function SourceList({ sources }: { sources: SourceChunk[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  function toggle(i: number) {
    setOpenIndex((prev) => (prev === i ? null : i));
  }

  const open = openIndex !== null ? sources[openIndex] : null;
  const openLabel = open
    ? `${open.article_type} ${open.article_number}`
    : null;
  const openTitle = open?.article_title ? ` — ${open.article_title}` : "";

  return (
    <div className="pl-1 space-y-2 mt-1">
      {/* badge row — never shifts */}
      <div className="flex flex-wrap gap-1.5">
        {sources.map((src, i) => (
          <SourceBadge
            key={i}
            source={src}
            isOpen={openIndex === i}
            onToggle={() => toggle(i)}
          />
        ))}
      </div>
      {/* expanded panel — always below all badges */}
      {open && (
        <div className="max-w-[80%] rounded-md border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 p-3 text-xs text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed">
          <p className="font-semibold mb-1 text-zinc-900 dark:text-zinc-100">
            {openLabel}
            {openTitle}
          </p>
          {open.text}
        </div>
      )}
    </div>
  );
}

function LoadingBubble() {
  return (
    <div className="flex gap-2 items-end">
      <div className="rounded-2xl rounded-bl-sm bg-zinc-100 dark:bg-zinc-800 px-4 py-3">
        <span className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="block h-2 w-2 rounded-full bg-zinc-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </span>
      </div>
    </div>
  );
}

// ---------- main page -------------------------------------------------------

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function fetchAnswer(question: string) {
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal: AbortSignal.timeout(95_000),
      });

      if (!res.ok) throw new Error(`Service returned ${res.status}`);

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, sources: data.sources },
      ]);
    } catch (err) {
      const isTimeout =
        err instanceof DOMException && err.name === "TimeoutError";
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          question,
          content: isTimeout
            ? "Yanıt zaman aşımına uğradı."
            : "Bir hata oluştu.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function send(question: string) {
    if (!question.trim() || loading) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    await fetchAnswer(question);
  }

  function retry(question: string, errorIndex: number) {
    setMessages((prev) => prev.filter((_, i) => i !== errorIndex));
    fetchAnswer(question);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  const isEmpty = messages.length === 0 && !loading;

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-zinc-950">
      {/* header */}
      <header className="shrink-0 border-b border-zinc-200 dark:border-zinc-800 px-6 py-5 text-center">
        <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
          İş Hukuku Asistanı
        </h1>
        <p className="mt-0.5 text-xs text-zinc-500">
          Türk iş mevzuatına dayalı sorularınızı yanıtlar
        </p>
      </header>

      {/* messages */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="px-4 py-6 max-w-3xl mx-auto space-y-6">
          {isEmpty && (
            <div className="flex flex-col items-center gap-6 pt-16 text-center">
              <div>
                <p className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                  Merhaba
                </p>
                <p className="mt-1 text-sm text-zinc-500">
                  İş hukukuyla ilgili bir soru sorun
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="rounded-full border border-zinc-200 dark:border-zinc-700 px-4 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 hover:border-zinc-400 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:border-zinc-500 transition-all duration-150 cursor-pointer"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => {
            if (msg.role === "user") {
              return (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-zinc-900 dark:bg-zinc-100 px-4 py-2.5 text-sm text-white dark:text-zinc-900">
                    {msg.content}
                  </div>
                </div>
              );
            }

            if (msg.role === "error") {
              return (
                <div key={i} className="flex justify-start">
                  <div className="max-w-[80%] rounded-2xl rounded-bl-sm border border-red-200 bg-red-50 dark:bg-red-950/30 px-4 py-2.5 text-sm text-red-700 dark:text-red-400">
                    <span>{msg.content}</span>
                    <button
                      onClick={() => retry(msg.question, i)}
                      className="ml-2 underline underline-offset-2 hover:opacity-70 transition-opacity"
                    >
                      Tekrar dene
                    </button>
                  </div>
                </div>
              );
            }

            return (
              <div key={i} className="flex flex-col gap-1">
                <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-zinc-100 dark:bg-zinc-800 px-4 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 leading-relaxed">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                      ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
                      li: ({ children }) => <li>{children}</li>,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
                {msg.sources.length > 0 && (
                  <SourceList sources={msg.sources} />
                )}
              </div>
            );
          })}

          {loading && <LoadingBubble />}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* input */}
      <div className="shrink-0 border-t border-zinc-200 dark:border-zinc-800 px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Sorunuzu yazın… (Enter ile gönderin)"
            disabled={loading}
            rows={1}
            className="resize-none min-h-10.5 max-h-36 overflow-y-auto"
          />
          <Button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            size="sm"
            className="shrink-0 h-10.5 px-4"
          >
            Gönder
          </Button>
        </div>
      </div>
    </div>
  );
}
