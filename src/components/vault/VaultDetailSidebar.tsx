/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import type { VaultPublic } from "./VaultTypes";
import "../../styles/VaultDetailSidebar.css";

type Props = {
  vault: VaultPublic;
  apiBaseUrl?: string;
};

const DEFAULT_API =
  (import.meta as any).env?.VITE_API_URL ?? "http://127.0.0.1:8000";

export default function VaultDetailSidebar({
  vault,
  apiBaseUrl = DEFAULT_API,
}: Props) {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const ownerName =
    (vault as any)?.owner?.name ??
    (vault as any)?.ownerName ??
    (vault as any)?.createdBy ??
    "Owner";

  const sharedMembers: string[] =
    (vault as any)?.sharedMembers ??
    (vault as any)?.members ??
    (vault as any)?.sharedWith ??
    [];

  const vaultId = (vault as any)?.id ?? (vault as any)?.vaultId;

  async function handleDelete() {
    const id = (vault as any)?.id ?? (vault as any)?.vaultId;
    if (!id) {
      alert("Could not delete: missing vault id.");
      return;
    }

    setDeleting(true);

    try {
      const url = `${apiBaseUrl}/api/vaults/${id}`;

      const res = await fetch(url, {
        method: "DELETE",
        headers: { Accept: "application/json" },
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `Delete failed (${res.status})`);
      }

      setShowDeleteConfirm(false);
      navigate("/", { replace: true });
    } catch (e: any) {
      alert(e?.message ?? "Failed to delete vault");
      setDeleting(false);
    }
  }

  return (
    <aside className="vds-sidebar">
      <div className="vds-top">
        <button
          type="button"
          className="vds-homeBtn"
          onClick={() => navigate("/")}
          aria-label="Go home"
          title="Home"
        >
          ←
        </button>

        <div className="vds-brandBlock">
          <div className="vds-brand">MemoryVault</div>
          <div className="vds-subtitle">Vault</div>
        </div>
      </div>

      <div className="vds-section">
        <div className="vds-sectionTitle">Owner</div>
        <div className="vds-personRow">
          <div className="vds-avatar" aria-hidden="true">
            {String(ownerName).slice(0, 1).toUpperCase()}
          </div>
          <div className="vds-personMeta">
            <div className="vds-personName">{ownerName}</div>
            <div className="vds-personHint">Vault owner</div>
          </div>
        </div>
      </div>

      <div className="vds-divider" />

      <div className="vds-section">
        <div className="vds-sectionTitle">Shared members</div>

        {sharedMembers.length === 0 ? (
          <div className="vds-empty">Not shared with anyone yet.</div>
        ) : (
          <div className="vds-list">
            {sharedMembers.map((name, idx) => (
              <div className="vds-personRow" key={`${name}-${idx}`}>
                <div className="vds-avatar" aria-hidden="true">
                  {String(name).slice(0, 1).toUpperCase()}
                </div>
                <div className="vds-personMeta">
                  <div className="vds-personName">{name}</div>
                  <div className="vds-personHint">Member</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ flex: 1 }} />

      <div className="vds-divider" />

      <button
        type="button"
        className="vds-deleteBtn"
        onClick={() => setShowDeleteConfirm(true)}
        disabled={deleting}
        title="Delete vault"
      >
        <span className="vds-deleteIcon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path
              d="M9 3h6m0 0v-1.5a1.5 1.5 0 00-1.5-1.5h-3a1.5 1.5 0 00-1.5 1.5V3m0 0h8.25m0 0l-.75 13.5a2 2 0 01-2 1.84H6.75a2 2 0 01-2-1.84L4 3m4.5 6v6m3-6v6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span>Delete Vault</span>
      </button>

      {showDeleteConfirm &&
        createPortal(
          <div className="vds-deleteModal">
            <div className="vds-deleteContent">
              <div className="vds-deleteTitle">Delete Vault?</div>
              <div className="vds-deleteMessage">
                Are you sure you want to delete this vault? This action cannot
                be undone.
              </div>
              <div className="vds-deleteActions">
                <button
                  type="button"
                  className="vds-deleteCancel"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="vds-deleteConfirm"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
            <div
              className="vds-deleteBackdrop"
              onClick={() => !deleting && setShowDeleteConfirm(false)}
            />
          </div>,
          document.body
        )}
    </aside>
  );
}
