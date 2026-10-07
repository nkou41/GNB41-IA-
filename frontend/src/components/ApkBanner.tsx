import { useEffect, useState } from 'react';
import './ApkBanner.css';

const KEY = 'gnb41_apk_banner';

function dismissed(): boolean {
  try {
    const v = localStorage.getItem(KEY);
    return !!v && Date.now() < Number(v);
  } catch {
    return false;
  }
}

export default function ApkBanner() {
  const [info, setInfo] = useState<{ version: string; size: number } | null>(null);

  useEffect(() => {
    if (!/android/i.test(navigator.userAgent)) return;
    if (window.matchMedia('(display-mode: standalone)').matches) return;
    if (window.matchMedia('(display-mode: fullscreen)').matches) return;
    if (document.referrer.startsWith('android-app://')) return;
    if (dismissed()) return;
    fetch('/apk-version.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setInfo)
      .catch(() => {});
  }, []);

  if (!info) return null;

  const fermer = () => {
    try {
      localStorage.setItem(KEY, String(Date.now() + 14 * 86400000));
    } catch {
      /* stockage indisponible */
    }
    setInfo(null);
  };
  const mo = (info.size / 1048576).toFixed(1).replace('.', ',');

  return (
    <div className="ab-bar" role="region" aria-label="Application Android">
      <img className="ab-logo" src="/android-chrome-192x192.png" alt="" />
      <div className="ab-text">
        <div className="ab-title">Application GNB41 IA</div>
        <div className="ab-sub">Android · {mo} Mo · v{info.version}</div>
      </div>
      <a className="ab-btn" href="/telecharger/">Installer</a>
      <button className="ab-close" onClick={fermer} aria-label="Fermer">×</button>
    </div>
  );
}
