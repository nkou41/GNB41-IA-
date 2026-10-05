import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  ArrowLeft, Bell, BellOff, CheckCheck, CheckCircle2, Clock, Search, XCircle,
} from 'lucide-react';
import { getSocket } from '../socket';

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

const KINDS: Record<Kind, { icon: typeof Bell; box: string }> = {
  pending:  { icon: Clock,        box: 'bg-amber-100 text-amber-600' },
  review:   { icon: Search,       box: 'bg-blue-100 text-blue-600' },
  rejected: { icon: XCircle,      box: 'bg-red-100 text-red-600' },
  approved: { icon: CheckCircle2, box: 'bg-green-100 text-green-600' },
  info:     { icon: Bell,         box: 'bg-indigo-100 text-indigo-600' },
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

  // Bloque le défilement de la page derrière le panneau + touche Échap
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
    const { icon: Icon, box } = KINDS[kindOf(n)];
    return (
      <button
        key={n.id}
        onClick={() => ouvrir(n)}
        className={`relative flex w-full gap-3 rounded-2xl border p-3.5 text-left transition active:scale-[0.985] ${
          n.lu ? 'border-gray-200 bg-white' : 'border-indigo-200 bg-indigo-50/60'
        }`}
      >
        <span className={`flex h-11 w-11 flex-none items-center justify-center rounded-xl ${box}`}>
          <Icon size={22} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="text-[15px] font-bold leading-snug text-gray-900">{n.titre}</span>
            <span className={`whitespace-nowrap text-xs text-gray-500 ${n.lu ? '' : 'mr-4'}`}>
              {relatif(n.created_at)}
            </span>
          </span>
          <span className="mt-1 block break-words text-sm leading-relaxed text-gray-600">
            {n.message}
          </span>
        </span>
        {!n.lu && <span className="absolute right-3.5 top-3.5 h-2.5 w-2.5 rounded-full bg-indigo-500" />}
      </button>
    );
  };

  const groupe = (titre: string, items: Notification[]) =>
    items.length > 0 && (
      <section>
        <h3 className="mb-2 mt-5 px-1 text-xs font-bold uppercase tracking-wider text-gray-500">
          {titre}
        </h3>
        <div className="space-y-2.5">{items.map(carte)}</div>
      </section>
    );

  const panneau = (
    <div className="fixed inset-0 z-[100] bg-black/40" onClick={() => setOpen(false)}>
      <div
        className="absolute inset-0 flex flex-col bg-gray-50 md:inset-y-0 md:left-auto md:right-0 md:w-[420px] md:shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header
          className="border-b border-gray-200 bg-white px-4"
          style={{ paddingTop: 'env(safe-area-inset-top)' }}
        >
          <div className="flex h-14 items-center gap-3">
            <button
              onClick={() => setOpen(false)}
              aria-label="Fermer"
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"
            >
              <ArrowLeft size={20} />
            </button>
            <h2 className="flex-1 text-xl font-bold text-gray-900">
              Notifications
              {nonLues > 0 && (
                <span className="ml-2 inline-flex h-[22px] min-w-[22px] items-center justify-center rounded-full bg-indigo-500 px-2 align-middle text-xs font-bold text-white">
                  {nonLues}
                </span>
              )}
            </h2>
            <button
              onClick={toutMarquerLu}
              disabled={nonLues === 0}
              className="flex items-center gap-1 py-2 text-[13px] font-semibold text-indigo-600 disabled:opacity-40"
            >
              <CheckCheck size={16} /> Tout lire
            </button>
          </div>
          <div className="flex gap-2 pb-3">
            {(['all', 'unread'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFiltre(f)}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold ${
                  filtre === f ? 'bg-indigo-500 text-white' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {f === 'all' ? 'Toutes' : 'Non lues'}
              </button>
            ))}
          </div>
        </header>

        <main
          className="flex-1 overflow-y-auto px-4 pb-8"
          style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 32px)' }}
        >
          {affichees.length === 0 ? (
            <div className="px-6 py-20 text-center text-gray-500">
              <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-3xl bg-indigo-50 text-indigo-500">
                <BellOff size={38} />
              </div>
              <h3 className="mb-1 text-lg font-bold text-gray-900">Aucune notification</h3>
              <p className="text-sm">
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
      <button
        onClick={() => setOpen(true)}
        aria-label="Notifications"
        className="relative rounded-full p-2 hover:bg-gray-100"
      >
        <Bell size={22} />
        {nonLues > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs text-white">
            {nonLues > 9 ? '9+' : nonLues}
          </span>
        )}
      </button>
      {open && createPortal(panneau, document.body)}
    </>
  );
}
