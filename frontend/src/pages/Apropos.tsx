import PublicNav from '../components/PublicNav';

export default function Apropos({ navProps }: { navProps: any }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
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
