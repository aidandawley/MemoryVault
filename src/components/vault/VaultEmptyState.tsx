import React from "react";

type Props = {
  hasQuery: boolean;
};

export function VaultEmptyState({ hasQuery }: Props) {
  return (
    <div className="vaultEmpty">
      <div className="vaultEmptyTitle">No vaults found</div>
      <div className="vaultEmptyText">
        {hasQuery
          ? "Try a different search."
          : "Create your first vault to get started."}
      </div>
    </div>
  );
}
