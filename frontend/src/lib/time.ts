import { useSyncExternalStore } from 'react';

const KEY = 'gnb41_timezone';

export const COUNTRIES: { nom: string; tz: string }[] = [
  { nom: 'Bénin', tz: 'Africa/Porto-Novo' },
  { nom: 'Togo', tz: 'Africa/Lome' },
  { nom: "Côte d'Ivoire", tz: 'Africa/Abidjan' },
  { nom: 'Sénégal', tz: 'Africa/Dakar' },
  { nom: 'Mali', tz: 'Africa/Bamako' },
  { nom: 'Burkina Faso', tz: 'Africa/Ouagadougou' },
  { nom: 'Niger', tz: 'Africa/Niamey' },
  { nom: 'Nigeria', tz: 'Africa/Lagos' },
  { nom: 'Ghana', tz: 'Africa/Accra' },
  { nom: 'Cameroun', tz: 'Africa/Douala' },
  { nom: 'Gabon', tz: 'Africa/Libreville' },
  { nom: 'Congo-Brazzaville', tz: 'Africa/Brazzaville' },
  { nom: 'RD Congo (Kinshasa)', tz: 'Africa/Kinshasa' },
  { nom: 'Guinée', tz: 'Africa/Conakry' },
  { nom: 'Maroc', tz: 'Africa/Casablanca' },
  { nom: 'Algérie', tz: 'Africa/Algiers' },
  { nom: 'Tunisie', tz: 'Africa/Tunis' },
  { nom: 'France', tz: 'Europe/Paris' },
  { nom: 'Belgique', tz: 'Europe/Brussels' },
  { nom: 'Suisse', tz: 'Europe/Zurich' },
  { nom: 'Royaume-Uni', tz: 'Europe/London' },
  { nom: 'Canada (Montréal)', tz: 'America/Toronto' },
  { nom: 'États-Unis (New York)', tz: 'America/New_York' },
  { nom: 'Chine', tz: 'Asia/Shanghai' },
];

const listeners = new Set<() => void>();

export function deviceTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

/** 'auto' (fuseau du téléphone) ou un fuseau IANA choisi par l'utilisateur */
export function getTimeZonePref(): string {
  try {
    return localStorage.getItem(KEY) || 'auto';
  } catch {
    return 'auto';
  }
}

export function getTimeZone(): string {
  const pref = getTimeZonePref();
  return pref === 'auto' ? deviceTimeZone() : pref;
}

export function setTimeZonePref(pref: string) {
  try {
    if (pref === 'auto') localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, pref);
  } catch {
    /* stockage indisponible */
  }
  listeners.forEach((l) => l());
}

/** À appeler dans un composant pour qu'il se mette à jour quand le fuseau change */
export function useTimeZone(): string {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    getTimeZone
  );
}

/** Les dates du serveur sont en UTC mais sans suffixe : on les lit comme de l'UTC */
export function parseServerDate(value: string | Date): Date {
  if (value instanceof Date) return value;
  let s = String(value).trim().replace(' ', 'T');
  if (s.length > 10 && !/(Z|[+-]\d{2}:?\d{2})$/i.test(s)) s += 'Z';
  return new Date(s);
}

function fmt(value: string | Date, opts: Intl.DateTimeFormatOptions): string {
  const d = parseServerDate(value);
  if (isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat('fr-FR', { timeZone: getTimeZone(), ...opts }).format(d);
}

export const formatDate = (v: string | Date) =>
  fmt(v, { day: '2-digit', month: '2-digit', year: 'numeric' });

export const formatTime = (v: string | Date) =>
  fmt(v, { hour: '2-digit', minute: '2-digit' });

export const formatDateTime = (v: string | Date) =>
  fmt(v, {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

const jour = (v: string | Date) =>
  fmt(v, { year: 'numeric', month: '2-digit', day: '2-digit' });

export const isToday = (v: string | Date) => jour(v) === jour(new Date());

export function formatRelative(v: string | Date): string {
  const d = parseServerDate(v);
  if (isNaN(d.getTime())) return '';
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return "À l'instant";
  if (s < 3600) return `Il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `Il y a ${Math.floor(s / 3600)} h`;
  if (s < 172800) return 'Hier';
  return fmt(d, { day: 'numeric', month: 'short' });
}

export const formatShortDateTime = (v: string | Date) =>
  fmt(v, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
