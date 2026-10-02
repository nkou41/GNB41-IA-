with open('src/App.tsx', 'r') as f:
    content = f.read()

old = "  if (!user && !showAuth) {"

new = '''  if (!user && publicPage && publicPage !== 'accueil') {
    const PublicNav = () => (
      <div className="public-navbar">
        <span className="public-navbar-logo" onClick={() => { setPublicPage(null); navigateTo('/'); }}>GNB41 IA</span>
        <div className="public-navbar-links">
          <span onClick={() => { setPublicPage(null); navigateTo('/'); }}>Accueil</span>
          <span onClick={() => { setPublicPage('fonctionnalites'); navigateTo('/fonctionnalites'); }}>Fonctionnalités</span>
          <span onClick={() => { setPublicPage('tarifs'); navigateTo('/tarifs'); }}>Tarifs</span>
          <span onClick={() => { setPublicPage('boutique'); api.listMarketplace().then((res) => setPublicListings(res.listings)).catch(() => {}); navigateTo('/boutique'); }}>Boutique</span>
          <span onClick={() => { setPublicPage('apropos'); navigateTo('/a-propos'); }}>À propos</span>
          <span onClick={() => { setPublicPage('contact'); navigateTo('/contact'); }}>Contact</span>
        </div>
        <button className="public-navbar-cta" onClick={() => { setPublicPage(null); setShowAuth(true); setAuthMode('login'); navigateTo('/'); }}>Se connecter</button>
      </div>
    );

    if (publicPage === 'fonctionnalites') {
      return (
        <div className="public-page">
          <PublicNav />
          <div className="public-page-content">
            <h1>Fonctionnalités</h1>
            <div className="landing-features" style={{ marginTop: '2rem' }}>
              <div className="feature-card">
                <h3>Génération IA multi-provider</h3>
                <p>Claude, GPT, Gemini ou Mistral : choisissez le modèle qui génère votre application a partir d'une simple description.</p>
              </div>
              <div className="feature-card">
                <h3>Éditeur de code intégré</h3>
                <p>Modifiez directement le code généré, fichier par fichier, sans quitter l'application.</p>
              </div>
              <div className="feature-card">
                <h3>Base de données automatique</h3>
                <p>Vos applications generees obtiennent automatiquement des tables de donnees et une cle API pour stocker de l'information.</p>
              </div>
              <div className="feature-card">
                <h3>Déploiement en un clic</h3>
                <p>Chaque application generee obtient instantanement une URL publique accessible partout.</p>
              </div>
              <div className="feature-card">
                <h3>Galerie de templates</h3>
                <p>Demarrez a partir d'une application deja creee par la communaute pour aller plus vite.</p>
              </div>
              <div className="feature-card">
                <h3>Boutique integree</h3>
                <p>Publiez et vendez vos applications directement sur la plateforme, avec paiement securise.</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (publicPage === 'tarifs') {
      return (
        <div className="public-page">
          <PublicNav />
          <div className="public-page-content">
            <h1>Tarifs</h1>
            <div className="plans-grid" style={{ marginTop: '2rem' }}>
              <div className="plan-card">
                <h3>Gratuit</h3>
                <p className="plan-price">0€<span>/mois</span></p>
                <ul>
                  <li>3 projets par espace de travail</li>
                  <li>1 espace de travail</li>
                  <li>Génération IA limitée</li>
                </ul>
                <button className="plan-btn" onClick={() => { setPublicPage(null); setShowAuth(true); setAuthMode('register'); navigateTo('/'); }}>Commencer</button>
              </div>
              <div className="plan-card plan-card-highlight">
                <span className="plan-badge">Populaire</span>
                <h3>Pro</h3>
                <p className="plan-price">19€<span>/mois</span></p>
                <ul>
                  <li>Projets illimités</li>
                  <li>Espaces de travail illimités</li>
                  <li>Génération IA prioritaire</li>
                </ul>
                <button className="plan-btn" onClick={() => { setPublicPage(null); setShowAuth(true); setAuthMode('register'); navigateTo('/'); }}>Commencer</button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (publicPage === 'apropos') {
      return (
        <div className="public-page">
          <PublicNav />
          <div className="public-page-content">
            <h1>À propos</h1>
            <p style={{ marginTop: '1rem', lineHeight: 1.7, maxWidth: '600px' }}>
              GNB41 IA est une plateforme de generation d'applications par intelligence artificielle.
              Decrivez votre idee en langage naturel, et obtenez une application complete, professionnelle
              et prete a etre deployee — sans avoir a ecrire une seule ligne de code.
            </p>
          </div>
        </div>
      );
    }

    if (publicPage === 'contact') {
      return (
        <div className="public-page">
          <PublicNav />
          <div className="public-page-content">
            <h1>Contact</h1>
            <p style={{ marginTop: '1rem' }}>Pour toute question, ecrivez-nous a :</p>
            <p style={{ fontWeight: 600, marginTop: '0.5rem' }}>contact@gnb41ia.com</p>
          </div>
        </div>
      );
    }

    if (publicPage === 'boutique') {
      return (
        <div className="public-page">
          <PublicNav />
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
  }

  if (!user && !showAuth) {'''

if old in content:
    content = content.replace(old, new)
    with open('src/App.tsx', 'w') as f:
        f.write(content)
    print("OK: pages publiques ajoutees")
else:
    print("ERREUR: marker landing non trouve")
