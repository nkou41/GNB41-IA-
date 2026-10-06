import { useEffect, useState } from 'react';
import { fetchCategories, saveCategory, type NotifCategory } from '../lib/notifPrefs';
import './Preferences.css';

export default function NotificationPrefs() {
  const [cats, setCats] = useState<NotifCategory[]>([]);
  const [msg, setMsg] = useState('');
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetchCategories()
      .then((c) => { setCats(c); setLoaded(true); })
      .catch(() => { setMsg('Impossible de charger vos préférences.'); setLoaded(true); });
  }, []);

  const toggle = async (c: NotifCategory) => {
    const active = !c.active;
    setMsg('');
    setCats((prev) => prev.map((x) => (x.id === c.id ? { ...x, active } : x)));
    try {
      await saveCategory(c.id, active);
    } catch {
      setCats((prev) => prev.map((x) => (x.id === c.id ? { ...x, active: !active } : x)));
      setMsg("L'enregistrement a échoué. Réessayez.");
    }
  };

  if (loaded && cats.length === 0 && !msg) return null;

  return (
    <div className="pf-card">
      <h3 className="pf-title">Types de notifications</h3>
      <div className="pf-hint">
        Choisissez ce que vous voulez recevoir. Une catégorie désactivée ne produit plus aucune notification.
      </div>
      {cats.map((c) => (
        <div className="pf-row" key={c.id}>
          <div className="pf-row-text">
            <div className="pf-row-label">{c.label}</div>
            <div className="pf-row-desc">{c.description}</div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={c.active}
            aria-label={c.label}
            className={`pf-switch${c.active ? ' is-on' : ''}`}
            onClick={() => toggle(c)}
          >
            <span className="pf-switch-knob" />
          </button>
        </div>
      ))}
      {msg && <div className="pf-hint">{msg}</div>}
    </div>
  );
}
