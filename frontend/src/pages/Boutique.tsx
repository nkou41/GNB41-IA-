import PublicNav from '../components/PublicNav';

export default function Boutique({ navProps, publicListings }: { navProps: any; publicListings: any[] }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Boutique</h1>
        <p style={{ marginTop: '0.5rem', color: '#8a7f68' }}>Connectez-vous pour acheter ou publier une application.</p>
        {publicListings.length === 0 ? (
          <div className="marketplace-empty"><p>Aucune application publiee pour le moment.</p></div>
        ) : (
          <div className="marketplace-grid" style={{ marginTop: '1.5rem' }}>
            {publicListings.map((l: any) => (
              <div key={l.id} className="marketplace-card">
                <h3>{l.titre}</h3>
                <p className="marketplace-card-desc">{l.description}</p>
                <div className="marketplace-card-footer">
                  <span className="marketplace-price">{(l.prix_centimes / 100).toFixed(2)} {l.devise}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
