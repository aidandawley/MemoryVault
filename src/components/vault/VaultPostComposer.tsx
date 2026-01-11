/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useMemo, useRef, useState } from "react";
import "../../styles/VaultPostComposer.css";

type Props = {
  vaultId: string;
  apiBaseUrl?: string;
  onCreated?: (card: any) => void;
};

const DEFAULT_API =
  (import.meta as any).env?.VITE_API_URL ?? "http://127.0.0.1:8000";

function getMediaType(file: File): "image" | "video" | null {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  return null;
}

function parseTags(input: string): string[] {
  const raw = input
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const uniq: string[] = [];
  for (const t of raw) {
    const key = t.toLowerCase();
    if (!uniq.some((x) => x.toLowerCase() === key)) uniq.push(t);
  }
  return uniq.slice(0, 12);
}

async function readTextSafe(res: Response) {
  try {
    return await res.text();
  } catch {
    return "";
  }
}

export default function VaultPostComposer({
  vaultId,
  apiBaseUrl = DEFAULT_API,
  onCreated,
}: Props) {
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [caption, setCaption] = useState("");
  const [tagsInput, setTagsInput] = useState("");

  const [posting, setPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaType = useMemo(() => (file ? getMediaType(file) : null), [file]);
  const tags = useMemo(() => parseTags(tagsInput), [tagsInput]);

  const canPost = useMemo(() => {
    return (
      !!vaultId &&
      !!file &&
      !!mediaType &&
      caption.trim().length > 0 &&
      !posting
    );
  }, [vaultId, file, mediaType, caption, posting]);

  function reset() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setCaption("");
    setTagsInput("");
    setPosting(false);
    setError(null);
  }

  function pick(next: File | null) {
    setError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);

    if (!next) {
      setFile(null);
      setPreviewUrl(null);
      return;
    }

    const mt = getMediaType(next);
    if (!mt) {
      setFile(null);
      setPreviewUrl(null);
      setError("Unsupported file. Upload an image or video.");
      return;
    }

    setFile(next);
    setPreviewUrl(URL.createObjectURL(next));
  }

  async function post() {
    if (!canPost || !file || !mediaType) return;

    setPosting(true);
    setError(null);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("media_type", mediaType);
      form.append("caption", caption.trim());
      form.append("tags", tags.join(",")); // backend expects comma-separated
      form.append("isActive", "true");

      const res = await fetch(`${apiBaseUrl}/api/vaults/${vaultId}/cards`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const text = await readTextSafe(res);
        throw new Error(text || `Post failed (${res.status})`);
      }

      const card = await res.json();
      onCreated?.(card);
      reset();
    } catch (e: any) {
      setError(e?.message ?? "Failed to post");
      setPosting(false);
    }
  }

  return (
    <section className="vpc-shell" aria-label="Create post">
      <div className="vpc-card">
        <div className="vpc-header">
          <div className="vpc-title">Create a memory</div>
          <div className="vpc-sub">
            Upload a photo/video + caption and add tags.
          </div>
        </div>

        <div className="vpc-body">
          <div className="vpc-left">
            <input
              ref={fileRef}
              type="file"
              accept="image/*,video/*"
              className="vpc-file"
              onChange={(e) => {
                pick(e.target.files?.[0] ?? null);
                e.currentTarget.value = "";
              }}
              disabled={posting}
            />

            {previewUrl ? (
              <div className="vpc-preview">
                {mediaType === "video" ? (
                  <video src={previewUrl} className="vpc-media" controls />
                ) : (
                  <img src={previewUrl} className="vpc-media" alt="" />
                )}

                <div className="vpc-previewActions">
                  <button
                    type="button"
                    className="vpc-ghost"
                    onClick={() => fileRef.current?.click()}
                    disabled={posting}
                  >
                    Change
                  </button>

                  <button
                    type="button"
                    className="vpc-danger"
                    onClick={() => pick(null)}
                    disabled={posting}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="vpc-pick"
                onClick={() => fileRef.current?.click()}
                disabled={posting}
              >
                Upload photo or video
              </button>
            )}
          </div>

          <div className="vpc-right">
            <label className="vpc-field">
              <div className="vpc-label">Caption</div>
              <textarea
                className="vpc-textarea"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="Write a caption..."
                rows={5}
                disabled={posting}
              />
            </label>

            <label className="vpc-field">
              <div className="vpc-label">Tags</div>
              <input
                className="vpc-input"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="e.g. family, summer, japan"
                disabled={posting}
              />
            </label>

            <div className="vpc-tagsRow" aria-label="Selected tags">
              {tags.length === 0 ? (
                <div className="vpc-tagsEmpty">No tags yet</div>
              ) : (
                tags.map((t) => (
                  <span key={t.toLowerCase()} className="vpc-tag">
                    {t}
                  </span>
                ))
              )}
            </div>

            {error && <div className="vpc-error">{error}</div>}

            <div className="vpc-actions">
              <button
                type="button"
                className="vpc-ghost"
                onClick={reset}
                disabled={posting}
              >
                Clear
              </button>
              <button
                type="button"
                className="vpc-primary"
                onClick={post}
                disabled={!canPost}
              >
                {posting ? "Posting..." : "Post"}
              </button>
            </div>

            <div className="vpc-footnote">
              Caption is required. Tags are optional and saved as
              comma-separated tags.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
