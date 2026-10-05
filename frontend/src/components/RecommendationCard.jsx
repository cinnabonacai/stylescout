import { getCategoryIcon } from "../lib/categoryIcons";

function BudgetBadge({ totalCost, budget, fitsBudget }) {
  if (budget == null) {
    return (
      <span className="rounded-full border border-[var(--color-border)] px-3 py-1 text-xs font-medium text-[var(--color-text-muted)]">
        Total: ${totalCost.toFixed(2)}
      </span>
    );
  }

  const color = fitsBudget ? "var(--color-good)" : "var(--color-bad)";

  return (
    <span
      className="rounded-full border px-3 py-1 text-xs font-medium"
      style={{ borderColor: color, color }}
    >
      Total: ${totalCost.toFixed(2)} / ${budget} budget
    </span>
  );
}

export default function RecommendationCard({ result }) {
  const isMock = result.styling_notes.startsWith("[MOCK MODE]");
  const isFallback = result.styling_notes.startsWith("[FALLBACK]");
  const approved = result.critique === "No issues found.";

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-8">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="rounded-full bg-[var(--color-brand-soft)] px-3 py-1 text-xs font-medium tracking-wide uppercase"
          style={{ color: "var(--color-accent)" }}
        >
          Your Outfit
        </span>

        <BudgetBadge
          totalCost={result.total_cost}
          budget={result.budget}
          fitsBudget={result.fits_budget}
        />

        <span
          className="ml-auto flex items-center gap-1.5 text-xs font-medium"
          style={{ color: approved ? "var(--color-good)" : "var(--color-bad)" }}
        >
          <span
            className="inline-block h-1.5 w-1.5 rounded-full"
            style={{ background: approved ? "var(--color-good)" : "var(--color-bad)" }}
          />
          {approved ? "Self-check passed" : "Self-check flagged a revision"}
        </span>
      </div>

      <ul className="mt-5 divide-y divide-[var(--color-border)] border-y border-[var(--color-border)]">
        {result.selected_items.map((item) => (
          <li key={item.item_id} className="flex items-center gap-3 py-3">
            <span className="text-xl" aria-hidden="true">
              {getCategoryIcon(item.category)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{item.name}</p>
              <p className="text-xs text-[var(--color-text-muted)] capitalize">
                {item.color} · {item.brand}
              </p>
            </div>
            <span className="font-semibold whitespace-nowrap">
              ${item.price.toFixed(2)}
            </span>
          </li>
        ))}
      </ul>

      <p
        className="mt-5 text-lg leading-relaxed text-[var(--color-text)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {result.styling_notes}
      </p>

      {isMock && (
        <p className="mt-4 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-xs text-[var(--color-text-muted)]">
          No GROQ_API_KEY or ANTHROPIC_API_KEY is set on the backend, so
          this is a placeholder pick, not a real styling rationale. Set a
          key to see real output.
        </p>
      )}

      {isFallback && (
        <p className="mt-4 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3 text-xs text-[var(--color-text-muted)]">
          Your API key is set and working, but the model's last response
          couldn't be parsed, so this is a placeholder pick rather than a
          real styling rationale. Usually transient &mdash; try the same
          request again.
        </p>
      )}
    </div>
  );
}
