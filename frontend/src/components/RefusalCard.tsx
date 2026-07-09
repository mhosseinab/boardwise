/**
 * RefusalCard — the distinct rendering for a refused `ChatResponse`
 * (`refused: true`, SPEC "Frontend requirements" states & a11y). The
 * card's own framing copy is static, canned text (never markup-rendered
 * model output); `answer` is shown as plain text, exactly as the API
 * returned it.
 */
export interface RefusalCardProps {
  answer: string;
}

function RefusalCard({ answer }: RefusalCardProps) {
  return (
    <div
      role="note"
      aria-label="Off-topic request"
      className="max-w-md space-y-2 rounded-card border border-coral/30 bg-coral/5 p-4 shadow-soft"
    >
      <p className="font-heading text-sm font-semibold text-coral">
        I only cover paddleboards
      </p>
      <p className="text-sm text-slate-700">{answer}</p>
      <p className="text-xs text-slate-500">
        Ask me about boards, paddles, pumps, fins, leashes, or gear
        compatibility instead.
      </p>
    </div>
  );
}

export default RefusalCard;
