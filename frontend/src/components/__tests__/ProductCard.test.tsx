import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it } from "vitest";

import ProductCard from "../ProductCard";
import { touringBoardFixture } from "../../lib/fixtures";

// `vite.config.ts` runs Vitest with `globals: false`, so RTL's automatic
// afterEach(cleanup) (which relies on a global `afterEach`) never registers.
afterEach(cleanup);

describe("ProductCard", () => {
  it("shows brand, model, and price from the fixture", () => {
    render(createElement(ProductCard, { board: touringBoardFixture }));

    expect(screen.getByText(touringBoardFixture.brand)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: touringBoardFixture.model }),
    ).toBeInTheDocument();
    expect(screen.getByText("$899")).toBeInTheDocument();
  });

  it("renders the best-for pill tags and an Add to compare affordance", () => {
    render(createElement(ProductCard, { board: touringBoardFixture }));

    for (const tag of touringBoardFixture.best_for) {
      expect(screen.getByText(tag)).toBeInTheDocument();
    }
    expect(
      screen.getByRole("button", { name: "Add to compare" }),
    ).toBeInTheDocument();
  });
});
