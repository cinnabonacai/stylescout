const EXAMPLES = [
  "a cozy preppy outfit for fall under $150",
  "something edgy for a night out",
  "elevated office look, minimalist",
  "budget capsule wardrobe under $200",
];

export default function QueryForm({ query, setQuery, onSubmit, loading }) {
  function handleSubmit(e) {
    e.preventDefault();
    if (query.trim() && !loading) {
      onSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl">
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What are you dressing for?"
          className="flex-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-base outline-none placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)]"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="rounded-xl bg-[var(--color-accent)] px-6 py-3 font-semibold text-white transition hover:bg-[var(--color-accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Styling…" : "Style me"}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => setQuery(example)}
            className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-1 text-xs text-[var(--color-text-muted)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-text)]"
          >
            {example}
          </button>
        ))}
      </div>
    </form>
  );
}
