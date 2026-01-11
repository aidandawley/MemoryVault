// VaultCollectionPage.tsx
import React, { useEffect, useMemo, useState } from "react";
import "../styles/VaultCollection.css";
import type { VaultPublic } from "../components/vault/VaultTypes";
import { VaultTopBar } from "../components/vault/VaultTopBar";
import { VaultErrorBanner } from "../components/vault/VaultErrorBanner";
import { VaultEmptyState } from "../components/vault/VaultEmptyState";
import { VaultGrid } from "../components/vault/VaultGrid";
import { VaultGridSkeleton } from "../components/vault/VaultGridSkeleton";
import { useNavigate } from "react-router-dom";
import CreateVaultButton from "../components/vault/CreateVaultButton";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

type Props = {
  userName: string;
  onOpenVault?: (vaultId: string) => void;
};

export default function VaultCollectionPage({ userName, onOpenVault }: Props) {
  const [vaults, setVaults] = useState<VaultPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const navigate = useNavigate();

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

  function handleOpenVault(vaultId: string) {
    onOpenVault?.(vaultId);
    navigate(`/vaults/${vaultId}`);
  }

  return (
    <div className="vaultPage">
      <VaultTopBar
        userName={userName}
        loading={loading}
        totalCount={vaults.length}
        query={query}
        setQuery={setQuery}
      />

      <CreateVaultButton />
      <main className="vaultContent">
        {err && (
          <VaultErrorBanner
            message={err}
            onReload={() => window.location.reload()}
          />
        )}

        {!err && loading && <VaultGridSkeleton />}

        {!err && !loading && filtered.length === 0 && (
          <VaultEmptyState hasQuery={!!query.trim()} />
        )}

        {!err && !loading && filtered.length > 0 && (
          <VaultGrid vaults={filtered} onOpenVault={handleOpenVault} />
        )}
      </main>
    </div>
  );
}
