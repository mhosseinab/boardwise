import "@testing-library/jest-dom/vitest";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../../App";
import CatalogPanel from "../CatalogPanel";
import { getBoards, postChat } from "../../lib/api";
import {
  compactTouringBoardFixture,
  touringBoardFixture,
} from "../../lib/fixtures";
import type { ChatResponse } from "../../lib/types";

// `vite.config.ts` runs Vitest with `globals: false`, so RTL's automatic
// afterEach(cleanup) (which relies on a global `afterEach`) never registers.
afterEach(() => {
  cleanup();
  vi.mocked(getBoards).mockReset();
  vi.mocked(postChat).mockReset();
});

vi.mock("../../lib/api", () => ({
  getBoards: vi.fn(),
  postChat: vi.fn(),
}));

const mockedGetBoards = vi.mocked(getBoards);
const mockedPostChat = vi.mocked(postChat);

const catalogFixture = [touringBoardFixture, compactTouringBoardFixture];

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    createElement(QueryClientProvider, { client: queryClient }, ui),
  );
}

function renderApp() {
  return renderWithQueryClient(createElement(App));
}

describe("catalog panel (S17)", () => {
  it("renders fixture boards from the catalog", async () => {
    mockedGetBoards.mockResolvedValueOnce(catalogFixture);

    renderWithQueryClient(
      createElement(CatalogPanel, { onAskAboutBoard: vi.fn() }),
    );

    expect(
      await screen.findByText(touringBoardFixture.model),
    ).toBeInTheDocument();
    expect(
      screen.getByText(compactTouringBoardFixture.model),
    ).toBeInTheDocument();
  });

  it("refetches with a skill_level param when the skill filter changes", async () => {
    mockedGetBoards.mockResolvedValue(catalogFixture);

    renderWithQueryClient(
      createElement(CatalogPanel, { onAskAboutBoard: vi.fn() }),
    );

    await screen.findByText(touringBoardFixture.model);

    fireEvent.change(screen.getByLabelText("Skill level filter"), {
      target: { value: "beginner" },
    });

    await screen.findByText(touringBoardFixture.model);
    expect(mockedGetBoards).toHaveBeenLastCalledWith(
      expect.objectContaining({ skill_level: "beginner" }),
    );
  });

  it("calls onAskAboutBoard with a question containing the board's model when clicked", async () => {
    mockedGetBoards.mockResolvedValueOnce(catalogFixture);
    const onAskAboutBoard = vi.fn();

    renderWithQueryClient(
      createElement(CatalogPanel, { onAskAboutBoard }),
    );

    const boardButton = await screen.findByRole("button", {
      name: new RegExp(touringBoardFixture.model.replace(/"/g, ""), "i"),
    });
    fireEvent.click(boardButton);

    expect(onAskAboutBoard).toHaveBeenCalledTimes(1);
    expect(onAskAboutBoard.mock.calls[0][0]).toContain(
      touringBoardFixture.model,
    );
  });

  it("shows the mock-data banner text on initial render", () => {
    mockedGetBoards.mockResolvedValueOnce(catalogFixture);
    renderApp();

    expect(
      screen.getByText("Specs are mock data for demonstration."),
    ).toBeInTheDocument();
  });

  it("clicking a catalog board in the app seeds a chat question via the composer submit", async () => {
    mockedGetBoards.mockResolvedValueOnce(catalogFixture);
    const chatResponse: ChatResponse = {
      answer: "Here's what I know about that board.",
      cards: [touringBoardFixture],
      tables: [],
      compatibility: [],
      tools_used: [],
      refused: false,
      prompt_version: "v1",
    };
    mockedPostChat.mockResolvedValueOnce(chatResponse);

    renderApp();

    const boardList = await screen.findByRole("list", { name: "Boards" });
    const boardButton = within(boardList).getByRole("button", {
      name: new RegExp(touringBoardFixture.model.replace(/"/g, ""), "i"),
    });
    fireEvent.click(boardButton);

    await screen.findByRole("heading", { name: touringBoardFixture.model });
    expect(mockedPostChat.mock.calls[0][0].message).toContain(
      touringBoardFixture.model,
    );
  });
});
