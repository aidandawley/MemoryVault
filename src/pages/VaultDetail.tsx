// src/pages/VaultDetailPage.tsx
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Carousel, { type CarouselItem } from "../components/memorypage/Carousel";
import type { VaultPublic } from "../components/vault/VaultTypes";
import VaultDetailSidebar from "../components/vault/VaultDetailSidebar";
import VaultAddMediaSection from "../components/vault/VaultAddMediaSection";
import { Card } from "../components/memorypage/Card";
import type { CardPublic } from "../types/card";
import "../styles/VaultDetail.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export default function VaultDetailPage() {
  const { vaultId } = useParams();
  const [vault, setVault] = useState<VaultPublic | null>(null);
  const [items, setItems] = useState<CarouselItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [addedCards, setAddedCards] = useState<CardPublic[]>([]);

  useEffect(() => {
    if (!vaultId) return;

    const ac = new AbortController();

    async function load() {
      try {
        setLoading(true);
        setErr(null);

        const res = await fetch(`${API_URL}/api/vaults/${vaultId}`, {
          signal: ac.signal,
        });

        if (res.status === 404) {
          setErr("Vault not found");
          return;
        }

        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(text || `Request failed (${res.status})`);
        }

        const data = (await res.json()) as VaultPublic;
        setVault(data);

        const demoItems: CarouselItem[] = [
          {
            id: `${vaultId}-demo-photo-1`,
            title: data.title ?? "Untitled Vault",
            creator: "Demo User",
            type: "photo",
            thumbnailUrl: "/dog1.jpg",
            photoUrl: "/dog1.jpg",
            card: {
              media_type: "image",
              cardId: `${vaultId}-card-1`,
              media_id: "demo-media-1",
              caption: data.title ?? "Untitled Vault",
              tags: ["memory", "photo"],
              isActive: true,
            },
          },
          {
            id: `${vaultId}-demo-photo-2`,
            title: "Second memory",
            creator: "Demo User",
            type: "photo",
            thumbnailUrl: "/dog2.jpg",
            photoUrl: "/dog2.jpg",
            card: {
              media_type: "image",
              cardId: `${vaultId}-card-2`,
              media_id: "demo-media-2",
              caption: "Second memory",
              tags: ["memory", "photo"],
              isActive: true,
            },
          },
          {
            id: `${vaultId}-demo-photo-3`,
            title: "Bob’s B-Day",
            creator: "Group Vault",
            type: "photo",
            thumbnailUrl: "/dog3.jpg",
            photoUrl: "/dog3.jpg",
            card: {
              media_type: "image",
              cardId: `${vaultId}-card-3`,
              media_id: "demo-media-3",
              caption: "Bob's B-Day",
              tags: ["birthday", "bob"],
              isActive: true,
            },
          },
        ];

        setItems(demoItems);
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          setErr(e?.message ?? "Failed to load vault");
        }
      } finally {
        setLoading(false);
      }
    }

    load();
    return () => ac.abort();
  }, [vaultId]);

  if (loading) return <div className="vault-detail-loading">Loading...</div>;
  if (err) return <div className="vault-detail-error">{err}</div>;
  if (!vault || !vaultId)
    return <div className="vault-detail-error">Vault not found</div>;

  return (
    <div className="vault-detail-shell">
      <VaultDetailSidebar vault={vault} />

      <main className="vault-detail-main">
        <div className="vault-detail-container">
          <div className="vault-detail-header">
            <h1>{vault.title}</h1>
            <p>{vault.description}</p>
          </div>

          {items.length > 0 && (
            <div className="vault-detail-media">
              <Carousel items={items} initialIndex={0} radius={2} />
            </div>
          )}

          <VaultAddMediaSection
            vaultId={vaultId}
            apiBaseUrl={API_URL}
            onCreated={(card) => {
              // Add created card to a separate section beneath the carousel
              setAddedCards((prev) => [card as CardPublic, ...prev]);
            }}
          />

          {/* Section for added media (created via composer) */}
          {addedCards.length > 0 && (
            <section className="vault-detail-added">
              <h2 className="vault-detail-added__title">Recently added</h2>
              <div className="vault-detail-added__grid">
                {addedCards.map((c) => (
                  <div
                    key={(c as any).cardId ?? (c as any).card_id}
                    className="vault-detail-added__item"
                  >
                    <Card card={c} />
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
