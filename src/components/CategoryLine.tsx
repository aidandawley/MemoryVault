import React, { useEffect, useMemo, useRef, useState } from "react";
import "../styles/CategoryLine.css";
import type { CardPublic } from "../types/card";
import SectionTag from "./SectionTag";
export type CategoryLineItem = {
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
  title?: string;
  items: CategoryLineItem[];
};

export default function CategoryLine({ title, items }: Props) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [openItem, setOpenItem] = useState<CategoryLineItem | null>(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  const updateEdges = () => {
    const el = scrollerRef.current;
    if (!el) return;
    const max = el.scrollWidth - el.clientWidth;
    setCanLeft(el.scrollLeft > 2);
    setCanRight(el.scrollLeft < max - 2);
  };

  useEffect(() => {
    updateEdges();
  }, [items.length]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;

    const onScroll = () => updateEdges();
    el.addEventListener("scroll", onScroll, { passive: true });

    const ro = new ResizeObserver(() => updateEdges());
    ro.observe(el);

    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, []);

  const scrollByPage = (dir: "left" | "right") => {
    const el = scrollerRef.current;
    if (!el) return;

    const amount = Math.max(320, Math.floor(el.clientWidth * 0.85));
    el.scrollBy({
      left: dir === "left" ? -amount : amount,
      behavior: "smooth",
    });
  };

  const modalTitle = useMemo(() => {
    if (!openItem) return "";
    return openItem.card?.caption ?? openItem.title ?? "Untitled";
  }, [openItem]);

  return (
    <>
      {title && <SectionTag tag={title.toString()} />}
      <section className="cl">
        {title ? <div className="cl-title">{title}</div> : null}

        <div className="cl-row">
          <button
            className={`cl-nav cl-nav--left ${canLeft ? "" : "is-hidden"}`}
            onClick={() => scrollByPage("left")}
            aria-label="Scroll left"
          >
            ◀
          </button>

          <div
            ref={scrollerRef}
            className="cl-scroller"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "ArrowLeft") scrollByPage("left");
              if (e.key === "ArrowRight") scrollByPage("right");
              if (e.key === "Escape") setOpenItem(null);
            }}
            aria-label="Media row"
          >
            {items.map((item) => {
              const src =
                item.type === "photo" ? item.thumbnailUrl : item.thumbnailUrl;

              return (
                <button
                  key={item.id}
                  className="cl-item"
                  onClick={() => setOpenItem(item)}
                  aria-label={`Open ${item.title}`}
                >
                  <div className="cl-thumbWrap">
                    <img
                      className="cl-thumb"
                      src={src}
                      alt={item.title}
                      loading="lazy"
                      draggable={false}
                    />

                    {item.type === "video" ? (
                      <div className="cl-playBadge" aria-hidden="true">
                        ▶
                      </div>
                    ) : null}

                    <div className="cl-gradient" />

                    <div className="cl-meta">
                      <div className="cl-metaTitle">{item.title}</div>
                      <div className="cl-metaSub">
                        {item.creator ? <span>{item.creator}</span> : null}
                        {item.card?.tags?.length ? (
                          <span className="cl-dot">•</span>
                        ) : null}
                        {item.card?.tags?.length ? (
                          <span className="cl-metaHint">
                            {item.card.tags
                              .slice(0, 2)
                              .map((t) => `#${t}`)
                              .join(" ")}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          <button
            className={`cl-nav cl-nav--right ${canRight ? "" : "is-hidden"}`}
            onClick={() => scrollByPage("right")}
            aria-label="Scroll right"
          >
            ▶
          </button>
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
                <div className="mv-cardModalCard__title">{modalTitle}</div>

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
                    alt={modalTitle}
                    loading="lazy"
                  />
                )}

                {openItem.card?.tags?.length ? (
                  <div className="mv-cardModalCard__tagOverlay">
                    {openItem.card.tags.slice(0, 12).map((t) => (
                      <span key={t} className="mv-cardModalCard__tagChip">
                        #{t}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="mv-cardModalCard__bottom">
                <div className="mv-cardModalCard__caption">{modalTitle}</div>
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
