import PublicNav from '../components/PublicNav';

export default function Apropos({ navProps }: { navProps: any }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>À propos</h1>
        <p className="page-text">
          GNB41 IA est une plateforme de génération d'applications par intelligence artificielle.
          Décrivez votre idée en langage naturel, et obtenez une application complète, professionnelle
          et prête à être déployée, sans avoir à écrire une seule ligne de code.
        </p>
      </div>
    </div>
  );
}
