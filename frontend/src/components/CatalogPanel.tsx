/**
 * CatalogPanel — the browsable catalog side panel (SPEC "Frontend
 * requirements": browsable catalog side panel). Lists boards from
 * `GET /api/boards` via TanStack Query, with filters (type, skill, rider
 * capacity, price) wired to the API's query params (`lib/api.ts`
 * `BoardFilters`); clicking a board seeds a chat question about it via
 * `onAskAboutBoard`, which the caller wires to the composer's submit
 * handler.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getBoards, type BoardFilters } from "../lib/api";
import type { BoardCard } from "../lib/types";

const BOARD_TYPES = ["touring", "yoga", "whitewater", "racing", "all-around"];
const SKILL_LEVELS = ["beginner", "intermediate", "advanced"];

export interface CatalogPanelProps {
  /** Called with a templated question when a board row/card is clicked. */
  onAskAboutBoard: (question: string) => void;
}

/** Templates a chat question for a catalog board (seeded into the composer). */
function boardQuestion(board: BoardCard): string {
  return `Tell me more about the ${board.brand} ${board.model}.`;
}

function LoadingSkeleton() {
  return (
    <ul
      role="status"
      aria-label="Loading boards"
      className="animate-pulse space-y-2"
    >
      {[0, 1, 2].map((index) => (
        <li key={index} className="h-16 rounded-card bg-slate-100" />
      ))}
    </ul>
  );
}

function CatalogPanel({ onAskAboutBoard }: CatalogPanelProps) {
  const [boardType, setBoardType] = useState("");
  const [skillLevel, setSkillLevel] = useState("");
  const [minCapacityKg, setMinCapacityKg] = useState("");
  const [maxPriceUsd, setMaxPriceUsd] = useState("");

  const filters: BoardFilters = {
    board_type: boardType || undefined,
    skill_level: skillLevel || undefined,
    min_capacity_kg: minCapacityKg ? Number(minCapacityKg) : undefined,
    max_price_usd: maxPriceUsd ? Number(maxPriceUsd) : undefined,
  };

  const {
    data: boards,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["boards", filters],
    queryFn: () => getBoards(filters),
  });

  return (
    <aside
      aria-label="Board catalog"
      className="w-full max-w-xs shrink-0 space-y-4 rounded-card border border-border bg-surface p-4 shadow-soft lg:sticky lg:top-6 lg:self-start"
    >
      <h2 className="font-heading text-lg font-semibold text-slate-900">
        Browse the catalog
      </h2>

      <fieldset aria-label="Catalog filters" className="space-y-2">
        <legend className="sr-only">Catalog filters</legend>
        <label className="flex flex-col text-xs text-slate-500">
          Board type
          <select
            aria-label="Board type filter"
            value={boardType}
            onChange={(event) => setBoardType(event.target.value)}
            className="rounded-card border border-border px-2 py-1 text-sm text-slate-800"
          >
            <option value="">Any</option>
            {BOARD_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs text-slate-500">
          Skill level filter
          <select
            aria-label="Skill level filter"
            value={skillLevel}
            onChange={(event) => setSkillLevel(event.target.value)}
            className="rounded-card border border-border px-2 py-1 text-sm text-slate-800"
          >
            <option value="">Any</option>
            {SKILL_LEVELS.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs text-slate-500">
          Min rider capacity (kg)
          <input
            type="number"
            aria-label="Minimum rider capacity (kg)"
            value={minCapacityKg}
            onChange={(event) => setMinCapacityKg(event.target.value)}
            className="rounded-card border border-border px-2 py-1 text-sm text-slate-800"
          />
        </label>
        <label className="flex flex-col text-xs text-slate-500">
          Max price (USD)
          <input
            type="number"
            aria-label="Maximum price (USD)"
            value={maxPriceUsd}
            onChange={(event) => setMaxPriceUsd(event.target.value)}
            className="rounded-card border border-border px-2 py-1 text-sm text-slate-800"
          />
        </label>
      </fieldset>

      {isLoading && <LoadingSkeleton />}

      {isError && (
        <p className="text-sm text-compat-red">Couldn't load the catalog.</p>
      )}

      {boards && boards.length === 0 && (
        <p className="text-sm text-slate-500">
          No boards match those filters.
        </p>
      )}

      {boards && boards.length > 0 && (
        <ul aria-label="Boards" className="space-y-2">
          {boards.map((board) => (
            <li key={board.id}>
              <button
                type="button"
                onClick={() => onAskAboutBoard(boardQuestion(board))}
                className="w-full rounded-card border border-border bg-surface p-3 text-left text-sm shadow-soft transition-colors duration-200 hover:bg-primary-50"
              >
                <p className="font-medium text-primary">{board.brand}</p>
                <p className="font-heading font-semibold text-slate-900">
                  {board.model}
                </p>
                <p className="text-xs text-slate-500">
                  {board.board_type} &middot; {board.skill_level} &middot; $
                  {board.price_usd}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

export default CatalogPanel;
