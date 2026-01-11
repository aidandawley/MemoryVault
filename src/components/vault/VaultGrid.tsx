import React from "react";
import type { VaultPublic } from "./VaultTypes";

type Props = {
  vaults: VaultPublic[];
  onOpenVault?: (vaultId: string) => void;
};

export function VaultGrid({ vaults, onOpenVault }: Props) {
  return (
    <div className="vaultGrid">
      {vaults.map((v) => (
        <div
          key={v.vaultId}
          className="vaultCard"
          onClick={() => onOpenVault?.(v.vaultId)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") onOpenVault?.(v.vaultId);
          }}
        >
          <div className="vaultTitle">{v.title}</div>
          <div className="vaultDesc">{v.description}</div>
        </div>
      ))}
    </div>
  );
}
