import { useCallback, useEffect, useState } from 'react';
import {
  disablePush, enablePush, pushStatus, sendTestPush, type PushStatus,
} from '../lib/push';
import './Preferences.css';

const AIDE: Record<string, string> = {
  denied:
    "Les notifications sont bloquées pour ce site. Dans Chrome : touchez ⋮ puis Paramètres, Paramètres du site, Notifications, et autorisez ce site. Revenez ensuite ici.",
  'ios-install':
    "Sur iPhone, ajoutez d'abord le site à l'écran d'accueil (Partager puis « Sur l'écran d'accueil »), puis rouvrez-le depuis son icône.",
  unsupported:
    "Ce navigateur ne permet pas les notifications hors de l'application. Essayez avec Chrome.",
};

export default function PushToggle() {
  const [status, setStatus] = useState<PushStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const refresh = useCallback(
    () => pushStatus().then(setStatus).catch(() => setStatus('unsupported')),
    []
  );
  useEffect(() => { refresh(); }, [refresh]);

  const run = async (fn: () => Promise<void>, ok: string) => {
    setBusy(true);
    setMsg('');
    try {
      await fn();
      setMsg(ok);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : 'Une erreur est survenue.');
    } finally {
      await refresh();
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
      {status === null && <div className="pf-hint">Vérification…</div>}
      {status && AIDE[status] && <div className="pf-hint">{AIDE[status]}</div>}
      {(status === 'available' || status === 'enabled') && (
        <>
          <div className="pf-hint">
            {status === 'enabled'
              ? 'Les notifications sont activées sur cet appareil.'
              : "Recevez vos notifications (annonces, ventes…) même quand l'application est fermée."}
          </div>
          <div className="pf-actions">
            {status === 'available' ? (
              <button className="pf-btn" disabled={busy}
                onClick={() => run(enablePush, 'Notifications activées sur cet appareil.')}>
                Activer les notifications
              </button>
            ) : (
              <>
                <button className="pf-btn" disabled={busy}
                  onClick={() => run(disablePush, 'Notifications désactivées sur cet appareil.')}>
                  Désactiver
                </button>
                <button className="pf-btn pf-btn-soft" disabled={busy} onClick={test}>
                  Envoyer un test
                </button>
              </>
            )}
          </div>
        </>
      )}
      {msg && <div className="pf-hint">{msg}</div>}
    </div>
  );
}
