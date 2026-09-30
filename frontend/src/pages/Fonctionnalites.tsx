import PublicNav from '../components/PublicNav';

const FONCTIONNALITES = [
  { titre: 'Génération IA multi-provider', texte: "Claude, GPT, Gemini ou Mistral : choisissez le modèle qui génère votre application à partir d'une simple description." },
  { titre: 'Éditeur de code intégré', texte: "Modifiez directement le code généré, fichier par fichier, sans quitter l'application." },
  { titre: 'Base de données automatique', texte: "Vos applications générées obtiennent automatiquement des tables de données et une clé API pour stocker de l'information." },
  { titre: 'Déploiement en un clic', texte: "Chaque application générée obtient instantanément une URL publique accessible partout." },
  { titre: 'Galerie de templates', texte: "Démarrez à partir d'une application déjà créée par la communauté pour aller plus vite." },
  { titre: 'Boutique intégrée', texte: "Publiez et vendez vos applications directement sur la plateforme, avec paiement sécurisé." },
];

export default function Fonctionnalites({ navProps }: { navProps: any }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Fonctionnalités</h1>
        <div className="fx-grid">
          {FONCTIONNALITES.map((f, i) => (
            <div key={f.titre} className="fx-card">
              <span className="fx-num">{String(i + 1).padStart(2, '0')}</span>
              <h3>{f.titre}</h3>
              <p>{f.texte}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
