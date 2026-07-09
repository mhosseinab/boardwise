/**
 * CompatBadge — renders a `CompatibilityResult` payload as a green/red/amber
 * pill (SPEC "Frontend requirements": compatibility badges).
 *
 * The wire contract only carries `compatible: boolean` + `caveats: string[]`
 * (no separate three-way verdict field), so the three-way mapping is derived
 * here: incompatible -> red, compatible with caveats -> amber, compatible
 * with no caveats -> green.
 */
import type { CompatibilityResult } from "../lib/types";

type Verdict = "compatible" | "caveats" | "incompatible";

const VERDICT_LABEL: Record<Verdict, string> = {
  compatible: "Compatible",
  caveats: "Compatible with caveats",
  incompatible: "Incompatible",
};

const VERDICT_CLASS: Record<Verdict, string> = {
  compatible: "bg-compat-green/10 text-compat-green",
  caveats: "bg-compat-amber/10 text-compat-amber",
  incompatible: "bg-compat-red/10 text-compat-red",
};

function verdictFor(result: CompatibilityResult): Verdict {
  if (!result.compatible) return "incompatible";
  return result.caveats.length > 0 ? "caveats" : "compatible";
}

export interface CompatBadgeProps {
  result: CompatibilityResult;
}

function CompatBadge({ result }: CompatBadgeProps) {
  const verdict = verdictFor(result);

  return (
    <div className="max-w-sm space-y-1.5 rounded-card border border-border bg-surface p-3 shadow-soft">
      <span
        role="status"
        aria-label={VERDICT_LABEL[verdict]}
        data-verdict={verdict}
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${VERDICT_CLASS[verdict]}`}
      >
        {VERDICT_LABEL[verdict]}
      </span>
      <p className="text-sm text-slate-700">{result.reason}</p>
      {result.caveats.length > 0 && (
        <ul className="list-inside list-disc text-xs text-slate-500">
          {result.caveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default CompatBadge;
