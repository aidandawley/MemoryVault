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

  return (
    <div onClick={() => onClick?.(card.cardId)} className="card-container">
      <div className="card-header">
        <div className={`card-status ${card.isActive ? "active" : ""}`}>
          {card.isActive ? "Active" : "Inactive"}
        </div>
      </div>

      <div className="card-mediaWrapper">
        {card.media_type === "video" ? (
          <video
            src={mediaSrc}
            controls
            preload="metadata"
            className="card-video"
          />
        ) : (
          <img src={mediaSrc} alt={card.caption} className="card-image" />
        )}
      </div>

      <div className="card-caption">{card.caption}</div>

      {card.tags.length > 0 && (
        <div className="card-tags">
          {card.tags.map((t) => (
            <span key={t} className="card-tag">
              #{t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
