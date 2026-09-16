import PublicNav from '../components/PublicNav';

export default function Fonctionnalites({ navProps }: { navProps: any }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
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
