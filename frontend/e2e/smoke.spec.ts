/**
 * S18 offline smoke test: example prompt chip -> product cards + spec table.
 *
 * Fully offline (decision §4.12): `page.route` intercepts every network call
 * the app makes (`GET /api/boards*` for the catalog panel's mount fetch and
 * `POST /api/chat` for the composer/example-prompt flow) and fulfills them
 * with the S15 typed fixtures (`src/lib/fixtures.ts`) — no backend process,
 * no `LLM_API_KEY`, no real network traffic.
 */
import { expect, test } from "@playwright/test";

import {
  compactTouringBoardFixture,
  specTableFixture,
  touringBoardFixture,
} from "../src/lib/fixtures";
import type { BoardCard, ChatResponse } from "../src/lib/types";

const boardsFixture: BoardCard[] = [
  touringBoardFixture,
  compactTouringBoardFixture,
];

const chatResponseFixture: ChatResponse = {
  answer: "Here are two touring boards that fit your ask.",
  cards: [touringBoardFixture, compactTouringBoardFixture],
  tables: [specTableFixture],
  compatibility: [],
  tools_used: [],
  refused: false,
  prompt_version: "v1",
};

test("clicking an example prompt renders product cards and a spec table", async ({
  page,
}) => {
  await page.route("**/api/boards**", async (route) => {
    await route.fulfill({ json: boardsFixture });
  });

  await page.route("**/api/chat", async (route) => {
    await route.fulfill({ json: chatResponseFixture });
  });

  await page.goto("/");

  await expect(
    page.getByText("Specs are mock data for demonstration."),
  ).toBeVisible();

  const examplePrompts = page.getByRole("list", { name: "Example prompts" });
  await examplePrompts.getByRole("button").first().click();

  const cards = page.getByRole("list", { name: "Boards" });
  await expect(
    cards.getByRole("article", {
      name: `${touringBoardFixture.brand} ${touringBoardFixture.model}`,
    }),
  ).toBeVisible();
  await expect(cards.getByRole("article")).toHaveCount(2);

  await expect(page.getByText(specTableFixture.title)).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
});
