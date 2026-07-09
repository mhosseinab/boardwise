/**
 * SpecTable — renders a `SpecTable` payload as a side-by-side comparison
 * (SPEC "Frontend requirements": spec comparison tables). One row per board,
 * cells aligned to `columns` (mirrors `backend/app/schemas.py` "SpecTable.rows
 * is list[list[str]], one row per board, cells aligned to columns").
 */
import type { SpecTable as SpecTableData } from "../lib/types";

/**
 * Columns whose "winning" direction is unambiguous from the header alone:
 * lower is better for price/cost, higher is better for capacity/volume.
 * Every other column (dimensions, PSI, fin box, etc.) has no defensible
 * single "winner" and is left unhighlighted rather than guessing.
 */
const LOWER_IS_BETTER = /price|cost/i;
const HIGHER_IS_BETTER = /capacity|rider weight|volume/i;

function parseNumeric(cell: string): number | null {
  const match = /-?\d+(\.\d+)?/.exec(cell);
  return match ? Number(match[0]) : null;
}

/** Row index of the winning cell per column, or -1 if that column has no defensible winner. */
function winningRowPerColumn(table: SpecTableData): number[] {
  return table.columns.map((column, columnIndex) => {
    const direction = LOWER_IS_BETTER.test(column)
      ? "lower"
      : HIGHER_IS_BETTER.test(column)
        ? "higher"
        : null;
    if (!direction) return -1;

    const values = table.rows.map((row) => parseNumeric(row[columnIndex] ?? ""));
    if (values.some((value) => value === null)) return -1;

    const numericValues = values as number[];
    if (new Set(numericValues).size < 2) return -1;

    const target =
      direction === "lower" ? Math.min(...numericValues) : Math.max(...numericValues);
    return numericValues.indexOf(target);
  });
}

export interface SpecTableProps {
  table: SpecTableData;
}

function SpecTable({ table }: SpecTableProps) {
  const winningRows = winningRowPerColumn(table);

  return (
    <figure className="overflow-x-auto rounded-card border border-border bg-surface shadow-soft">
      <figcaption className="border-b border-border px-4 py-3 font-heading text-sm font-semibold text-slate-900">
        {table.title}
      </figcaption>
      <table className="w-full text-left text-sm tabular-nums">
        <thead>
          <tr className="border-b border-border text-slate-500">
            {table.columns.map((column) => (
              <th key={column} scope="col" className="px-4 py-2 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr
              key={table.board_ids[rowIndex] ?? rowIndex}
              className="border-b border-border last:border-0"
            >
              {row.map((cell, columnIndex) => (
                <td
                  key={`${table.board_ids[rowIndex] ?? rowIndex}-${columnIndex}`}
                  className={
                    winningRows[columnIndex] === rowIndex
                      ? "bg-primary-50 px-4 py-2 font-semibold text-primary"
                      : "px-4 py-2 text-slate-700"
                  }
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

export default SpecTable;
