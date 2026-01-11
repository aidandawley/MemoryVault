import React, { useEffect, useMemo, useRef, useState } from "react";
import "../../styles/Carousel.css";

import type { CardPublic } from "../../types/card";

export type CarouselItem = {
  id: string;
  title: string;
  creator?: string;

  type: "photo" | "video";
  thumbnailUrl: string;

  photoUrl?: string;
  videoUrl?: string;

  card?: CardPublic;
};

type Props = {
  items: CarouselItem[];
  initialIndex?: number;
  radius?: number;
  onActiveChange?: (item: CarouselItem, index: number) => void;
};

function mod(n: number, m: number) {
  return ((n % m) + m) % m;
}

function circularOffset(index: number, active: number, length: number) {
  const raw = index - active;
  if (raw > length / 2) return raw - length;
  if (raw < -length / 2) return raw + length;
  return raw;
}

export default function Carousel({
  items,
  initialIndex = 0,
  radius = 2,
  onActiveChange,
}: Props) {
  const length = items.length;
  const [active, setActive] = useState(() =>
    length ? mod(initialIndex, length) : 0
  );
  const activeVideoRef = useRef<HTMLVideoElement | null>(null);

  const [openItem, setOpenItem] = useState<CarouselItem | null>(null);

  const setActiveIndex = (next: number) => {
    if (!length) return;
    const idx = mod(next, length);
    setActive(idx);
    onActiveChange?.(items[idx], idx);
  };

  const goLeft = () => setActiveIndex(active - 1);
  const goRight = () => setActiveIndex(active + 1);

  useEffect(() => {
    const activeItem = items[active];
    if (!activeItem || activeItem.type !== "video") return;

    const v = activeVideoRef.current;
    if (!v) return;

    v.currentTime = 0;
    const p = v.play();
    if (p && typeof (p as Promise<void>).catch === "function") {
      (p as Promise<void>).catch(() => {});
    }
  }, [active, items]);

  const visibleIndices = useMemo(() => {
    if (!length) return [];
    const out: number[] = [];
    for (let d = -radius; d <= radius; d++) out.push(mod(active + d, length));
    return out;
  }, [active, length, radius]);

  const getCardStyle = (index: number): React.CSSProperties => {
    const offset = circularOffset(index, active, length);
    const abs = Math.abs(offset);

    const translateX = offset * 260;
    const translateY = abs * 22;
    const scale = 1 - abs * 0.12;
    const rotateY = offset * -18;

    const zIndex = 100 - abs;
    const opacity = 1 - abs * 0.18;

    return {
      transform: `
        translate(-50%, -50%)
        translateX(${translateX}px)
        translateY(${translateY}px)
        perspective(1200px)
        rotateY(${rotateY}deg)
        scale(${scale})
      `,
      zIndex,
      opacity,
    };
  };

  if (!items.length) return null;

  return (
    <>
      <section
        className="mv-carousel"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") goLeft();
          if (e.key === "ArrowRight") goRight();
          if (e.key === "Enter") {
            const item = items[active];
            if (item) setOpenItem(item);
          }
          if (e.key === "Escape") setOpenItem(null);
        }}
        aria-label="Featured media"
      >
        <button
          className="mv-carousel__nav mv-carousel__nav--left"
          onClick={goLeft}
          aria-label="Previous"
        >
          ◀
        </button>

        <button
          className="mv-carousel__nav mv-carousel__nav--right"
          onClick={goRight}
          aria-label="Next"
        >
          ▶
        </button>

        <div className="mv-carousel__stage">
          {visibleIndices.map((index) => {
            const item = items[index];
            const offset = circularOffset(index, active, length);
            const isActive = offset === 0;

            return (
              <article
                key={item.id}
                className={`mv-carousel__card ${isActive ? "is-active" : ""}`}
                style={getCardStyle(index)}
                onClick={() => {
                  if (!isActive) {
                    setActiveIndex(index);
                    return;
                  }
                  setOpenItem(item);
                }}
                role="button"
                aria-label={
                  isActive ? `Open ${item.title}` : `Select ${item.title}`
                }
              >
                <div className="mv-carousel__media">
                  {isActive ? (
                    item.type === "video" ? (
                      <video
                        ref={activeVideoRef}
                        className="mv-carousel__video"
                        src={item.videoUrl}
                        poster={item.thumbnailUrl}
                        muted
                        loop
                        playsInline
                        autoPlay
                        preload="metadata"
                      />
                    ) : (
                      <img
                        className="mv-carousel__thumb"
                        src={item.photoUrl ?? item.thumbnailUrl}
                        alt={item.title}
                        draggable={false}
                      />
                    )
                  ) : (
                    <img
                      className="mv-carousel__thumb"
                      src={item.thumbnailUrl}
                      alt={item.title}
                      draggable={false}
                      loading="lazy"
                    />
                  )}

                  <div className="mv-carousel__gradient" />

                  <div className="mv-carousel__meta">
                    <div className="mv-carousel__title">{item.title}</div>
                    <div className="mv-carousel__sub">
                      {item.creator ? <span>{item.creator}</span> : null}
                      {isActive ? (
                        <span className="mv-carousel__dot">•</span>
                      ) : null}
                      {isActive ? (
                        <span className="mv-carousel__hint">Click to open</span>
                      ) : null}
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {openItem && (
        <div className="mv-cardModal" role="dialog" aria-modal="true">
          <button
            className="mv-cardModal__backdrop"
            onClick={() => setOpenItem(null)}
            aria-label="Close"
          />
          <div className="mv-cardModal__content">
            <button
              className="mv-cardModal__close"
              onClick={() => setOpenItem(null)}
              aria-label="Close"
            >
              ✕
            </button>

            <div className="mv-cardModalCard">
              <div className="mv-cardModalCard__top">
                <div className="mv-cardModalCard__title">
                  {openItem.card?.caption ?? openItem.title ?? "Untitled"}
                </div>

                {openItem.card && (
                  <div
                    className={`mv-cardModalCard__status ${
                      openItem.card.isActive ? "active" : ""
                    }`}
                  >
                    {openItem.card.isActive ? "Active" : "Inactive"}
                  </div>
                )}
              </div>

              <div className="mv-cardModalCard__media">
                {openItem.type === "video" ? (
                  <video
                    className="mv-cardModalCard__mediaEl"
                    src={openItem.videoUrl ?? openItem.thumbnailUrl}
                    poster={openItem.thumbnailUrl}
                    controls
                    preload="metadata"
                  />
                ) : (
                  <img
                    className="mv-cardModalCard__mediaEl"
                    src={openItem.photoUrl ?? openItem.thumbnailUrl}
                    alt={openItem.card?.caption ?? openItem.title}
                    loading="lazy"
                  />
                )}

                {openItem.card?.tags?.length ? (
                  <div className="mv-cardModalCard__tagOverlay">
                    {openItem.card.tags.slice(0, 8).map((t) => (
                      <span key={t} className="mv-cardModalCard__tagChip">
                        #{t}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="mv-cardModalCard__bottom">
                <div className="mv-cardModalCard__caption">
                  {openItem.card?.caption ?? openItem.title ?? ""}
                </div>

                {openItem.creator ? (
                  <div className="mv-cardModalCard__creator">
                    {openItem.creator}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
