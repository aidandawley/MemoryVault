// src/components/vault/AddVaultMediaButton.tsx
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useMemo, useRef, useState } from "react";
import "../../styles/AddVaultMediaButton.css";

type CardPublic = any;

export type MediaAnalysisResult =
  | { kind: "image"; tags: string[] }
  | { kind: "video"; video_id?: string; hashtags: string[] };

type Props = {
  vaultId: string;
  apiBaseUrl?: string;
  className?: string;
  onCreated?: (card: CardPublic) => void;

  // ✅ NEW: injected analyzer (photo->Gemini, video->TwelveLabs)
  analyzeMediaFile?: (file: File) => Promise<MediaAnalysisResult>;
};

const DEFAULT_API =
  (import.meta as any).env?.VITE_API_URL ?? "http://127.0.0.1:8000";

function getMediaType(file: File): "image" | "video" | null {
  if ((file.type || "").startsWith("image/")) return "image";
  if ((file.type || "").startsWith("video/")) return "video";
  return null;
}

async function readTextSafe(res: Response) {
  try {
    return await res.text();
  } catch {
    return "";
  }
}

export default function AddVaultMediaButton({
  vaultId,
  apiBaseUrl = DEFAULT_API,
  className,
  onCreated,
  analyzeMediaFile,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState(""); // optional
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaType = useMemo(() => (file ? getMediaType(file) : null), [file]);

  const canSubmit = useMemo(() => {
    return (
      !!vaultId &&
      !!file &&
      !!mediaType &&
      title.trim().length > 0 &&
      !uploading
    );
  }, [vaultId, file, mediaType, title, uploading]);

  function reset() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setTitle("");
    setDescription("");
    setUploading(false);
    setError(null);
  }

  function close() {
    setOpen(false);
    setTimeout(() => reset(), 120);
  }

  function pickFile(next: File | null) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setError(null);

    if (!next) {
      setFile(null);
      setPreviewUrl(null);
      return;
    }

    const mt = getMediaType(next);
    if (!mt) {
      setFile(null);
      setPreviewUrl(null);
      setError("Unsupported file type. Please upload an image or a video.");
      return;
    }

    setFile(next);
    setPreviewUrl(URL.createObjectURL(next));
  }

  async function submit() {
    if (!canSubmit || !file || !mediaType) return;

    setUploading(true);
    setError(null);

    try {
      // ✅ Step 1: analyze photo/video (if provided)
      let autoTags: string[] = [];
      let analysisKind: "image" | "video" | null = null;

      if (analyzeMediaFile) {
        const analysis = await analyzeMediaFile(file);

        if (analysis.kind === "image") {
          analysisKind = "image";
          autoTags = Array.isArray(analysis.tags) ? analysis.tags : [];
        } else {
          analysisKind = "video";
          autoTags = Array.isArray(analysis.hashtags) ? analysis.hashtags : [];
        }
      }

      // ✅ Step 2: merge user-entered description tags + AI tags
      // (backend expects "tags" as comma-separated string per your comment)
      const userTags = description
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      const merged = Array.from(new Set([...autoTags, ...userTags]));

      const form = new FormData();
      form.append("file", file);
      form.append("media_type", mediaType);
      form.append("caption", title.trim());
      form.append("tags", merged.join(","));
      form.append("isActive", "true");

      // Optional: if you store this, nice for debugging
      if (analysisKind) form.append("analysis_kind", analysisKind);

      const res = await fetch(`${apiBaseUrl}/api/vaults/${vaultId}/cards`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const text = await readTextSafe(res);
        throw new Error(text || `Upload failed (${res.status})`);
      }

      const card = await res.json();
      onCreated?.(card);
      close();
    } catch (e: any) {
      setError(e?.message ?? "Failed to upload");
      setUploading(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className={`avmb-btn ${className ?? ""}`}
        onClick={() => setOpen(true)}
      >
        <span className="avmb-btnIcon" aria-hidden="true">
          ＋
        </span>
        <span>Add media</span>
      </button>

      {open && (
        <div className="avmb-modal" role="dialog" aria-modal="true">
          <button
            className="avmb-backdrop"
            onClick={() => !uploading && close()}
            aria-label="Close"
          />

          <div className="avmb-panel">
            <div className="avmb-top">
              <div className="avmb-title">Add to vault</div>
              <button
                className="avmb-x"
                onClick={close}
                disabled={uploading}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="avmb-body">
              <div className="avmb-grid">
                <div className="avmb-left">
                  <div className="avmb-upload">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*,video/*"
                      className="avmb-file"
                      onChange={(e) => {
                        pickFile(e.target.files?.[0] ?? null);
                        e.currentTarget.value = "";
                      }}
                      disabled={uploading}
                    />

                    {previewUrl ? (
                      <div className="avmb-preview">
                        {mediaType === "video" ? (
                          <video
                            src={previewUrl}
                            controls
                            className="avmb-media"
                          />
                        ) : (
                          <img src={previewUrl} className="avmb-media" alt="" />
                        )}

                        <button
                          type="button"
                          className="avmb-change"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploading}
                        >
                          Change
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="avmb-pick"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                      >
                        Upload photo or video
                      </button>
                    )}
                  </div>
                </div>

                <div className="avmb-right">
                  <label className="avmb-field">
                    <div className="avmb-label">Title</div>
                    <input
                      className="avmb-input"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Give this memory a title"
                      disabled={uploading}
                      autoFocus
                    />
                  </label>

                  <label className="avmb-field">
                    <div className="avmb-label">Description</div>
                    <textarea
                      className="avmb-textarea"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Optional (comma-separated tags work best)"
                      rows={6}
                      disabled={uploading}
                    />
                  </label>

                  {error && <div className="avmb-error">{error}</div>}

                  <div className="avmb-actions">
                    <button
                      className="avmb-cancel"
                      onClick={close}
                      disabled={uploading}
                    >
                      Cancel
                    </button>
                    <button
                      className="avmb-primary"
                      onClick={submit}
                      disabled={!canSubmit}
                    >
                      {uploading ? "Uploading..." : "Add"}
                    </button>
                  </div>

                  <div className="avmb-hint">
                    Upload a photo/video, add a title + description, and we’ll
                    create a new card in this vault.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}