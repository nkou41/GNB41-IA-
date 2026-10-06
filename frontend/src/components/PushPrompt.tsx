import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Bell } from 'lucide-react';
import { enablePush, pushStatus, syncPush } from '../lib/push';
import './PushPrompt.css';

const KEY = 'gnb41_push_prompt';
let claimed = false;

function snoozed(): boolean {
  try {
    const v = localStorage.getItem(KEY);
    if (!v) return false;
    if (v === 'never') return true;
    return Date.now() < Number(v);
  } catch {
    return false;
  }
}
function snooze(days?: number) {
  try {
    localStorage.setItem(KEY, days ? String(Date.now() + days * 86400000) : 'never');
  } catch {
    /* stockage indisponible */
  }
}

export default function PushPrompt() {
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    if (claimed) return;
    claimed = true;
    let cancelled = false;
    let timer: number | undefined;
    (async () => {
      try {
        const st = await pushStatus();
        if (st === 'enabled') {
          await syncPush();
        } else if (st === 'available') {
          if (Notification.permission === 'granted') {
            await syncPush();
          } else if (!snoozed()) {
            timer = window.setTimeout(() => { if (!cancelled) setShow(true); }, 2500);
          }
        }
      } catch {
        /* silencieux : la demande n'est jamais bloquante */
      }
    })();
    return () => {
      cancelled = true;
      claimed = false;
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  if (!show) return null;

  const later = () => { snooze(7); setShow(false); };
  const never = () => { snooze(); setShow(false); };
  const activer = async () => {
    setBusy(true);
    setMsg('');
    try {
      await enablePush();
      setShow(false);
    } catch (e: unknown) {
      snooze(30);
      setMsg(e instanceof Error ? e.message : 'Activation impossible.');
      setBusy(false);
    }
  };

  return createPortal(
    <div className="pp-overlay" onClick={later}>
      <div className="pp-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="pp-ico"><Bell size={26} /></div>
        <div className="pp-title">Activer les notifications ?</div>
        <div className="pp-text">
          Soyez prévenu des ventes, des paiements et des décisions sur vos annonces, même quand l'application est fermée.
        </div>
        {msg && <div className="pp-error">{msg}</div>}
        <button className="pp-primary" onClick={activer} disabled={busy}>
          {busy ? 'Activation…' : 'Activer'}
        </button>
        <button className="pp-secondary" onClick={later} disabled={busy}>Plus tard</button>
        <button className="pp-link" onClick={never} disabled={busy}>Ne plus demander</button>
      </div>
    </div>,
    document.body
  );
}
