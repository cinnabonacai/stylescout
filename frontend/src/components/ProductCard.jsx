import { getCategoryIcon } from "../lib/categoryIcons";

export default function ProductCard({ item, selected = false }) {
  const relevancePercent = Math.min(100, Math.round(item.relevance * 100 * 3));

  return (
    <div
      className="relative flex flex-col rounded-xl border bg-[var(--color-surface)] p-4"
      style={{
        borderColor: selected ? "var(--color-accent)" : "var(--color-border)",
        borderWidth: selected ? "2px" : "1px",
      }}
    >
      {selected && (
        <span
          className="absolute -top-2.5 right-3 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide text-[var(--color-bg)] uppercase"
          style={{ background: "var(--color-accent)" }}
        >
          Selected
        </span>
      )}

      <div className="flex items-start justify-between">
        <span className="text-2xl" aria-hidden="true">
          {getCategoryIcon(item.category)}
        </span>
        <span className="rounded-full bg-[var(--color-brand-soft)] px-2 py-0.5 text-xs font-medium text-[var(--color-brand)]">
          {item.brand}
        </span>
      </div>

      <h3 className="mt-3 font-semibold leading-snug">{item.name}</h3>
      <p className="mt-0.5 text-sm text-[var(--color-text-muted)] capitalize">
        {item.color} · {item.category}
      </p>

      <div className="mt-2 flex flex-wrap gap-1">
        {item.style_tags.split(",").map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[11px] text-[var(--color-text-muted)]"
          >
            {tag}
          </span>
        ))}
      </div>

      <div className="mt-auto flex items-center justify-between pt-4">
        <span className="font-semibold">${item.price.toFixed(2)}</span>

        <div className="flex items-center gap-1.5" title={`Relevance score: ${item.relevance}`}>
          <div className="h-1.5 w-12 overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
            <div
              className="h-full rounded-full bg-[var(--color-brand)]"
              style={{ width: `${relevancePercent}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
