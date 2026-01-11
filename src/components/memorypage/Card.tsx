import React from "react";
import type { CardPublic } from "../../types/card";
import "../../styles/Card.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

type Props = {
  card: CardPublic;
  onClick?: (cardId: string) => void;
};

export function Card({ card, onClick }: Props) {
  const mediaSrc = `${API_URL}/media/${card.media_id}`;
  const statusText = card.isActive ? "Active" : "Inactive";

  return (
    <div className="card" onClick={() => onClick?.(card.cardId)} role="button">
      <div className="card-top">
        <div className="card-title">{card.caption || "Untitled"}</div>

        <div className={`card-statusPill ${card.isActive ? "active" : ""}`}>
          {statusText}
        </div>
      </div>

      <div className="card-media">
        {card.media_type === "video" ? (
          <video
            src={mediaSrc}
            controls
            preload="metadata"
            className="card-mediaEl"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <img
            src={mediaSrc}
            alt={card.caption}
            className="card-mediaEl"
            loading="lazy"
            onClick={(e) => e.stopPropagation()}
          />
        )}

        {card.tags.length > 0 && (
          <div className="card-tagOverlay">
            {card.tags.slice(0, 6).map((t) => (
              <span key={t} className="card-tagChip">
                #{t}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="card-bottom">
        {card.tags.length > 0 ? (
          <div className="card-tagsRow">
            {card.tags.slice(0, 10).map((t) => (
              <span key={t} className="card-tagLine">
                #{t}
              </span>
            ))}
          </div>
        ) : (
          <div className="card-muted">No tags yet</div>
        )}
      </div>
    </div>
  );
}
