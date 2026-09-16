import PublicNav from '../components/PublicNav';

export default function Contact({ navProps }: { navProps: any }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Contact</h1>
        <p style={{ marginTop: '1rem' }}>Pour toute question, ecrivez-nous a :</p>
        <p style={{ fontWeight: 600, marginTop: '0.5rem' }}>contact@gnb41ia.com</p>
      </div>
    </div>
  );
}
