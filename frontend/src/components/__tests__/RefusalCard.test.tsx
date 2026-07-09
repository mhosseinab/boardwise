import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import RefusalCard from "../RefusalCard";
import { refusedChatResponseFixture } from "../../lib/fixtures";

describe("RefusalCard", () => {
  it("renders the refusal text and a distinct scope-limit heading", () => {
    render(
      createElement(RefusalCard, {
        answer: refusedChatResponseFixture.answer,
      }),
    );

    expect(
      screen.getByText(refusedChatResponseFixture.answer),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("note", { name: "Off-topic request" }),
    ).toBeInTheDocument();
  });
});
