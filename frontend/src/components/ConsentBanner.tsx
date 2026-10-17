import { useState } from 'react';
import { analyticsConfigured, getConsent, setConsent } from '../analytics';
import './ConsentBanner.css';

export default function ConsentBanner() {
  const [visible, setVisible] = useState(() => analyticsConfigured() && getConsent() === null);
  if (!visible) return null;

  const choisir = (c: 'accepted' | 'refused') => {
    setConsent(c);
    setVisible(false);
  };

  return (
    <div className="cb-bar" role="dialog" aria-label="Mesure d'audience">
      <div className="cb-text">
        <b>Mesure d'audience</b>
        <span>
          Acceptez-vous que nous mesurions les pages consultées pour améliorer GNB41 IA ? Rien n'est collecté sans votre accord.
        </span>
      </div>
      <div className="cb-actions">
        <button className="cb-refuse" onClick={() => choisir('refused')}>Refuser</button>
        <button className="cb-accept" onClick={() => choisir('accepted')}>Accepter</button>
      </div>
    </div>
  );
}
