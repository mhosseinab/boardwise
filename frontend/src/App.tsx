// Chat pane wired up in S16; the catalog side panel and persistent
// mock-data banner are added by S17.
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";

import ChatPane, { type ChatExchange } from "./components/ChatPane";
import Composer from "./components/Composer";
import ExamplePrompts from "./components/ExamplePrompts";
import { postChat } from "./lib/api";

function App() {
  const [exchanges, setExchanges] = useState<ChatExchange[]>([]);
  const nextId = useRef(0);
  const mutation = useMutation({ mutationFn: postChat });

  function submitMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed) return;

    const id = `exchange-${nextId.current++}`;
    setExchanges((previous) => [
      ...previous,
      { id, prompt: trimmed, status: "pending" },
    ]);

    mutation.mutate(
      { message: trimmed },
      {
        onSuccess: (response) => {
          setExchanges((previous) =>
            previous.map((exchange) =>
              exchange.id === id
                ? { ...exchange, status: "success", response }
                : exchange,
            ),
          );
        },
        onError: (error) => {
          setExchanges((previous) =>
            previous.map((exchange) =>
              exchange.id === id
                ? {
                    ...exchange,
                    status: "error",
                    error:
                      error instanceof Error
                        ? error.message
                        : "Something went wrong.",
                  }
                : exchange,
            ),
          );
        },
      },
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-surface/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-4">
          <span
            className="inline-block h-6 w-6 rounded-full bg-primary"
            aria-hidden="true"
          />
          <h1 className="font-heading text-xl font-semibold text-primary">
            BoardWise
          </h1>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
        {exchanges.length === 0 ? (
          <ExamplePrompts onSelect={submitMessage} />
        ) : (
          <ChatPane exchanges={exchanges} />
        )}
        <Composer onSubmit={submitMessage} disabled={mutation.isPending} />
      </main>
    </div>
  );
}

export default App;
