import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it } from "vitest";

import CompatBadge from "../CompatBadge";
import {
  compatibleResultFixture,
  compatibleWithCaveatsResultFixture,
  incompatibleResultFixture,
} from "../../lib/fixtures";

// `vite.config.ts` runs Vitest with `globals: false`, so RTL's automatic
// afterEach(cleanup) (which relies on a global `afterEach`) never registers.
afterEach(cleanup);

describe("CompatBadge", () => {
  it("maps a compatible verdict (no caveats) to green", () => {
    render(createElement(CompatBadge, { result: compatibleResultFixture }));

    const badge = screen.getByRole("status", { name: "Compatible" });
    expect(badge).toHaveClass("text-compat-green");
    expect(
      screen.getByText(compatibleResultFixture.reason),
    ).toBeInTheDocument();
  });

  it("maps a compatible-with-caveats verdict to amber and lists the caveats", () => {
    render(
      createElement(CompatBadge, {
        result: compatibleWithCaveatsResultFixture,
      }),
    );

    const badge = screen.getByRole("status", {
      name: "Compatible with caveats",
    });
    expect(badge).toHaveClass("text-compat-amber");
    for (const caveat of compatibleWithCaveatsResultFixture.caveats) {
      expect(screen.getByText(caveat)).toBeInTheDocument();
    }
  });

  it("maps an incompatible verdict to red", () => {
    render(createElement(CompatBadge, { result: incompatibleResultFixture }));

    const badge = screen.getByRole("status", { name: "Incompatible" });
    expect(badge).toHaveClass("text-compat-red");
  });
});
