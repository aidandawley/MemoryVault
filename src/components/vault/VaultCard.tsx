import React from "react";
import type { VaultPublic } from "./VaultTypes";
import { colorClassForVaultId } from "./VaultColors";

type Props = {
  vault: VaultPublic;
  onOpenVault?: (vaultId: string) => void;
};

export function VaultCard({ vault, onOpenVault }: Props) {
  const colorClass = colorClassForVaultId(vault.vaultId);

  return (
    <button
      className="vaultCard"
      onClick={() => onOpenVault?.(vault.vaultId)}
      type="button"
    >
      <div className={`vaultCardCover ${colorClass}`}>
        <div className="vaultCoverMark" />
      </div>

      <div className="vaultCardMeta">
        <div className="vaultCardTitle" title={vault.title}>
          {vault.title}
        </div>
        <div className="vaultCardDesc" title={vault.description ?? ""}>
          {vault.description ?? "—"}
        </div>
      </div>
    </button>
  );
}
