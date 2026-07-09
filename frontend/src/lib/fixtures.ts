/**
 * Typed fixture payloads for RTL component tests (S15) and later reuse by
 * S16/S18. Fictional brands only (Aquara/Riptide/Zephyr/Cascade/Velocity/
 * Fjord — SPEC "Data & fixtures"); every board-shaped row carries
 * `is_mock: true`.
 */
import type {
  BoardCard,
  ChatResponse,
  CompatibilityResult,
  SpecTable,
} from "./types";

export const touringBoardFixture: BoardCard = {
  id: "aquara-atlas-12",
  brand: "Aquara",
  model: "Atlas 12'0\"",
  length_ft: 12,
  width_in: 32,
  thickness_in: 6,
  volume_l: 320,
  max_rider_weight_kg: 140,
  recommended_psi: 15,
  max_psi: 18,
  board_type: "touring",
  skill_level: "intermediate",
  fin_box: "US-box",
  valve_type: "H3",
  board_weight_kg: 9.5,
  price_usd: 899,
  best_for: ["long-distance", "flatwater"],
  image_url: "/assets/placeholders/touring.svg",
  is_mock: true,
};

export const compactTouringBoardFixture: BoardCard = {
  id: "riptide-tourer-11-6",
  brand: "Riptide",
  model: "Tourer 11'6\"",
  length_ft: 11.5,
  width_in: 30,
  thickness_in: 6,
  volume_l: 280,
  max_rider_weight_kg: 120,
  recommended_psi: 14,
  max_psi: 17,
  board_type: "touring",
  skill_level: "beginner",
  fin_box: "US-box",
  valve_type: "H3",
  board_weight_kg: 8.9,
  price_usd: 749,
  best_for: ["day trips", "flatwater"],
  image_url: "/assets/placeholders/touring.svg",
  is_mock: true,
};

export const specTableFixture: SpecTable = {
  title: "Touring boards compared",
  columns: ["Model", "Length (ft)", "Capacity (kg)", "Price (USD)"],
  rows: [
    ["Aquara Atlas 12'0\"", "12.0", "140.0", "899"],
    ["Riptide Tourer 11'6\"", "11.5", "120.0", "749"],
  ],
  board_ids: ["aquara-atlas-12", "riptide-tourer-11-6"],
};

export const compatibleResultFixture: CompatibilityResult = {
  board_id: "aquara-atlas-12",
  accessory_id: "fjord-glide-fin",
  compatible: true,
  reason: "Fin box types match (US-box).",
  caveats: [],
};

export const compatibleWithCaveatsResultFixture: CompatibilityResult = {
  board_id: "aquara-atlas-12",
  accessory_id: "zephyr-airtrek-pump",
  compatible: true,
  reason: "Pump reaches the recommended PSI for this board.",
  caveats: ["Requires the H3 valve adapter, sold separately."],
};

export const incompatibleResultFixture: CompatibilityResult = {
  board_id: "aquara-atlas-12",
  accessory_id: "cascade-river-fin",
  compatible: false,
  reason: "Fin box mismatch: board uses US-box, accessory is slide-in.",
  caveats: [],
};

export const refusedChatResponseFixture: ChatResponse = {
  answer:
    "I can only help with paddleboard boards, gear, and compatibility questions — try asking about a board, paddle, or fin instead.",
  cards: [],
  tables: [],
  compatibility: [],
  tools_used: [],
  refused: true,
  prompt_version: "v1",
};
