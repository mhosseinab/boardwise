import "@testing-library/jest-dom/vitest";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../../App";
import { postChat } from "../../lib/api";
import {
  refusedChatResponseFixture,
  touringBoardFixture,
} from "../../lib/fixtures";
import type { ChatResponse } from "../../lib/types";

// `vite.config.ts` runs Vitest with `globals: false`, so RTL's automatic
// afterEach(cleanup) (which relies on a global `afterEach`) never registers.
afterEach(() => {
  cleanup();
  vi.mocked(postChat).mockReset();
});

vi.mock("../../lib/api", () => ({
  postChat: vi.fn(),
}));

const mockedPostChat = vi.mocked(postChat);

const groundedResponseFixture: ChatResponse = {
  answer: "Here's a great touring option for you.",
  cards: [touringBoardFixture],
  tables: [],
  compatibility: [],
  tools_used: [],
  refused: false,
  prompt_version: "v1",
};

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(App),
    ),
  );
}

describe("chat pane (S16)", () => {
  it("submit flow renders a ProductCard from the grounded fixture", async () => {
    mockedPostChat.mockResolvedValueOnce(groundedResponseFixture);
    renderApp();

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Show me a touring board" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByRole("heading", { name: touringBoardFixture.model }),
    ).toBeInTheDocument();
    // TanStack Query's mutationFn is invoked with a second context arg
    // ({ client, meta, mutationKey }); assert only the payload we sent.
    expect(mockedPostChat.mock.calls[0][0]).toEqual({
      message: "Show me a touring board",
    });
  });

  it("renders a RefusalCard when the response is refused", async () => {
    mockedPostChat.mockResolvedValueOnce(refusedChatResponseFixture);
    renderApp();

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "What's the weather like today?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByRole("note", { name: "Off-topic request" }),
    ).toBeInTheDocument();
  });

  it("shows a loading skeleton while the request is pending", async () => {
    let resolveResponse: (value: ChatResponse) => void = () => {};
    mockedPostChat.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveResponse = resolve;
        }),
    );
    renderApp();

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Show me a touring board" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByRole("status", { name: "Loading response" }),
    ).toBeInTheDocument();

    resolveResponse(groundedResponseFixture);

    await waitFor(() =>
      expect(
        screen.queryByRole("status", { name: "Loading response" }),
      ).not.toBeInTheDocument(),
    );
  });

  it("submits an example prompt's text when a chip is clicked", async () => {
    mockedPostChat.mockResolvedValueOnce(groundedResponseFixture);
    renderApp();

    const chip = screen.getByRole("button", {
      name: /compare the aquara atlas/i,
    });
    fireEvent.click(chip);

    await waitFor(() => expect(mockedPostChat).toHaveBeenCalledTimes(1));
    expect(mockedPostChat.mock.calls[0][0].message).toMatch(
      /compare the aquara atlas/i,
    );
  });

  it("templates the rider-profile quick-fill into the composer message", () => {
    renderApp();

    fireEvent.change(screen.getByLabelText("Weight (kg)"), {
      target: { value: "75" },
    });
    fireEvent.change(screen.getByLabelText("Skill level"), {
      target: { value: "beginner" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add my profile" }));

    const textarea = screen.getByLabelText("Message") as HTMLTextAreaElement;
    expect(textarea.value).toContain("75kg");
    expect(textarea.value).toContain("beginner skill level");
  });

  it("submits the message when Enter is pressed in the composer", async () => {
    mockedPostChat.mockResolvedValueOnce(groundedResponseFixture);
    renderApp();

    const textarea = screen.getByLabelText("Message");
    fireEvent.change(textarea, {
      target: { value: "Show me a touring board" },
    });
    fireEvent.keyDown(textarea, { key: "Enter", code: "Enter" });

    await waitFor(() =>
      expect(mockedPostChat.mock.calls[0][0]).toEqual({
        message: "Show me a touring board",
      }),
    );
  });

  it("renders a graceful error state when the request fails", async () => {
    mockedPostChat.mockRejectedValueOnce(new Error("network down"));
    renderApp();

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Show me a touring board" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "network down",
    );
  });
});
