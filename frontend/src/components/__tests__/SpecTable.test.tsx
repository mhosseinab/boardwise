import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it } from "vitest";

import SpecTable from "../SpecTable";
import { specTableFixture } from "../../lib/fixtures";

// `vite.config.ts` runs Vitest with `globals: false`, so RTL's automatic
// afterEach(cleanup) (which relies on a global `afterEach`) never registers.
afterEach(cleanup);

describe("SpecTable", () => {
  it("renders all columns as headers", () => {
    render(createElement(SpecTable, { table: specTableFixture }));

    for (const column of specTableFixture.columns) {
      expect(
        screen.getByRole("columnheader", { name: column }),
      ).toBeInTheDocument();
    }
  });

  it("renders every row's cells", () => {
    render(createElement(SpecTable, { table: specTableFixture }));

    for (const row of specTableFixture.rows) {
      for (const cell of row) {
        expect(screen.getByText(cell)).toBeInTheDocument();
      }
    }
  });

  it("highlights the cheaper board's price cell as the winner", () => {
    render(createElement(SpecTable, { table: specTableFixture }));

    const cheaperPriceCell = screen.getByText("749");
    expect(cheaperPriceCell).toHaveClass("text-primary");
  });
});
