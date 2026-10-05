export default function AgentTracePanel({ result }) {
  return (
    <details className="mt-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
      <summary className="cursor-pointer text-sm font-medium text-[var(--color-text-muted)]">
        How the agent got there
      </summary>

      <div className="mt-3 space-y-1.5 text-sm text-[var(--color-text-muted)]">
        <p>
          <span className="font-medium text-[var(--color-text)]">Raw request:</span>{" "}
          {result.query}
        </p>
        <p>
          <span className="font-medium text-[var(--color-text)]">Search query used:</span>{" "}
          {result.search_query}
        </p>
        <p>
          <span className="font-medium text-[var(--color-text)]">Self-critique notes:</span>{" "}
          {result.critique}
        </p>
      </div>
    </details>
  );
}
