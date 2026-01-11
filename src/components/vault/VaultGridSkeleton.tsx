import React from "react";

type Props = {
  count?: number;
};

export function VaultGridSkeleton({ count = 8 }: Props) {
  return (
    <div className="vaultGrid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="vaultCard vaultCardSkeleton">
          <div className="vaultCardCover" />
          <div className="vaultCardMeta">
            <div className="vaultSkLine vaultSkLine1" />
            <div className="vaultSkLine vaultSkLine2" />
          </div>
        </div>
      ))}
    </div>
  );
}
