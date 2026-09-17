import PublicNav from '../components/PublicNav';

export default function Tarifs({ navProps, plansList }: { navProps: any; plansList: any[] }) {
  const { setPublicPage, setShowAuth, setAuthMode, navigateTo } = navProps;
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Tarifs</h1>
        <div className="plans-grid" style={{ marginTop: '2rem' }}>
          {plansList.map((p: any) => (
            <div key={p.id} className={`plan-card ${p.populaire ? 'plan-card-highlight' : ''}`}>
              {p.populaire && <span className="plan-badge">Populaire</span>}
              <h3>{p.nom}</h3>
              <p className="plan-price">
                {p.sur_devis ? 'Sur devis' : `${p.prix_usd}$`}
                {!p.sur_devis && <span>/mois</span>}
              </p>
              {!p.sur_devis && p.credits != null && (
                <p className="plan-credits">{p.credits} crédits de génération</p>
              )}
              <ul>
                {(p.features || []).map((f: string, i: number) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
              <button className="plan-btn" onClick={() => { setPublicPage(null); setShowAuth(true); setAuthMode('register'); navigateTo('/'); }}>
                {p.sur_devis ? 'Nous contacter' : 'Commencer'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
