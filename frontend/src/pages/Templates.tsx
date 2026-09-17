import PublicNav from '../components/PublicNav';

export default function Templates({ navProps, templatesList }: { navProps: any; templatesList: any[] }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Galerie de templates</h1>
        <p style={{ marginTop: '0.5rem', color: '#8a7f68' }}>Connectez-vous pour utiliser un template comme base de votre projet.</p>
        {templatesList.length === 0 ? (
          <div className="marketplace-empty"><p>Aucun template disponible pour le moment.</p></div>
        ) : (
          <div className="marketplace-grid" style={{ marginTop: '1.5rem' }}>
            {templatesList.map((t: any) => (
              <div key={t.id} className="marketplace-card">
                <h3>{t.nom}</h3>
                <p className="marketplace-card-desc">{t.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
