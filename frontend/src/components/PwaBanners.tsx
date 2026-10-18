import { useEffect, useState } from 'react';
import { applyUpdate, useNeedRefresh } from '../pwa';
import './PwaBanners.css';

export default function PwaBanners() {
  const needRefresh = useNeedRefresh();
  const [online, setOnline] = useState(() => navigator.onLine);
  const [back, setBack] = useState(false);

  useEffect(() => {
    let timer: number | undefined;
    const off = () => { setOnline(false); setBack(false); };
    const on = () => {
      setOnline(true);
      setBack(true);
      timer = window.setTimeout(() => setBack(false), 8000);
    };
    window.addEventListener('offline', off);
    window.addEventListener('online', on);
    return () => {
      window.removeEventListener('offline', off);
      window.removeEventListener('online', on);
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  return (
    <>
      {!online && <div className="pw-pill pw-off" role="status">Hors connexion</div>}
      {online && back && (
        <div className="pw-pill pw-on" role="status">
          De retour en ligne <button onClick={() => window.location.reload()}>Actualiser</button>
        </div>
      )}
      {needRefresh && (
        <div className="pw-toast" role="alert">
          <span>Nouvelle version disponible</span>
          <button onClick={applyUpdate}>Mettre à jour</button>
        </div>
      )}
    </>
  );
}
