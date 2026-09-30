import PublicNav from '../components/PublicNav';

export default function Contact({ navProps }: { navProps: any }) {
  return (
    <div className="public-page">
      <PublicNav {...navProps} />
      <div className="public-page-content">
        <h1>Contact</h1>
        <div className="contact-card">
          <p>Pour toute question, écrivez-nous à :</p>
          <a className="shop-buy contact-mail" href="mailto:contact@gnb41ia.com">contact@gnb41ia.com</a>
        </div>
      </div>
    </div>
  );
}
