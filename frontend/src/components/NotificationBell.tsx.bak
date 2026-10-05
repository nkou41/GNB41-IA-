import { useEffect, useState, useRef } from 'react';
import { Bell } from 'lucide-react';
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

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [nonLues, setNonLues] = useState(0);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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
    socket.on('notification', (notif: Notification) => {
      setNotifications((prev) => [notif, ...prev]);
      setNonLues((prev) => prev + 1);
    });

    return () => {
      socket.off('notification');
    };
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const marquerLu = async (id: number) => {
    try {
      await fetch(`${API_BASE}/notifications/${id}/lu`, {
        method: 'POST',
        credentials: 'include',
      });
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, lu: true } : n))
      );
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

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-full hover:bg-gray-100"
      >
        <Bell size={22} />
        {nonLues > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {nonLues > 9 ? '9+' : nonLues}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white shadow-lg rounded-lg border border-gray-200 max-h-96 overflow-y-auto z-50">
          <div className="flex justify-between items-center p-3 border-b">
            <span className="font-semibold">Notifications</span>
            {nonLues > 0 && (
              <button onClick={toutMarquerLu} className="text-sm text-blue-600 hover:underline">
                Tout marquer comme lu
              </button>
            )}
          </div>
          {notifications.length === 0 ? (
            <div className="p-4 text-gray-500 text-sm text-center">Aucune notification</div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                onClick={() => !n.lu && marquerLu(n.id)}
                className={`p-3 border-b cursor-pointer hover:bg-gray-50 ${!n.lu ? 'bg-blue-50' : ''}`}
              >
                <div className="font-medium text-sm">{n.titre}</div>
                <div className="text-sm text-gray-600">{n.message}</div>
                <div className="text-xs text-gray-400 mt-1">
                  {new Date(n.created_at).toLocaleString('fr-FR')}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
