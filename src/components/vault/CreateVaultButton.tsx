// src/components/CreateVaultButton.tsx
import React, { useMemo, useRef, useState } from "react";
import "../../styles/CreateVault.css";

type Vault = {
  id?: string;
  vaultId?: string;
  title: string;
  description?: string | null;
};

type CardPublic = {
  cardId: string;
  mediaId: string;
  mediaType: "image" | "video";
  caption: string;
  tags: string[];
  isActive: boolean;
};

type UploadItem = {
  id: string;
  file: File;
  previewUrl: string;
  caption: string;
  tags: string;
  isActive: boolean;
};

type Props = {
  apiBaseUrl?: string;
  buttonLabel?: string;
  className?: string;
  disabled?: boolean;
  defaultTitle?: string;
  defaultDescription?: string;
  onCreated?: (result: { vault: Vault; cards: CardPublic[] }) => void;
};

const DEFAULT_API =
  (import.meta as any).env?.VITE_API_URL ?? "http://127.0.0.1:8000";

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function getMediaType(file: File): "image" | "video" | null {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  return null;
}

async function readTextSafe(res: Response) {
  try {
    return await res.text();
  } catch {
    return "";
  }
}

async function createVault(
  apiBaseUrl: string,
  payload: { title: string; description?: string }
) {
  const res = await fetch(`${apiBaseUrl}/api/vaults`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok)
    throw new Error((await readTextSafe(res)) || "Failed to create vault");
  return (await res.json()) as Vault;
}

async function uploadCard(
  apiBaseUrl: string,
  vaultId: string,
  payload: { file: File; caption: string; tags?: string; isActive: boolean }
) {
  const mediaType = getMediaType(payload.file);
  if (!mediaType)
    throw new Error(`Unsupported file type: ${payload.file.type}`);

  const form = new FormData();
  form.append("file", payload.file);
  form.append("caption", payload.caption);
  form.append("media_type", mediaType);
  form.append("isActive", String(payload.isActive));
  if (payload.tags) form.append("tags", payload.tags);

  const res = await fetch(`${apiBaseUrl}/api/vaults/${vaultId}/cards`, {
    method: "POST",
    body: form,
  });

  if (!res.ok)
    throw new Error((await readTextSafe(res)) || "Failed to upload card");
  return (await res.json()) as CardPublic;
}

