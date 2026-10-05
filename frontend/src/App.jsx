import { useState } from "react";
import Header from "./components/Header";
import QueryForm from "./components/QueryForm";
import RecommendationCard from "./components/RecommendationCard";
import ProductCard from "./components/ProductCard";
import TrendPanel from "./components/TrendPanel";
import AgentTracePanel from "./components/AgentTracePanel";
import { requestStyling } from "./lib/api";

export default function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const selectedIds = new Set(
    result ? result.selected_items.map((item) => item.item_id) : []
  );

  async function handleSubmit() {
    setLoading(true);
    setError(null);

    try {
      const data = await requestStyling(query);
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong talking to the backend.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-12 sm:py-16">
      <div className="mx-auto max-w-4xl">
        <Header />

        <QueryForm
          query={query}
          setQuery={setQuery}
          onSubmit={handleSubmit}
          loading={loading}
        />

        {error && (
          <div className="mx-auto mt-8 max-w-2xl rounded-xl border border-[var(--color-bad)] bg-[var(--color-surface)] p-4 text-sm text-[var(--color-bad)]">
            {error}. Is the backend running at the URL set in VITE_API_URL?
          </div>
        )}

        {loading && (
          <div className="mt-12 flex flex-col items-center gap-3 text-[var(--color-text-muted)]">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
            <p className="text-sm">Planning, searching the catalog, and styling…</p>
          </div>
        )}

        {result && !loading && (
          <div className="mt-10">
            <RecommendationCard result={result} />

            <h2 className="mt-10 mb-3 text-sm font-semibold tracking-wide text-[var(--color-text-muted)] uppercase">
              Items considered
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {result.catalog_results.map((item) => (
                <ProductCard
                  key={item.item_id}
                  item={item}
                  selected={selectedIds.has(item.item_id)}
                />
              ))}
            </div>

            <TrendPanel trends={result.trend_results} />
            <AgentTracePanel result={result} />
          </div>
        )}
      </div>
    </div>
  );
}
