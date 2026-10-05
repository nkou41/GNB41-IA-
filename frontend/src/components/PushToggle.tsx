import { useEffect, useState } from 'react';
import {
  disablePush, enablePush, isPushEnabled, pushSupported, sendTestPush,
} from '../lib/push';
import './Preferences.css';

export default function PushToggle() {
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const supported = pushSupported();

  useEffect(() => {
    if (supported) isPushEnabled().then(setEnabled).catch(() => {});
  }, [supported]);

  const toggle = async () => {
    setBusy(true);
    setMsg('');
    try {
      if (enabled) {
        await disablePush();
        setEnabled(false);
        setMsg('Notifications désactivées sur cet appareil.');
      } else {
        await enablePush();
        setEnabled(true);
        setMsg('Notifications activées sur cet appareil.');
      }
    } catch (e: any) {
      setMsg(e?.message || 'Une erreur est survenue.');
    } finally {
      setBusy(false);
    }
  };

  const test = async () => {
    setBusy(true);
    setMsg('');
    const n = await sendTestPush().catch(() => 0);
    setMsg(n > 0
      ? 'Test envoyé. Fermez l’application : la notification arrive dans quelques secondes.'
      : "Aucun envoi réussi. Vérifiez la configuration du serveur.");
    setBusy(false);
  };

  return (
    <div className="pf-card">
      <h3 className="pf-title">Notifications sur l'appareil</h3>
      {!supported ? (
        <div className="pf-hint">Ce navigateur ne permet pas les notifications hors de l'application.</div>
      ) : (
        <>
          <div className="pf-hint">
            Recevez vos notifications (annonces, ventes…) même quand l'application est fermée.
          </div>
          <div className="pf-actions">
            <button className="pf-btn" onClick={toggle} disabled={busy}>
              {enabled ? 'Désactiver' : 'Activer les notifications'}
            </button>
            {enabled && (
              <button className="pf-btn pf-btn-soft" onClick={test} disabled={busy}>
                Envoyer un test
              </button>
            )}
          </div>
          {msg && <div className="pf-hint">{msg}</div>}
        </>
      )}
    </div>
  );
}