export default function CreateVaultButton({
  apiBaseUrl = DEFAULT_API,
  buttonLabel = "Create Vault",
  className,
  disabled,
  defaultTitle = "",
  defaultDescription = "",
  onCreated,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);

  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState(defaultDescription);

  const [items, setItems] = useState<UploadItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canNext = useMemo(() => title.trim().length > 0, [title]);
  const canCreate = useMemo(
    () => title.trim().length > 0 && items.length > 0 && !busy,
    [title, items.length, busy]
  );

  function resetAll() {
    items.forEach((i) => URL.revokeObjectURL(i.previewUrl));
    setStep(1);
    setTitle(defaultTitle);
    setDescription(defaultDescription);
    setItems([]);
    setBusy(false);
    setError(null);
  }

  function close() {
    setOpen(false);
    setTimeout(() => resetAll(), 150);
  }

  function onPickFiles(files: FileList | null) {
    if (!files || files.length === 0) return;

    const next: UploadItem[] = [];
    Array.from(files).forEach((file) => {
      const mt = getMediaType(file);
      if (!mt) return;
      const id = uid();
      next.push({
        id,
        file,
        previewUrl: URL.createObjectURL(file),
        caption: mt === "image" ? "New photo" : "New video",
        tags: "",
        isActive: true,
      });
    });

    if (next.length === 0) return;
    setItems((prev) => [...prev, ...next]);
  }

  function removeItem(id: string) {
    setItems((prev) => {
      const found = prev.find((x) => x.id === id);
      if (found) URL.revokeObjectURL(found.previewUrl);
      return prev.filter((x) => x.id !== id);
    });
  }

  async function handleCreate() {
    setError(null);
    setBusy(true);

    try {
      const vault = await createVault(apiBaseUrl, {
        title: title.trim(),
        description: description.trim() ? description.trim() : undefined,
      });

      const vaultId = vault.id ?? vault.vaultId;
      if (!vaultId) throw new Error("Vault created but returned no id");

      const uploaded: CardPublic[] = [];
      for (const item of items) {
        const card = await uploadCard(apiBaseUrl, vaultId, {
          file: item.file,
          caption: item.caption.trim() || "Untitled",
          tags: item.tags.trim() || undefined,
          isActive: item.isActive,
        });
        uploaded.push(card);
      }

      onCreated?.({ vault, cards: uploaded });
      close();
    } catch (e: any) {
      setError(e?.message ?? "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className={`cvb-button ${className ?? ""}`}
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        <span className="cvb-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 5v14M5 12h14"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <span className="cvb-label">{buttonLabel}</span>
      </button>

      {open && (
        <div className="cvb-overlay" role="dialog" aria-modal="true">
          <div className="cvb-modal">
            <div className="cvb-topbar">
              <div className="cvb-title">
                {step === 1 ? "Create a Vault" : "Add media"}
              </div>
              <button
                type="button"
                className="cvb-x"
                onClick={close}
                aria-label="Close"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M6 6l12 12M18 6L6 18"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>

            <div className="cvb-body">
              {step === 1 && (
                <div className="cvb-step">
                  <label className="cvb-field">
                    <div className="cvb-fieldLabel">Title</div>
                    <input
                      className="cvb-input"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Japan Trip, Family, Projects"
                      autoFocus
                    />
                  </label>

                  <label className="cvb-field">
                    <div className="cvb-fieldLabel">Description</div>
                    <textarea
                      className="cvb-textarea"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Optional"
                      rows={4}
                    />
                  </label>

                  <div className="cvb-hint">
                    This is like making a folder — you’ll add photos/videos
                    next.
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="cvb-step">
                  <div className="cvb-uploadRow">
                    <button
                      type="button"
                      className="cvb-uploadBtn"
                      onClick={() => inputRef.current?.click()}
                      disabled={busy}
                    >
                      <span className="cvb-uploadIcon" aria-hidden="true">
                        <svg
                          width="18"
                          height="18"
                          viewBox="0 0 24 24"
                          fill="none"
                        >
                          <path
                            d="M12 16V6"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                          />
                          <path
                            d="M8 10l4-4 4 4"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                          <path
                            d="M5 18a3 3 0 003 3h8a3 3 0 003-3"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                          />
                        </svg>
                      </span>
                      Add photos/videos
                    </button>

                    <input
                      ref={inputRef}
                      className="cvb-file"
                      type="file"
                      accept="image/*,video/*"
                      multiple
                      onChange={(e) => {
                        onPickFiles(e.target.files);
                        e.currentTarget.value = "";
                      }}
                    />

                    <div className="cvb-count">
                      {items.length === 0
                        ? "No media selected"
                        : `${items.length} item${
                            items.length === 1 ? "" : "s"
                          }`}
                    </div>
                  </div>

                  {items.length > 0 && (
                    <div className="cvb-grid">
                      {items.map((item) => {
                        const mt = getMediaType(item.file);
                        const isVideo = mt === "video";
                        return (
                          <div key={item.id} className="cvb-card">
                            <div className="cvb-preview">
                              {isVideo ? (
                                <video
                                  src={item.previewUrl}
                                  className="cvb-media"
                                  controls
                                />
                              ) : (
                                <img
                                  src={item.previewUrl}
                                  className="cvb-media"
                                  alt=""
                                />
                              )}

                              <button
                                type="button"
                                className="cvb-remove"
                                onClick={() => removeItem(item.id)}
                                disabled={busy}
                                aria-label="Remove"
                              >
                                <svg
                                  width="16"
                                  height="16"
                                  viewBox="0 0 24 24"
                                  fill="none"
                                >
                                  <path
                                    d="M6 6l12 12M18 6L6 18"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                  />
                                </svg>
                              </button>

                              <div className="cvb-badge">
                                {isVideo ? "Video" : "Image"}
                              </div>
                            </div>

                            <div className="cvb-cardBody">
                              <label className="cvb-miniField">
                                <div className="cvb-miniLabel">Caption</div>
                                <input
                                  className="cvb-miniInput"
                                  value={item.caption}
                                  onChange={(e) =>
                                    setItems((prev) =>
                                      prev.map((x) =>
                                        x.id === item.id
                                          ? { ...x, caption: e.target.value }
                                          : x
                                      )
                                    )
                                  }
                                  placeholder="Write a caption"
                                  disabled={busy}
                                />
                              </label>

                              <label className="cvb-miniField">
                                <div className="cvb-miniLabel">Tags</div>
                                <input
                                  className="cvb-miniInput"
                                  value={item.tags}
                                  onChange={(e) =>
                                    setItems((prev) =>
                                      prev.map((x) =>
                                        x.id === item.id
                                          ? { ...x, tags: e.target.value }
                                          : x
                                      )
                                    )
                                  }
                                  placeholder="comma,separated,tags"
                                  disabled={busy}
                                />
                              </label>

                              <div className="cvb-toggleRow">
                                <label className="cvb-toggle">
                                  <input
                                    type="checkbox"
                                    checked={item.isActive}
                                    onChange={(e) =>
                                      setItems((prev) =>
                                        prev.map((x) =>
                                          x.id === item.id
                                            ? {
                                                ...x,
                                                isActive: e.target.checked,
                                              }
                                            : x
                                        )
                                      )
                                    }
                                    disabled={busy}
                                  />
                                  <span>Active</span>
                                </label>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {items.length === 0 && (
                    <div className="cvb-empty">
                      <div className="cvb-emptyTitle">
                        Drop in your first memory
                      </div>
                      <div className="cvb-emptySub">
                        Add a photo or video like an Instagram post — we’ll turn
                        each one into a card.
                      </div>
                    </div>
                  )}
                </div>
              )}

              {error && <div className="cvb-error">{error}</div>}
            </div>

            <div className="cvb-footer">
              <div className="cvb-steps">
                <div className={`cvb-dot ${step === 1 ? "active" : ""}`} />
                <div className={`cvb-dot ${step === 2 ? "active" : ""}`} />
              </div>

              <div className="cvb-actions">
                {step === 2 ? (
                  <button
                    type="button"
                    className="cvb-ghost"
                    onClick={() => setStep(1)}
                    disabled={busy}
                  >
                    Back
                  </button>
                ) : (
                  <button
                    type="button"
                    className="cvb-ghost"
                    onClick={close}
                    disabled={busy}
                  >
                    Cancel
                  </button>
                )}

                {step === 1 ? (
                  <button
                    type="button"
                    className="cvb-primary"
                    onClick={() => setStep(2)}
                    disabled={!canNext}
                  >
                    Next
                  </button>
                ) : (
                  <button
                    type="button"
                    className="cvb-primary"
                    onClick={handleCreate}
                    disabled={!canCreate}
                  >
                    {busy ? "Creating..." : "Create Vault"}
                  </button>
                )}
              </div>
            </div>
          </div>

          <button
            type="button"
            className="cvb-backdrop"
            onClick={close}
            aria-label="Close backdrop"
          />
        </div>
      )}
    </>
  );
}
