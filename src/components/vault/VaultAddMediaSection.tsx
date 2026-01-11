/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import AddVaultMediaButton from "./AddVaultMediaButton";
import "../../styles/VaultAddMediaSection.css";

export type MediaAnalysisResult =
  | { kind: "image"; tags: string[] }
  | { kind: "video"; video_id?: string; hashtags: string[] };

type Props = {
  vaultId: string;
  apiBaseUrl?: string;
  onCreated?: (card: any) => void;

  // ✅ NEW: allow VaultDetailPage to inject the analyzer
  analyzeMediaFile?: (file: File) => Promise<MediaAnalysisResult>;
};

export default function VaultAddMediaSection({
  vaultId,
  apiBaseUrl,
  onCreated,
  analyzeMediaFile,
}: Props) {
  return (
    <section className="vams-wrap" aria-label="Add media to vault">
      <div className="vams-card">
        <div className="vams-left">
          <div className="vams-title">Add a new memory</div>
          <div className="vams-sub">
            Upload a photo or video and we’ll add it to this vault as a new
            card.
          </div>
        </div>

        <div className="vams-right">
          <AddVaultMediaButton
            vaultId={vaultId}
            apiBaseUrl={apiBaseUrl}
            onCreated={onCreated}
            analyzeMediaFile={analyzeMediaFile}
          />
        </div>
      </div>
    </section>
  );
}