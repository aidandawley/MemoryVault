import React from "react";
import { useNavigate } from "react-router-dom";
import "../styles/LandingPage.css";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="lp-shell">
      <header className="lp-topbar">
        <div className="lp-brand">
          <div className="lp-logo">MV</div>
          <div className="lp-brandText">MemoryVault</div>
        </div>

        <div className="lp-topActions">
          <button className="lp-linkBtn" onClick={() => navigate("/vaults")}>
            Open Vaults
          </button>
          <button className="lp-primaryBtn" onClick={() => navigate("/vaults")}>
            Get Started
          </button>
        </div>
      </header>

      <main className="lp-main">
        <section className="lp-hero">
          <div className="lp-heroLeft">
            <div className="lp-pill">Media vaults, but smarter</div>

            <h1 className="lp-title">
              Your photos & videos,
              <br />
              organized into <span className="lp-accent">neat tags</span>.
            </h1>

            <p className="lp-subtitle">
              MemoryVault automatically groups what you upload into clean,
              searchable tags—so it’s super easy (and actually fun) to find
              moments again with friends or family.
            </p>

            <div className="lp-ctaRow">
              <button
                className="lp-primaryBtn"
                onClick={() => navigate("/vaults")}
              >
                Create a Vault
              </button>
              <button
                className="lp-secondaryBtn"
                onClick={() => navigate("/vaults")}
              >
                Explore Demo
              </button>
            </div>

            <div className="lp-micro">
              No messy albums. No endless scrolling. Just memories that make
              sense.
            </div>
          </div>

          <div className="lp-heroRight" aria-hidden="true">
            <div className="lp-phone">
              <div className="lp-phoneTop">
                <div className="lp-phoneDot" />
                <div className="lp-phoneDot" />
                <div className="lp-phoneDot" />
              </div>

              <div className="lp-card">
                <div className="lp-cardTitle">Weekend Trip</div>
                <div className="lp-cardMeta">Shared with 4</div>
                <div className="lp-tagRow">
                  <span className="lp-tag">#beach</span>
                  <span className="lp-tag">#food</span>
                  <span className="lp-tag">#sunset</span>
                </div>

                <div className="lp-grid">
                  <div className="lp-thumb" />
                  <div className="lp-thumb" />
                  <div className="lp-thumb" />
                  <div className="lp-thumb" />
                  <div className="lp-thumb" />
                  <div className="lp-thumb" />
                </div>
              </div>

              <div className="lp-searchCard">
                <div className="lp-searchLabel">Search by tag</div>
                <div className="lp-searchBar">
                  <div className="lp-searchIcon">⌕</div>
                  <div className="lp-searchText">#sunset</div>
                </div>
                <div className="lp-searchHint">
                  Instantly jump to every sunset clip, across the vault.
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="lp-diff">
          <div className="lp-diffInner">
            <div className="lp-diffLeft">
              <div className="lp-sectionKicker">Why it feels different</div>
              <h2 className="lp-diffTitle">
                Built for the way people actually relive memories.
              </h2>
              <p className="lp-diffText">
                Instead of dumping everything into endless albums, MemoryVault
                organizes your photos and videos into neat tags so you can
                explore moments by vibe and instantly find what you
                want—especially when you’re sharing a vault with friends or
                family.
              </p>

              <div className="lp-diffMiniList">
                <div className="lp-miniItem">
                  <span className="lp-miniDot" />
                  <span>Upload → tags appear automatically</span>
                </div>
                <div className="lp-miniItem">
                  <span className="lp-miniDot" />
                  <span>Tap a tag → jump through matching memories</span>
                </div>
                <div className="lp-miniItem">
                  <span className="lp-miniDot" />
                  <span>Share a vault → everyone gets the organized view</span>
                </div>
              </div>

              <div className="lp-diffCtaRow">
                <button
                  className="lp-primaryBtn"
                  onClick={() => navigate("/vaults")}
                >
                  Create a Vault
                </button>
                <button
                  className="lp-secondaryBtn"
                  onClick={() => navigate("/vaults")}
                >
                  Explore Demo
                </button>
              </div>
            </div>

            <div className="lp-diffRight">
              <div className="lp-panel">
                <div className="lp-panelTop">
                  <div className="lp-panelIcon">🏷️</div>
                  <div className="lp-panelTitle">Auto-tagged organization</div>
                </div>
                <div className="lp-panelText">
                  Upload anything and it lands in clean, meaningful tags. No
                  manual sorting, no messy album naming, no “where did I put
                  that?”.
                </div>

                <div className="lp-chipRow">
                  <span className="lp-chip">#beach</span>
                  <span className="lp-chip">#food</span>
                  <span className="lp-chip">#sunset</span>
                  <span className="lp-chip">#friends</span>
                </div>
              </div>

              <div className="lp-panel">
                <div className="lp-panelTop">
                  <div className="lp-panelIcon">🔎</div>
                  <div className="lp-panelTitle">
                    Search that’s actually fun
                  </div>
                </div>
                <div className="lp-panelText">
                  Instead of scrolling forever, you browse by tag and instantly
                  hop between the best matches. It feels like exploring, not
                  hunting.
                </div>

                <div className="lp-searchMock">
                  <div className="lp-searchMockLeft">⌕</div>
                  <div className="lp-searchMockText">Search: #sunset</div>
                  <div className="lp-searchMockPill">12</div>
                </div>
              </div>

              <div className="lp-panel">
                <div className="lp-panelTop">
                  <div className="lp-panelIcon">👥</div>
                  <div className="lp-panelTitle">Made for friends & family</div>
                </div>
                <div className="lp-panelText">
                  Share a vault and browse together. Everyone sees the same
                  organized tags so group memories stay easy to find for years.
                </div>

                <div className="lp-peopleRow">
                  <div className="lp-person">A</div>
                  <div className="lp-person">M</div>
                  <div className="lp-person">S</div>
                  <div className="lp-person">J</div>
                  <div className="lp-person lp-personPlus">+</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="lp-showcase">
          <div className="lp-showcaseHeader">
            <div className="lp-sectionKicker">Organized automatically</div>
            <h2 className="lp-showcaseTitle">
              Upload media. Get clean tags instantly.
            </h2>
            <p className="lp-showcaseText">
              Each upload is analyzed and grouped into neat tags so you can
              search moments fast with friends and family—no manual sorting, no
              chaos.
            </p>
          </div>

          <div className="lp-showcaseGrid">
            <div className="lp-vaultCard">
              <div className="lp-vaultCardTop">
                <div className="lp-vaultCardTitle">Dog Day</div>
                <div className="lp-vaultCardMeta">Auto-tags from the photo</div>
              </div>

              <div className="lp-vaultCardMedia">
                <img
                  className="lp-vaultCardImg"
                  src="https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=1800&q=80"
                  alt="Dog"
                  loading="lazy"
                />

                <div className="lp-vaultCardTagOverlay">
                  <span className="lp-tagChip">#dog</span>
                  <span className="lp-tagChip">#pet</span>
                  <span className="lp-tagChip">#cute</span>
                  <span className="lp-tagChip">#outdoors</span>
                  <span className="lp-tagChip">#portrait</span>
                </div>
              </div>
            </div>

            <div className="lp-vaultCard">
              <div className="lp-vaultCardTop">
                <div className="lp-vaultCardTitle">Concert Night</div>
                <div className="lp-vaultCardMeta">Auto-tags from the video</div>
              </div>

              <div className="lp-vaultCardMedia">
                <img
                  className="lp-vaultCardImg"
                  src="https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=1800&q=80"
                  alt="Concert"
                  loading="lazy"
                />

                <div className="lp-vaultCardTagOverlay">
                  <span className="lp-tagChip">#concert</span>
                  <span className="lp-tagChip">#music</span>
                  <span className="lp-tagChip">#stage</span>
                  <span className="lp-tagChip">#lights</span>
                  <span className="lp-tagChip">#crowd</span>
                </div>
              </div>
            </div>

            <div className="lp-vaultCard lp-vaultCardWide">
              <div className="lp-vaultCardTop">
                <div className="lp-vaultCardTitle">Golden Sunset</div>
                <div className="lp-vaultCardMeta">Auto-tags from the photo</div>
              </div>

              <div className="lp-vaultCardMedia">
                <img
                  className="lp-vaultCardImg"
                  src="https://images.unsplash.com/photo-1501973801540-537f08ccae7b?auto=format&fit=crop&w=2200&q=80"
                  alt="Sunset"
                  loading="lazy"
                />

                <div className="lp-vaultCardTagOverlay">
                  <span className="lp-tagChip">#sunset</span>
                  <span className="lp-tagChip">#goldenhour</span>
                  <span className="lp-tagChip">#sky</span>
                  <span className="lp-tagChip">#silhouette</span>
                  <span className="lp-tagChip">#landscape</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-footerInner">
          <div className="lp-footerBrand">MemoryVault</div>
          <div className="lp-footerNote">
            © {new Date().getFullYear()} MemoryVault
          </div>
        </div>
      </footer>
    </div>
  );
}
