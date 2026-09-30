import PublicNav from '../components/PublicNav';

export default function Templates({ navProps, templatesList }: { navProps: any; templatesList: any[] }) {
  const inscrire = () => { navProps.setPublicPage(null); navProps.setShowAuth(true); navProps.setAuthMode('register'); navProps.navigateTo('/'); };
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Galerie de templates</h1>
        <p className="shop-sub">Connectez-vous pour utiliser un template comme base de votre projet.</p>
        {templatesList.length === 0 ? (
          <div className="shop-empty"><p>Aucun template disponible pour le moment.</p></div>
        ) : (
          <div className="shop-grid">
            {templatesList.map((t: any) => (
              <article key={t.id} className="shop-card">
                <div className="shop-thumb" aria-hidden="true">
                  <span>{String(t.nom || '?').trim().charAt(0).toUpperCase()}</span>
                </div>
                <div className="shop-body">
                  {t.categorie && <span className="shop-tag">{t.categorie}</span>}
                  <h3 className="shop-title">{t.nom}</h3>
                  {t.description && <p className="shop-desc">{t.description}</p>}
                  <div className="shop-foot">
                    <button type="button" className="shop-buy shop-buy-full" onClick={inscrire}>Utiliser ce template</button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
