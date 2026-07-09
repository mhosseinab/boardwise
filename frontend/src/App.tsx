// Minimal shell for S14. The chat pane, catalog panel, and structured
// renderers are wired in here by S15-S17; this step only proves the app
// boots, builds, and is styled with the visual-identity tokens.
function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-surface/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-4">
          <span
            className="inline-block h-6 w-6 rounded-full bg-primary"
            aria-hidden="true"
          />
          <h1 className="font-heading text-xl font-semibold text-primary">
            BoardWise
          </h1>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10" />
    </div>
  );
}

export default App;
