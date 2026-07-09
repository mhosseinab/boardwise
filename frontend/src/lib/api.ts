/**
 * Typed fetch client for the BoardWise API.
 *
 * All requests use relative `/api/...` paths (decision §4.11): the Vite dev
 * server proxies `/api` to `http://localhost:8006` (see vite.config.ts), and
 * in production the nginx-served bundle proxies `/api` to the `api`
 * container. No absolute base URL is ever hardcoded here.
 */
import type { BoardCard, ChatRequest, ChatResponse } from "./types";

/** Query filters accepted by `GET /api/boards` (mirrors `backend/app/main.py`). */
export interface BoardFilters {
  board_type?: string;
  skill_level?: string;
  min_capacity_kg?: number;
  max_price_usd?: number;
  min_length_ft?: number;
  max_length_ft?: number;
  limit?: number;
  offset?: number;
}

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new ApiError(
      `${init?.method ?? "GET"} ${path} failed: ${response.status} ${detail}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

/** `POST /api/chat` — send a chat message, get back the structured payload. */
export function postChat(body: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** `GET /api/boards` — the browsable catalog, filtered/paginated server-side. */
export function getBoards(filters: BoardFilters = {}): Promise<BoardCard[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined) {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return request<BoardCard[]>(`/api/boards${query ? `?${query}` : ""}`);
}

/** `GET /api/boards/:id` — a single board's full spec row. */
export function getBoard(boardId: string): Promise<BoardCard> {
  return request<BoardCard>(`/api/boards/${encodeURIComponent(boardId)}`);
}
