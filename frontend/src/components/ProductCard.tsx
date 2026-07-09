/**
 * ProductCard — renders a single `BoardCard` payload (SPEC "Frontend
 * requirements": product cards). Pure presentational component: it only
 * reads typed fields off the structured payload, never raw model text.
 */
import type { BoardCard } from "../lib/types";

/**
 * Board-type → placeholder-block color, built only from the S14 theme
 * tokens (primary/accent/coral, plus the base slate palette already used in
 * `index.css`). Unknown/future board types fall back to a neutral slate
 * tint rather than inventing a new color.
 */
const BOARD_TYPE_COLOR: Record<string, string> = {
  touring: "bg-accent/20",
  "all-around": "bg-primary/10",
  racing: "bg-coral/20",
  whitewater: "bg-primary/20",
  yoga: "bg-accent/10",
};

const DEFAULT_TYPE_COLOR = "bg-slate-100";

function boardTypeColorClass(boardType: string): string {
  return BOARD_TYPE_COLOR[boardType] ?? DEFAULT_TYPE_COLOR;
}

const priceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export interface ProductCardProps {
  board: BoardCard;
  /** "Add to compare" is a stub affordance — wiring is owned by S16/S17. */
  onAddToCompare?: (boardId: string) => void;
}

function ProductCard({ board, onAddToCompare }: ProductCardProps) {
  return (
    <article
      className="w-full max-w-sm overflow-hidden rounded-card border border-border bg-surface shadow-soft transition-shadow duration-200 hover:shadow-soft-lg"
      aria-label={`${board.brand} ${board.model}`}
    >
      <div
        className={`flex h-32 items-center justify-center ${boardTypeColorClass(board.board_type)}`}
      >
        <span className="font-heading text-sm font-medium capitalize text-slate-600/80">
          {board.board_type}
        </span>
      </div>

      <div className="space-y-3 p-4">
        <header>
          <p className="text-sm font-medium text-primary">{board.brand}</p>
          <h3 className="font-heading text-lg font-semibold text-slate-900">
            {board.model}
          </h3>
        </header>

        <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm text-slate-700 tabular-nums">
          <div className="flex justify-between gap-2">
            <dt className="text-slate-500">Length</dt>
            <dd>{board.length_ft} ft</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-slate-500">Width</dt>
            <dd>{board.width_in} in</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-slate-500">Capacity</dt>
            <dd>{board.max_rider_weight_kg} kg</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-slate-500">PSI</dt>
            <dd>
              {board.recommended_psi}&ndash;{board.max_psi}
            </dd>
          </div>
        </dl>

        <p className="font-heading text-xl font-semibold tabular-nums text-slate-900">
          {priceFormatter.format(board.price_usd)}
        </p>

        {board.best_for.length > 0 && (
          <ul className="flex flex-wrap gap-1.5" aria-label="Best for">
            {board.best_for.map((tag) => (
              <li
                key={tag}
                className="rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary"
              >
                {tag}
              </li>
            ))}
          </ul>
        )}

        <button
          type="button"
          onClick={() => onAddToCompare?.(board.id)}
          className="w-full rounded-card border border-border bg-surface px-3 py-1.5 text-sm font-medium text-primary transition-colors duration-200 hover:bg-primary-50"
        >
          Add to compare
        </button>
      </div>
    </article>
  );
}

export default ProductCard;
