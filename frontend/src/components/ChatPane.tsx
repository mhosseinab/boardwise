/**
 * ChatPane — the warm, centered chat thread (SPEC "Frontend requirements").
 * Renders each turn's `ChatResponse` via the S15 typed components
 * (ProductCard/SpecTable/CompatBadge/RefusalCard); the model's free-text
 * `answer` is the ONLY thing rendered via `react-markdown` — every
 * structured spec (boards, tables, compatibility) goes through its typed
 * component, never through markdown/raw HTML.
 */
import ReactMarkdown from "react-markdown";

import type { ChatResponse } from "../lib/types";
import CompatBadge from "./CompatBadge";
import ProductCard from "./ProductCard";
import RefusalCard from "./RefusalCard";
import SpecTable from "./SpecTable";

/** One turn in the thread: the user's prompt plus its (in-flight/settled) reply. */
export interface ChatExchange {
  id: string;
  prompt: string;
  status: "pending" | "success" | "error";
  response?: ChatResponse;
  error?: string;
}

export interface ChatPaneProps {
  exchanges: ChatExchange[];
}

function UserMessage({ prompt }: { prompt: string }) {
  return (
    <p className="ml-auto max-w-md rounded-card bg-primary px-4 py-2 text-sm text-white shadow-soft">
      {prompt}
    </p>
  );
}

function LoadingSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading response"
      className="max-w-md animate-pulse space-y-2 rounded-card border border-border bg-surface p-4 shadow-soft"
    >
      <div className="h-4 w-3/4 rounded bg-slate-200" />
      <div className="h-4 w-full rounded bg-slate-200" />
      <div className="h-4 w-5/6 rounded bg-slate-200" />
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="max-w-md rounded-card border border-compat-red/30 bg-compat-red/5 p-4 text-sm text-compat-red shadow-soft"
    >
      Something went wrong: {message}
    </div>
  );
}

function ResponseView({ response }: { response: ChatResponse }) {
  if (response.refused) {
    return <RefusalCard answer={response.answer} />;
  }

  return (
    <div className="space-y-4">
      <div className="max-w-2xl text-sm text-slate-700">
        <ReactMarkdown>{response.answer}</ReactMarkdown>
      </div>

      {response.cards.length > 0 && (
        <div role="list" aria-label="Boards" className="grid gap-4 sm:grid-cols-2">
          {response.cards.map((card) => (
            <ProductCard key={card.id} board={card} />
          ))}
        </div>
      )}

      {response.tables.map((table) => (
        <SpecTable key={table.title} table={table} />
      ))}

      {response.compatibility.map((result) => (
        <CompatBadge
          key={`${result.board_id}-${result.accessory_id}`}
          result={result}
        />
      ))}
    </div>
  );
}

function ChatPane({ exchanges }: ChatPaneProps) {
  return (
    <ol
      role="log"
      aria-label="Conversation"
      aria-live="polite"
      className="space-y-6"
    >
      {exchanges.map((exchange) => (
        <li key={exchange.id} className="space-y-3">
          <UserMessage prompt={exchange.prompt} />
          {exchange.status === "pending" && <LoadingSkeleton />}
          {exchange.status === "error" && (
            <ErrorState message={exchange.error ?? "Please try again."} />
          )}
          {exchange.status === "success" && exchange.response && (
            <ResponseView response={exchange.response} />
          )}
        </li>
      ))}
    </ol>
  );
}

export default ChatPane;
