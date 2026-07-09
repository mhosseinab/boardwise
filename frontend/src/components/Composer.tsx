/**
 * Composer — the chat input (SPEC "Frontend requirements": composer has a
 * coral Send button and a rider-profile quick-fill). The quick-fill never
 * submits on its own; it only templates a sentence into the message text
 * box, which the rider can edit before sending.
 */
import { useId, useState, type KeyboardEvent } from "react";

export interface ComposerProps {
  onSubmit: (message: string) => void;
  /** True while a request is in flight — disables input to serialize submits. */
  disabled?: boolean;
}

const SKILL_LEVELS = ["beginner", "intermediate", "advanced"];
const USE_CASES = ["touring", "all-around", "yoga", "whitewater", "racing"];

function Composer({ onSubmit, disabled = false }: ComposerProps) {
  const [message, setMessage] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [skill, setSkill] = useState("");
  const [use, setUse] = useState("");
  const messageId = useId();

  function applyRiderProfile() {
    const parts: string[] = [];
    if (weightKg) parts.push(`${weightKg}kg`);
    if (heightCm) parts.push(`${heightCm}cm tall`);
    if (skill) parts.push(`${skill} skill level`);
    if (use) parts.push(`looking for ${use} use`);
    if (parts.length === 0) return;

    const template = `I'm a rider: ${parts.join(", ")}. `;
    setMessage((previous) => `${template}${previous}`);
  }

  function submit() {
    if (disabled) return;
    const trimmed = message.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setMessage("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="space-y-3 rounded-card border border-border bg-surface p-4 shadow-soft">
      <fieldset
        aria-label="Rider profile quick-fill"
        className="flex flex-wrap items-end gap-2"
      >
        <legend className="mb-1 w-full text-xs font-medium text-slate-500">
          Rider profile quick-fill
        </legend>
        <label className="flex flex-col text-xs text-slate-500">
          Weight (kg)
          <input
            type="number"
            aria-label="Weight (kg)"
            value={weightKg}
            onChange={(event) => setWeightKg(event.target.value)}
            disabled={disabled}
            className="w-20 rounded-card border border-border px-2 py-1 text-sm text-slate-800"
          />
        </label>
        <label className="flex flex-col text-xs text-slate-500">
          Height (cm)
          <input
            type="number"
            aria-label="Height (cm)"
            value={heightCm}
            onChange={(event) => setHeightCm(event.target.value)}
            disabled={disabled}
            className="w-20 rounded-card border border-border px-2 py-1 text-sm text-slate-800"
          />
        </label>
        <label className="flex flex-col text-xs text-slate-500">
          Skill level
          <select
            aria-label="Skill level"
            value={skill}
            onChange={(event) => setSkill(event.target.value)}
            disabled={disabled}
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
          Intended use
          <select
            aria-label="Intended use"
            value={use}
            onChange={(event) => setUse(event.target.value)}
            disabled={disabled}
            className="rounded-card border border-border px-2 py-1 text-sm text-slate-800"
          >
            <option value="">Any</option>
            {USE_CASES.map((useCase) => (
              <option key={useCase} value={useCase}>
                {useCase}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={applyRiderProfile}
          disabled={disabled}
          className="rounded-card border border-border bg-surface px-3 py-1.5 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary-50"
        >
          Add my profile
        </button>
      </fieldset>

      <div className="flex items-end gap-2">
        <label htmlFor={messageId} className="sr-only">
          Message
        </label>
        <textarea
          id={messageId}
          aria-label="Message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={2}
          placeholder="Ask about boards, gear, or compatibility…"
          className="flex-1 resize-none rounded-card border border-border px-3 py-2 text-sm text-slate-800 focus:border-primary focus:outline-none"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || message.trim().length === 0}
          className="rounded-card bg-coral px-4 py-2 text-sm font-semibold text-white shadow-soft transition-colors duration-200 hover:bg-coral/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default Composer;
