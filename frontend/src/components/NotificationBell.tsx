import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  ArrowLeft, Bell, BellOff, CheckCheck, CheckCircle2, Clock, Search, XCircle,
} from 'lucide-react';
import { getSocket } from '../socket';
import './NotificationBell.css';

interface Notification {
  id: number;
  type: string;
  titre: string;
  message: string;
  lien: string | null;
  lu: boolean;
  created_at: string;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

type Kind = 'pending' | 'review' | 'rejected' | 'approved' | 'info';

function kindOf(n: Notification): Kind {
  const s = `${n.type} ${n.titre}`.toLowerCase();
  if (/refus|rejet/.test(s)) return 'rejected';
  if (/accept|approuv|publi|valid/.test(s)) return 'approved';
  if (/examiner/.test(s)) return 'review';
  if (/cours|attente|examen/.test(s)) return 'pending';
  return 'info';
}

const ICONS = {
  pending: Clock,
  review: Search,
  rejected: XCircle,
  approved: CheckCircle2,
  info: Bell,
};

function relatif(iso: string) {
  const d = new Date(iso);
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return "À l'instant";
  if (s < 3600) return `Il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `Il y a ${Math.floor(s / 3600)} h`;
  if (s < 172800) return 'Hier';
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

const estAujourdhui = (iso: string) =>
  new Date(iso).toDateString() === new Date().toDateString();

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [nonLues, setNonLues] = useState(0);
  const [open, setOpen] = useState(false);
  const [filtre, setFiltre] = useState<'all' | 'unread'>('all');

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API_BASE}/notifications`, { credentials: 'include' });
      if (!res.ok) return;
      const data = await res.json();
      setNotifications(data.notifications);
      setNonLues(data.non_lues);
    } catch (e) {
      console.error('Erreur chargement notifications', e);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const socket = getSocket();
    const onNotif = (notif: Notification) => {
      setNotifications((prev) => [notif, ...prev]);
      setNonLues((prev) => prev + 1);
    };
    socket.on('notification', onNotif);
    return () => {
      socket.off('notification', onNotif);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const marquerLu = async (id: number) => {
    try {
      await fetch(`${API_BASE}/notifications/${id}/lu`, {
        method: 'POST',
        credentials: 'include',
      });
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, lu: true } : n)));
      setNonLues((prev) => Math.max(0, prev - 1));
    } catch (e) {
      console.error('Erreur marquage notification', e);
    }
  };

  const toutMarquerLu = async () => {
    try {
      await fetch(`${API_BASE}/notifications/tout-lire`, {
        method: 'POST',
        credentials: 'include',
      });
      setNotifications((prev) => prev.map((n) => ({ ...n, lu: true })));
      setNonLues(0);
    } catch (e) {
      console.error('Erreur marquage global', e);
    }
  };

  const ouvrir = async (n: Notification) => {
    if (!n.lu) await marquerLu(n.id);
    if (n.lien) {
      setOpen(false);
      window.location.assign(n.lien);
    }
  };

  const affichees = useMemo(
    () =>
      notifications
        .filter((n) => filtre === 'all' || !n.lu)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [notifications, filtre]
  );
  const aujourdhui = affichees.filter((n) => estAujourdhui(n.created_at));
  const avant = affichees.filter((n) => !estAujourdhui(n.created_at));

  const carte = (n: Notification) => {
    const kind = kindOf(n);
    const Icon = ICONS[kind];
    return (
      <button
        key={n.id}
        onClick={() => ouvrir(n)}
        className={`nb-card nb-${kind}${n.lu ? '' : ' is-unread'}`}
      >
        <span className="nb-ico"><Icon size={22} /></span>
        <span className="nb-text">
          <span className="nb-row">
            <span className="nb-card-title">{n.titre}</span>
            <span className="nb-time">{relatif(n.created_at)}</span>
          </span>
          <span className="nb-msg">{n.message}</span>
        </span>
        {!n.lu && <span className="nb-dot" />}
      </button>
    );
  };

  const groupe = (titre: string, items: Notification[]) =>
    items.length > 0 && (
      <section>
        <h3 className="nb-group">{titre}</h3>
        <div className="nb-list">{items.map(carte)}</div>
      </section>
    );

  const panneau = (
    <div className="nb-overlay" onClick={() => setOpen(false)}>
      <div className="nb-panel" onClick={(e) => e.stopPropagation()}>
        <header className="nb-header">
          <div className="nb-bar">
            <button className="nb-back" onClick={() => setOpen(false)} aria-label="Fermer">
              <ArrowLeft size={20} />
            </button>
            <h2 className="nb-title">
              Notifications
              {nonLues > 0 && <span className="nb-count">{nonLues}</span>}
            </h2>
            <button className="nb-readall" onClick={toutMarquerLu} disabled={nonLues === 0}>
              <CheckCheck size={16} /> Tout lire
            </button>
          </div>
          <div className="nb-tabs">
            {(['all', 'unread'] as const).map((f) => (
              <button
                key={f}
                className={`nb-tab${filtre === f ? ' is-active' : ''}`}
                onClick={() => setFiltre(f)}
              >
                {f === 'all' ? 'Toutes' : 'Non lues'}
              </button>
            ))}
          </div>
        </header>

        <main className="nb-main">
          {affichees.length === 0 ? (
            <div className="nb-empty">
              <div className="nb-empty-ico"><BellOff size={38} /></div>
              <h3>Aucune notification</h3>
              <p>
                {filtre === 'unread'
                  ? 'Tout est à jour.'
                  : "Vous serez prévenu ici dès qu'il y a du nouveau."}
              </p>
            </div>
          ) : (
            <>
              {groupe("Aujourd'hui", aujourdhui)}
              {groupe('Plus tôt', avant)}
            </>
          )}
        </main>
      </div>
    </div>
  );

  return (
    <>
      <button className="nb-bell" onClick={() => setOpen(true)} aria-label="Notifications">
        <Bell size={22} />
        {nonLues > 0 && <span className="nb-badge">{nonLues > 9 ? '9+' : nonLues}</span>}
      </button>
      {open && createPortal(panneau, document.body)}
    </>
  );
}
