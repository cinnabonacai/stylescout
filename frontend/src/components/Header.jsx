export default function Header() {
  return (
    <header className="mb-10 text-center">
      <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-1.5 text-xs font-medium tracking-wide text-[var(--color-text-muted)] uppercase">
        Agentic styling assistant
      </div>

      <h1
        className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Style<span className="text-[var(--color-accent)]">Scout</span>
      </h1>

      <p className="mx-auto mt-3 max-w-xl text-[var(--color-text-muted)]">
        Tell it an occasion, a vibe, or a budget. It searches a product
        catalog and current trend notes, then builds an outfit it can
        actually justify, item by item.
      </p>
    </header>
  );
}
