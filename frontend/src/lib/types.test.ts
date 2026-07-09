import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import App from "../App";
import type { ChatResponse } from "./types";

describe("ChatResponse contract mirror", () => {
  it("type-checks a ChatResponse fixture object field-for-field", () => {
    // If this object literal did not satisfy the `ChatResponse` interface
    // mirrored from backend/app/schemas.py, `tsc` would fail the build/CI
    // step before this assertion ever ran.
    const fixture: ChatResponse = {
      answer: "The Aquara Atlas 12 is a solid touring board.",
      cards: [
        {
          id: "aquara-atlas-12",
          brand: "Aquara",
          model: "Atlas 12",
          length_ft: 12,
          width_in: 30,
          thickness_in: 6,
          volume_l: 300,
          max_rider_weight_kg: 120,
          recommended_psi: 15,
          max_psi: 18,
          board_type: "touring",
          skill_level: "intermediate",
          fin_box: "US-box",
          valve_type: "H3",
          board_weight_kg: 9.5,
          price_usd: 899,
          best_for: ["long-distance", "flatwater"],
          image_url: "/images/touring.svg",
          is_mock: true,
        },
      ],
      tables: [],
      compatibility: [],
      tools_used: [
        {
          name: "search_boards",
          args: { board_type: "touring" },
          result_summary: "1 board found",
          latency_ms: 12,
        },
      ],
      refused: false,
      prompt_version: "v1",
    };

    expect(fixture.answer).toContain("Aquara");
    expect(fixture.cards).toHaveLength(1);
    expect(fixture.refused).toBe(false);
  });
});

describe("App shell", () => {
  it("renders without crashing and shows the BoardWise name", () => {
    render(createElement(App));

    expect(
      screen.getByRole("heading", { name: "BoardWise" }),
    ).toBeInTheDocument();
  });
});
