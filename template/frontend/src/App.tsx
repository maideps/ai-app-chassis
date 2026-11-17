import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, api, type Health, type Summary, type Usage } from "./api";

function describe(error: unknown): string {
  if (error instanceof ApiError && error.rule) return `Rejected by the ${error.rule} guardrail: ${error.message}`;
  if (error instanceof ApiError) return error.message;
  return "The backend is not reachable. Is it running on port 8000?";
}

export function App() {
  const [text, setText] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);

  const refreshUsage = useCallback(() => {
    api.usage().then(setUsage, () => setUsage(null));
  }, []);

  useEffect(() => {
    api.health().then(setHealth, () => setHealth(null));
    refreshUsage();
  }, [refreshUsage]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setSummary(await api.summarize(text));
    } catch (err) {
      setSummary(null);
      setError(describe(err));
    } finally {
      setBusy(false);
      refreshUsage();
    }
  }

  const total = usage?.total;
  return (
    <main>
      <header>
        <h1>Summarize</h1>
        <p className="model">{health ? `Model: ${health.model}` : "Backend offline"}</p>
      </header>

      <form onSubmit={onSubmit}>
        <label htmlFor="text">Text to summarize</label>
        <textarea id="text" rows={8} value={text} onChange={(event) => setText(event.target.value)} />
        <button type="submit" disabled={busy || !text.trim()}>
          {busy ? "Summarizing…" : "Summarize"}
        </button>
      </form>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {summary && (
        <section aria-label="Result">
          <h2>Summary</h2>
          <p>{summary.summary}</p>
          <ul className="keywords" aria-label="Keywords">
            {summary.keywords.map((keyword) => (
              <li key={keyword}>{keyword}</li>
            ))}
          </ul>
        </section>
      )}

      <section aria-label="Usage" className="usage">
        <h2>Usage since the backend started</h2>
        {total ? (
          <dl>
            <dt>Calls</dt>
            <dd>{total.calls}</dd>
            <dt>Failed</dt>
            <dd>{total.failed}</dd>
            <dt>Tokens in / out</dt>
            <dd>
              {total.input_tokens} / {total.output_tokens}
            </dd>
            <dt>Cost</dt>
            <dd>${total.cost_usd.toFixed(4)}</dd>
            <dt>Latency p95</dt>
            <dd>{total.latency_ms_p95} ms</dd>
          </dl>
        ) : (
          <p>No usage data.</p>
        )}
      </section>
    </main>
  );
}
