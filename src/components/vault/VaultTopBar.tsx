import React from "react";

type Props = {
  userName: string;
  loading: boolean;
  totalCount: number;
  query: string;
  setQuery: (v: string) => void;
};

export function VaultTopBar({
  userName,
  loading,
  totalCount,
  query,
  setQuery,
}: Props) {
  return (
    <header className="vaultTopBar">
      <div className="vaultTopLeft">
        <div className="vaultTitle">{userName}&apos;s vaults</div>
        <div className="vaultSubtitle">
          {loading ? "Loading…" : `${totalCount} total`}
        </div>
      </div>

      <div className="vaultTopRight">
        <div className="vaultSearchWrap">
          <input
            className="vaultSearch"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search vaults"
            aria-label="Search vaults"
          />
        </div>
      </div>
    </header>
  );
}
