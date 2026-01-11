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

type CategoryLineItem = {
  id: string;
  title: string;
  type: "video" | "photo";
  thumbnailUrl: string;
  photoUrl?: string;
  videoUrl?: string;
  card: CardPublic;
};

const VIDEO_THUMB_PLACEHOLDER = "/video-thumb-placeholder.png";

function getCardId(c: any): string | undefined {
  return c?.cardId ?? c?.card_id;
}

function getMediaType(c: any): "video" | "image" | undefined {
  const mt = c?.media_type ?? c?.mediaType;
  if (mt === "video") return "video";
  if (mt === "image") return "image";
  return undefined;
}

function getMediaId(c: any): string | undefined {
  return c?.media_id ?? c?.mediaId;
}

function getThumbnailId(c: any): string | undefined {
  return c?.thumbnail_id ?? c?.thumbnailId;
}

function buildMediaUrl(id?: string) {
  return id ? `${API_URL}/media/${id}` : "";
}

export default function VaultDetailPage() {
  const { vaultId } = useParams();
  const [vault, setVault] = useState<VaultPublic | null>(null);
  const [items, setItems] = useState<CarouselItem[]>([]);
  const [topTags, setTopTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [addedCards, setAddedCards] = useState<CardPublic[]>([]);

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
    form.append("file", file);

    const res = await fetch(endpoint, { method: "POST", body: form });

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

        const cardsRes = await fetch(`${API_URL}/api/vaults/${vaultId}/cards`, {
          signal: ac.signal,
        });

        const topTagsRes = await fetch(
          `${API_URL}/api/vaults/${vaultId}/top-tags?limit=7`,
          { signal: ac.signal }
        );

        if (cardsRes.ok) {
          const cards = (await cardsRes.json()) as CardPublic[];

          const carouselItems: CarouselItem[] = cards
            .map((card) => {
              const cardId = getCardId(card);
              const mediaType = getMediaType(card);
              const mediaId = getMediaId(card);
              const thumbId = getThumbnailId(card);
              const caption = (card as any)?.caption ?? "Untitled";

              if (!cardId || !mediaId || !mediaType) return null;

              const isVideo = mediaType === "video";

              const thumbnailUrl = thumbId
                ? buildMediaUrl(thumbId)
                : isVideo
                ? VIDEO_THUMB_PLACEHOLDER
                : buildMediaUrl(mediaId);

              return {
                id: cardId,
                title: caption,
                creator: "",
                type: isVideo ? "video" : "photo",
                thumbnailUrl,
                photoUrl: isVideo ? undefined : buildMediaUrl(mediaId),
                videoUrl: isVideo ? buildMediaUrl(mediaId) : undefined,
                card,
              } satisfies CarouselItem;
            })
            .filter(Boolean) as CarouselItem[];

          setItems(carouselItems);
        } else {
          setItems([]);
        }

        if (topTagsRes.ok) {
          const tags = (await topTagsRes.json()) as string[];
          setTopTags(tags);
        } else {
          setTopTags([]);
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
      const id = getCardId(c as any);
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

    for (const [tag, list] of map) {
      const seen = new Set<string>();
      map.set(
        tag,
        list.filter((c) => {
          const id = getCardId(c as any);
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
    const allTags = Array.from(cardsByTag.entries())
      .sort((a, b) => b[1].length - a[1].length)
      .map(([tag]) => tag);

    // If there are fewer than 7 tags total, show them all.
    if (allTags.length <= 7) return allTags;

    // If backend didn't return anything, fall back to showing all tags.
    if (!topTags || topTags.length === 0) return allTags;

    const topSet = new Set(topTags.map((t) => String(t).trim().toLowerCase()));

    // Otherwise, show only the backend top tags (but keep the frontend ordering by count)
    const filtered = allTags.filter((tag) => topSet.has(tag.toLowerCase()));

    // Safety fallback: if filtering removes everything, show all.
    return filtered.length > 0 ? filtered : allTags;
  }, [cardsByTag, topTags]);

  const toLineItems = (tag: string): CategoryLineItem[] => {
    const list = cardsByTag.get(tag) ?? [];

    return list
      .map((c) => {
        const cardId = getCardId(c as any);
        const mediaId = getMediaId(c as any);
        const mediaType = getMediaType(c as any);
        const thumbId = getThumbnailId(c as any);

        if (!cardId || !mediaId || !mediaType) return null;

        const matchingItem = items.find((it) => {
          const itId = getCardId((it.card as any) ?? {});
          return itId === cardId;
        });

        const isVideo = mediaType === "video";

        const fallbackThumb = thumbId
          ? buildMediaUrl(thumbId)
          : isVideo
          ? VIDEO_THUMB_PLACEHOLDER
          : buildMediaUrl(mediaId);

        const fallbackSrc = buildMediaUrl(mediaId);

        const photoUrl =
          matchingItem?.photoUrl ??
          (!isVideo ? fallbackSrc : undefined) ??
          undefined;

        const videoUrl =
          matchingItem?.videoUrl ?? (isVideo ? fallbackSrc : undefined);

        const type: "video" | "photo" = isVideo ? "video" : "photo";

        return {
          id: `${tag}-${cardId}`,
          title: (c as any).caption ?? "Untitled",
          type,
          thumbnailUrl: matchingItem?.thumbnailUrl ?? fallbackThumb,
          photoUrl: type === "video" ? undefined : photoUrl,
          videoUrl: type === "video" ? videoUrl : undefined,
          card: c,
        } satisfies CategoryLineItem;
      })
      .filter(Boolean) as CategoryLineItem[];
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
                    <CategoryLine
                      title={`#${tag}`}
                      items={toLineItems(tag)}
                      apiBaseUrl={API_URL}
                      onItemDeleted={(itemId) => {
                        setItems((prev) =>
                          prev.filter((item) => item.id !== itemId)
                        );
                      }}
                    />
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
                    key={getCardId(c as any)}
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
