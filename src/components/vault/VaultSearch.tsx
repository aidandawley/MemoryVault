import { useEffect, useState } from "react";
import { Card } from "../memorypage/Card";
import type { CardPublic } from "../../types/card";
import "../../styles/VaultSearch.css";

type SearchResult = CardPublic & {
  score: number;
  matched: { kind: "caption" | "tag"; text: string };
};

type SearchResponse = {
  query: string;
  results: SearchResult[];
  timings_ms: Record<string, number>;
};

type Props = {
  vaultId: string;
  apiBaseUrl: string;
  limit?: number;
};

/** Semantic search inside one vault: "beer" finds media tagged "drinks". */
export default function VaultSearch({ vaultId, apiBaseUrl, limit = 5 }: Props) {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setData(null);
      setErr(null);
      setLoading(false);
      return;
    }

    const ac = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setErr(null);
      try {
        const params = new URLSearchParams({ q, limit: String(limit) });
        const res = await fetch(
          `${apiBaseUrl}/api/vaults/${vaultId}/search?${params}`,
          { signal: ac.signal }
        );
        if (!res.ok) throw new Error(`Search failed (${res.status})`);
        setData((await res.json()) as SearchResponse);
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setErr((e as Error).message || "Search failed");
        }
      } finally {
        if (!ac.signal.aborted) setLoading(false);
      }
    }, 300);

    return () => {
      window.clearTimeout(timer);
      ac.abort();
    };
  }, [query, vaultId, apiBaseUrl, limit]);

  const showEmpty = !!data && !loading && data.results.length === 0;

  return (
    <section className="vault-search" aria-label="Search this vault">
      <label className="vault-search__label" htmlFor="vault-search-input">
        Search this vault
      </label>
      <div className="vault-search__bar">
        <span className="vault-search__icon" aria-hidden="true">⌕</span>
        <input
          id="vault-search-input"
          className="vault-search__input"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try "beer", "golden hour" or "best friends"'
          autoComplete="off"
        />
        {loading && <span className="vault-search__status">Searching…</span>}
      </div>

      {err && <div className="vault-search__error">{err}</div>}
      {showEmpty && <div className="vault-search__empty">No matches.</div>}

      {data && data.results.length > 0 && (
        <div className="vault-search__results">
          {data.results.map((r) => (
            <div key={r.cardId} className="vault-search__item">
              <Card card={r} />
              <div className="vault-search__why">
                matched {r.matched.kind === "tag" ? `#${r.matched.text}` : `“${r.matched.text}”`}
                <span className="vault-search__score">{r.score.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
