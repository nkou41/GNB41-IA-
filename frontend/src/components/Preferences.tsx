import { useEffect, useState } from 'react';
import {
  COUNTRIES, deviceTimeZone, formatDate, formatTime,
  getTimeZonePref, setTimeZonePref, useTimeZone,
} from '../lib/time';
import {
  BACKGROUNDS, setBgPref, setThemePref, useBgPref, useThemePref, type Theme,
} from '../lib/prefs';
import './Preferences.css';

const THEMES: { id: Theme; nom: string }[] = [
  { id: 'light', nom: 'Clair' },
  { id: 'dark', nom: 'Sombre' },
  { id: 'auto', nom: 'Automatique' },
];

export default function Preferences() {
  const tz = useTimeZone();
  const pref = getTimeZonePref();
  const theme = useThemePref();
  const bg = useBgPref();
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="pf-card">
      <h3 className="pf-title">Apparence et région</h3>

      <div className="pf-label">Pays / fuseau horaire</div>
      <select
        className="pf-select"
        value={pref}
        onChange={(e) => setTimeZonePref(e.target.value)}
      >
        <option value="auto">Automatique ({deviceTimeZone()})</option>
        {COUNTRIES.map((c) => (
          <option key={c.tz} value={c.tz}>{c.nom}</option>
        ))}
      </select>
      <div className="pf-hint">
        Heure actuelle : {formatTime(now)} le {formatDate(now)} ({tz})
      </div>

      <div className="pf-label">Thème</div>
      <div className="pf-seg">
        {THEMES.map((t) => (
          <button
            key={t.id}
            className={`pf-seg-btn${theme === t.id ? ' is-active' : ''}`}
            onClick={() => setThemePref(t.id)}
          >
            {t.nom}
          </button>
        ))}
      </div>

      <div className="pf-label">Fond d'écran (thème clair)</div>
      <div className="pf-swatches">
        {BACKGROUNDS.map((b) => (
          <button
            key={b.id}
            className={`pf-swatch${bg === b.id ? ' is-active' : ''}`}
            onClick={() => setBgPref(b.id)}
            aria-label={b.nom}
          >
            <span className="pf-swatch-color" style={{ background: b.css || '#f7f5f0' }} />
            <span className="pf-swatch-name">{b.nom}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
