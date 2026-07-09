/**
 * MockDataBanner — the persistent mock-data notice (SPEC "Frontend
 * requirements": mock-data notice). Rule: the disclaimer is a hard legal
 * constraint — it is always visible and offers no way to dismiss/close it.
 */
function MockDataBanner() {
  return (
    <footer
      role="contentinfo"
      className="border-t border-border bg-sand px-6 py-2 text-center text-xs text-slate-500"
    >
      Specs are mock data for demonstration.
    </footer>
  );
}

export default MockDataBanner;
