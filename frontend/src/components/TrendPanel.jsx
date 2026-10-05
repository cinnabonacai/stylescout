export default function TrendPanel({ trends }) {
  if (!trends.length) return null;

  return (
    <div className="mt-8">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-[var(--color-text-muted)] uppercase">
        Matched trend notes
      </h2>

      <div className="flex flex-col gap-2">
        {trends.map((t) => (
          <div
            key={t.trend_id}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm"
          >
            <span className="mr-2 font-mono text-xs text-[var(--color-brand)]">
              {t.trend_id}
            </span>
            <span className="text-[var(--color-text-muted)]">{t.excerpt}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
