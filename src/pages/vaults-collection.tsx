import React, { useEffect, useMemo, useState } from "react";
import "../styles/VaultCollection.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

type VaultPublic = {
  vaultId: string;
  ownerId: string;
  title: string;
  description?: string | null;
};

type Props = {
  userName: string;
  onOpenVault?: (vaultId: string) => void;
};

function hashToIndex(s: string, mod: number) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h % mod;
}

const VAULT_COLORS = [
  "vaultColor-0",
  "vaultColor-1",
  "vaultColor-2",
  "vaultColor-3",
  "vaultColor-4",
  "vaultColor-5",
  "vaultColor-6",
  "vaultColor-7",
];

export default function VaultCollectionPage({ userName, onOpenVault }: Props) {
  const [vaults, setVaults] = useState<VaultPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const ac = new AbortController();

    async function load() {
      try {
        setLoading(true);
        setErr(null);
        const res = await fetch(`${API_URL}/api/vaults`, {
          method: "GET",
          signal: ac.signal,
          headers: { "Content-Type": "application/json" },
        });

        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(text || `Request failed (${res.status})`);
        }

        const data = (await res.json()) as VaultPublic[];
        setVaults(Array.isArray(data) ? data : []);
      } catch (e: any) {
        if (e?.name !== "AbortError")
          setErr(e?.message ?? "Failed to load vaults");
      } finally {
        setLoading(false);
      }
    }

    load();
    return () => ac.abort();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return vaults;
    return vaults.filter((v) => {
      const t = (v.title ?? "").toLowerCase();
      const d = (v.description ?? "").toLowerCase();
      return t.includes(q) || d.includes(q);
    });
  }, [vaults, query]);

  return (
    <div className="vaultPage">
      <header className="vaultTopBar">
        <div className="vaultTopLeft">
          <div className="vaultTitle">{userName}&apos;s vaults</div>
          <div className="vaultSubtitle">
            {loading ? "Loading…" : `${vaults.length} total`}
          </div>
        </div>

        <div className="vaultTopRight">
          <div className="vaultSearchWrap">
            <input
              className="vaultSearch"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search vaults"
              aria-label="Search vaults"
            />
          </div>
        </div>
      </header>

      <main className="vaultContent">
        {err && (
          <div className="vaultBanner vaultBannerError">
            <div className="vaultBannerTitle">Couldn’t load vaults</div>
            <div className="vaultBannerText">{err}</div>
            <button
              className="vaultButton"
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
          </div>
        )}

        {!err && loading && (
          <div className="vaultGrid">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="vaultCard vaultCardSkeleton">
                <div className="vaultCardCover" />
                <div className="vaultCardMeta">
                  <div className="vaultSkLine vaultSkLine1" />
                  <div className="vaultSkLine vaultSkLine2" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!err && !loading && filtered.length === 0 && (
          <div className="vaultEmpty">
            <div className="vaultEmptyTitle">No vaults found</div>
            <div className="vaultEmptyText">
              {query.trim()
                ? "Try a different search."
                : "Create your first vault to get started."}
            </div>
          </div>
        )}

        {!err && !loading && filtered.length > 0 && (
          <div className="vaultGrid">
            {filtered.map((v) => {
              const colorClass =
                VAULT_COLORS[hashToIndex(v.vaultId, VAULT_COLORS.length)];
              return (
                <button
                  key={v.vaultId}
                  className="vaultCard"
                  onClick={() => onOpenVault?.(v.vaultId)}
                  type="button"
                >
                  <div className={`vaultCardCover ${colorClass}`}>
                    <div className="vaultCoverMark" />
                  </div>

                  <div className="vaultCardMeta">
                    <div className="vaultCardTitle" title={v.title}>
                      {v.title}
                    </div>
                    <div className="vaultCardDesc" title={v.description ?? ""}>
                      {v.description ?? "—"}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
