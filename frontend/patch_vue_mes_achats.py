with open('src/App.tsx', 'r') as f:
    content = f.read()

old_marker = "  // Vue Mes ventes\n  if (showMesVentes) {"

new_view = '''  // Vue Mes achats
  if (showMesAchats) {
    const totalDepense = myPurchasesList.reduce((sum, p) => sum + p.prix_paye_centimes, 0);

    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <h1 onClick={() => setShowMesAchats(false)}>← Boutique</h1>
          <div className="marketplace-header-actions">
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>

        <div className="marketplace-title-row">
          <div>
            <h2>Mes achats</h2>
            <p>{myPurchasesList.length} achat{myPurchasesList.length !== 1 ? 's' : ''} · {(totalDepense / 100).toFixed(2)} EUR dépensés</p>
          </div>
        </div>

        {myPurchasesList.length === 0 ? (
          <div className="marketplace-empty">
            <p>Vous n'avez encore rien acheté.</p>
          </div>
        ) : (
          <div className="marketplace-grid">
            {myPurchasesList.map((p) => (
              <div key={p.id} className="marketplace-card">
                <div className="marketplace-card-footer">
                  <span className="marketplace-price">{(p.prix_paye_centimes / 100).toFixed(2)} EUR</span>
                  <span className="marketplace-badge">{p.statut}</span>
                </div>
                <p className="marketplace-card-desc">
                  Acheté le {new Date(p.created_at).toLocaleDateString('fr-FR')}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Vue Mes ventes
  if (showMesVentes) {'''

if old_marker in content:
    content = content.replace(old_marker, new_view)
    with open('src/App.tsx', 'w') as f:
        f.write(content)
    print("OK: vue Mes achats ajoutee")
else:
    print("ERREUR: marker Mes ventes non trouve")
