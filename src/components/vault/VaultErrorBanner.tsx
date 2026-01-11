import React from "react";

type Props = {
  message: string;
  onReload: () => void;
};

export function VaultErrorBanner({ message, onReload }: Props) {
  return (
    <div className="vaultBanner vaultBannerError">
      <div className="vaultBannerTitle">Couldn’t load vaults</div>
      <div className="vaultBannerText">{message}</div>
      <button className="vaultButton" onClick={onReload} type="button">
        Reload
      </button>
    </div>
  );
}
