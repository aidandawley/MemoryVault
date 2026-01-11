// src/pages/VaultDetailPage.tsx
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import Carousel, { type CarouselItem } from "../components/memorypage/Carousel";
import type { VaultPublic } from "../components/vault/VaultTypes";
import VaultDetailSidebar from "../components/vault/VaultDetailSidebar";
import VaultAddMediaSection from "../components/vault/VaultAddMediaSection";
import { Card } from "../components/memorypage/Card";
import type { CardPublic } from "../types/card";
import CategoryLine from "../components/CategoryLine";
import "../styles/VaultDetail.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export type MediaAnalysisResult =
  | { kind: "image"; tags: string[] }
  | { kind: "video"; video_id: string; hashtags: string[] };

// ✅ Fix for TS: CategoryLine expects item.type to be "video" | "photo"
type CategoryLineItem = {
  id: string;
  title: string;
  type: "video" | "photo";
  thumbnailUrl: string;
  photoUrl?: string;
  videoUrl?: string;
  card: CardPublic;
};

export default function VaultDetailPage() {
  const { vaultId } = useParams();
  const [vault, setVault] = useState<VaultPublic | null>(null);
  const [items, setItems] = useState<CarouselItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [addedCards, setAddedCards] = useState<CardPublic[]>([]);

  // ✅ Single function: decides which backend endpoint to call based on file type
  const analyzeMediaFile = async (file: File): Promise<MediaAnalysisResult> => {
    const isVideo = file.type.startsWith("video/");
    const isImage = file.type.startsWith("image/");

    if (!isVideo && !isImage) {
      throw new Error(`Unsupported file type: ${file.type || "unknown"}`);
    }

    const endpoint = isVideo
      ? `${API_URL}/api/media/upload-video-hashtags`
      : `${API_URL}/api/media/upload-photo-tags`;

    const form = new FormData();
    form.append("file", file); // must match FastAPI param name

    const res = await fetch(endpoint, {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `Media analysis failed (${res.status})`);
    }

    const data = await res.json();

    if (isVideo) {
      return {
        kind: "video",
        video_id: data?.video_id,
        hashtags: Array.isArray(data?.hashtags) ? data.hashtags : [],
      };
    }

    return {
      kind: "image",
      tags: Array.isArray(data?.tags) ? data.tags : [],
    };
  };

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

        // Fetch actual cards from the database
        const cardsRes = await fetch(`${API_URL}/api/vaults/${vaultId}/cards`, {
          signal: ac.signal,
        });

        if (cardsRes.ok) {
          const cards = (await cardsRes.json()) as CardPublic[];

          const carouselItems: CarouselItem[] = cards.map((card) => {
            const mediaId = (card as any).media_id ?? (card as any).mediaId;
            const mediaType =
              (card as any).media_type ?? (card as any).mediaType;
            const cardId = (card as any).cardId ?? (card as any).card_id;
            const caption = (card as any).caption ?? "Untitled";

            return {
              id: cardId,
              title: caption,
              creator: "",
              type: mediaType === "video" ? "video" : "photo",
              thumbnailUrl: `${API_URL}/media/${mediaId}`,
              photoUrl:
                mediaType === "video" ? undefined : `${API_URL}/media/${mediaId}`,
              videoUrl:
                mediaType === "video" ? `${API_URL}/media/${mediaId}` : undefined,
              card: card,
            };
          });

          setItems(carouselItems);
        } else {
          setItems([]);
        }
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

  const vaultCards = useMemo(() => {
    const fromCarousel = items
      .map((i) => i.card)
      .filter(Boolean) as CardPublic[];

    const seen = new Set<string>();
    const out: CardPublic[] = [];

    for (const c of [...addedCards, ...fromCarousel]) {
      const id = (c as any).cardId ?? (c as any).card_id;
      if (!id) continue;
      if (seen.has(id)) continue;
      seen.add(id);
      out.push(c);
    }

    return out;
  }, [items, addedCards]);

  const cardsByTag = useMemo(() => {
    const map = new Map<string, CardPublic[]>();

    for (const card of vaultCards) {
      const tags = Array.isArray((card as any).tags) ? (card as any).tags : [];
      for (const t of tags) {
        const tag = String(t).trim().toLowerCase();
        if (!tag) continue;

        if (!map.has(tag)) map.set(tag, []);
        map.get(tag)!.push(card);
      }
    }

    // Deduplicate cards per tag
    for (const [tag, list] of map) {
      const seen = new Set<string>();
      map.set(
        tag,
        list.filter((c) => {
          const id = (c as any).cardId ?? (c as any).card_id;
          if (!id) return false;
          if (seen.has(id)) return false;
          seen.add(id);
          return true;
        })
      );
    }

    return map;
  }, [vaultCards]);

  const sortedTags = useMemo(() => {
    return Array.from(cardsByTag.entries())
      .sort((a, b) => b[1].length - a[1].length)
      .map(([tag]) => tag);
  }, [cardsByTag]);

  // ✅ Fix: explicitly return CategoryLineItem[] and force union type for item.type
  const toLineItems = (tag: string): CategoryLineItem[] => {
    const list = cardsByTag.get(tag) ?? [];

    return list
      .map((c) => {
        const cardId = (c as any).cardId ?? (c as any).card_id;
        const mediaId = (c as any).media_id ?? (c as any).mediaId;
        const mediaType =
          (c as any).media_type ?? (c as any).mediaType;

        const matchingItem = items.find(
          (it) =>
            it.card &&
            ((it.card as any).cardId ?? (it.card as any).card_id) === cardId
        );

        const fallbackSrc = `${API_URL}/media/${mediaId}`;

        const photoUrl =
          matchingItem?.photoUrl ?? matchingItem?.thumbnailUrl ?? fallbackSrc;

        const videoUrl =
          matchingItem?.videoUrl ?? matchingItem?.thumbnailUrl ?? fallbackSrc;

        const type: "video" | "photo" =
          mediaType === "video" ? "video" : "photo";

        return {
          id: `${tag}-${cardId}`,
          title: (c as any).caption ?? "Untitled",
          type,
          thumbnailUrl: matchingItem?.thumbnailUrl ?? photoUrl,
          photoUrl: type === "video" ? undefined : photoUrl,
          videoUrl: type === "video" ? videoUrl : undefined,
          card: c,
        };
      })
      .filter(Boolean);
  };

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

          {sortedTags.length > 0 && (
            <section className="vault-detail-tags">
              <h2 className="vault-detail-added__title">Browse by tag</h2>

              <div className="vault-detail-tagRows">
                {sortedTags.map((tag) => (
                  <div key={tag} className="vault-detail-tagRow">
                    <CategoryLine title={`#${tag}`} items={toLineItems(tag)} />
                  </div>
                ))}
              </div>
            </section>
          )}

          <VaultAddMediaSection
            vaultId={vaultId}
            apiBaseUrl={API_URL}
            analyzeMediaFile={analyzeMediaFile}
            onCreated={(card) => {
              setAddedCards((prev) => [card as CardPublic, ...prev]);
            }}
          />

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