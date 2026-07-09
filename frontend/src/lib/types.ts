/**
 * Hand-mirrored TypeScript twins of `backend/app/schemas.py` (rule §4.8).
 *
 * `backend/app/schemas.py` is the FROZEN wire contract (frozen at S4); this
 * file is frozen alongside it after S14. Any future schema change must touch
 * BOTH files in the same commit (none is currently planned). Field names and
 * types below are a literal, field-for-field mirror of the Pydantic models —
 * do not reinterpret or "improve" the shape here.
 */

/** Mirrors `BoardCard` (schemas.py). */
export interface BoardCard {
  id: string;
  brand: string;
  model: string;
  length_ft: number;
  width_in: number;
  thickness_in: number;
  volume_l: number;
  max_rider_weight_kg: number;
  recommended_psi: number;
  max_psi: number;
  board_type: string;
  skill_level: string;
  fin_box: string;
  valve_type: string;
  board_weight_kg: number;
  price_usd: number;
  best_for: string[];
  image_url: string;
  is_mock: boolean;
}

/** Mirrors `SpecTable` (schemas.py). */
export interface SpecTable {
  title: string;
  columns: string[];
  rows: string[][];
  board_ids: string[];
}

/** Mirrors `CompatibilityResult` (schemas.py). */
export interface CompatibilityResult {
  board_id: string;
  accessory_id: string;
  compatible: boolean;
  reason: string;
  caveats: string[];
}

/** Mirrors `ToolCall` (schemas.py). */
export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result_summary: string;
  latency_ms: number;
}

/** Mirrors `ChatRequest` (schemas.py). */
export interface ChatRequest {
  message: string;
  history?: unknown[] | null;
}

/** Mirrors `ChatResponse` (schemas.py). */
export interface ChatResponse {
  answer: string;
  cards: BoardCard[];
  tables: SpecTable[];
  compatibility: CompatibilityResult[];
  tools_used: ToolCall[];
  refused: boolean;
  prompt_version: string;
}
