import PublicNav from '../components/PublicNav';

export default function Boutique({ navProps, publicListings }: { navProps: any; publicListings: any[] }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Boutique</h1>
        <p className="shop-sub">Connectez-vous pour acheter ou publier une application.</p>
        {publicListings.length === 0 ? (
          <div className="shop-empty"><p>Aucune application publiée pour le moment.</p></div>
        ) : (
          <div className="shop-grid">
            {publicListings.map((l: any) => (
              <article key={l.id} className="shop-card">
                <div className="shop-thumb" aria-hidden="true">
                  <span>{String(l.titre || '?').trim().charAt(0).toUpperCase()}</span>
                </div>
                <div className="shop-body">
                  <h3 className="shop-title">{l.titre}</h3>
                  {l.description && <p className="shop-desc">{l.description}</p>}
                  <div className="shop-foot">
                    <span className="shop-price">{(l.prix_centimes / 100).toFixed(2)} {l.devise}</span>
                    <button type="button" className="shop-buy" onClick={() => { navProps.setPublicPage(null); navProps.setShowAuth(true); navProps.setAuthMode('register'); navProps.navigateTo('/'); }}>
                      Acheter
                    </button>
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
