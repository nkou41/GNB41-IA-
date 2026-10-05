import { useSyncExternalStore } from 'react';

export type Theme = 'light' | 'dark' | 'auto';

const THEME_KEY = 'theme';
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch { /* stockage indisponible */ }
}

export function getThemePref(): Theme {
  const v = read(THEME_KEY);
  return v === 'dark' || v === 'auto' ? v : 'light';
}

export function isDarkNow(): boolean {
  const t = getThemePref();
  if (t === 'dark') return true;
  if (t === 'auto') return window.matchMedia('(prefers-color-scheme: dark)').matches;
  return false;
}

export function applyAppearance() {
  document.body.classList.toggle('dark-mode', isDarkNow());
  document.body.style.background = '';
  document.body.style.backgroundAttachment = '';
}

export function setThemePref(t: Theme) {
  write(THEME_KEY, t);
  applyAppearance();
  emit();
}

const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};
export const useThemePref = () => useSyncExternalStore(subscribe, getThemePref);

if (typeof window !== 'undefined') {
  write('gnb41_bg', null); // nettoie l'ancien choix de fond
  applyAppearance();
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (getThemePref() === 'auto') { applyAppearance(); emit(); }
  });
}
