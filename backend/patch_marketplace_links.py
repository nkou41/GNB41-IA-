with open('src/App.tsx', 'r') as f:
    content = f.read()

old_grid = '''        {marketplaceListings.length === 0 ? (
          <div className="marketplace-empty">
            <p>Aucune application publiée pour le moment.</p>
          </div>
        ) : (
          <div className="marketplace-grid">
            {marketplaceListings.map((l) => (
              <div key={l.id} className="marketplace-card">
                <div className="marketplace-card-icon">{sourceIcon(l.source_type)}</div>
                <h3>{l.titre}</h3>
                <p className="marketplace-card-desc">{l.description}</p>
                <div className="marketplace-card-footer">
                  <span className="marketplace-price">{(l.prix_centimes / 100).toFixed(2)} {l.devise}</span>
                  <span className="marketplace-badge">{sourceLabel(l.source_type)}</span>
                </div>
              </div>
            ))}
          </div>
        )}'''

new_grid = '''        {marketplaceListings.length === 0 ? (
          <div className="marketplace-empty">
            <p>Aucune application publiée pour le moment.</p>
          </div>
        ) : (
          <div className="marketplace-grid">
            {marketplaceListings.map((l) => {
              const openLink = l.source_type === 'externe_lien' ? l.lien_externe : `http://localhost:5001/api/marketplace/${l.id}/preview`;
              const copyLink = () => {
                navigator.clipboard.writeText(openLink).catch(() => {});
              };
              return (
                <div key={l.id} className="marketplace-card">
                  <div className="marketplace-card-icon">
                    {l.favicon_url ? (
                      <img src={l.favicon_url} alt="" width="24" height="24" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    ) : sourceIcon(l.source_type)}
                  </div>
                  <h3>{l.titre}</h3>
                  <p className="marketplace-card-desc">{l.description}</p>
                  <div className="marketplace-card-footer">
                    <span className="marketplace-price">{(l.prix_centimes / 100).toFixed(2)} {l.devise}</span>
                    <span className="marketplace-badge">{sourceLabel(l.source_type)}</span>
                  </div>
                  {l.source_type !== 'externe_zip' && (
                    <div className="marketplace-card-links">
                      <a href={openLink} target="_blank" rel="noopener noreferrer" className="marketplace-link-btn">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                        Ouvrir
                      </a>
                      <button type="button" onClick={copyLink} className="marketplace-link-btn">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                        Copier
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}'''

if old_grid in content:
    content = content.replace(old_grid, new_grid)
    print("OK: grille avec liens et favicon ajoutee")
else:
    print("ERREUR: grille originale non trouvee")

with open('src/App.tsx', 'w') as f:
    f.write(content)
