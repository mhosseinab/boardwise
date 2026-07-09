/**
 * ExamplePrompts — 4-6 chips shown above the empty thread (SPEC "Frontend
 * requirements"). Each chip submits its prompt text on click; the set
 * exercises search/budget, board comparison, compatibility, a missing-spec
 * question, and an off-topic question (refusal).
 */
const PROMPTS: readonly string[] = [
  "I'm a beginner with a budget under $900 — what board should I get?",
  "Compare the Aquara Atlas 12'0\" and Riptide Tourer 11'6\".",
  "Is the Fjord Glide Fin compatible with the Aquara Atlas 12'0\"?",
  "What's the warranty on the Aquara Atlas 12'0\"?",
  "What's the best pizza topping?",
];

export interface ExamplePromptsProps {
  onSelect: (prompt: string) => void;
}

function ExamplePrompts({ onSelect }: ExamplePromptsProps) {
  return (
    <div className="space-y-3 py-8 text-center">
      <p className="font-heading text-lg font-semibold text-slate-900">
        Ask BoardWise about boards, gear, and compatibility
      </p>
      <ul aria-label="Example prompts" className="flex flex-wrap justify-center gap-2">
        {PROMPTS.map((prompt) => (
          <li key={prompt}>
            <button
              type="button"
              onClick={() => onSelect(prompt)}
              className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm text-primary shadow-soft transition-colors duration-200 hover:bg-primary-50"
            >
              {prompt}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ExamplePrompts;
