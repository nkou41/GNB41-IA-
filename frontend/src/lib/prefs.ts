import { useSyncExternalStore } from 'react';

export type Theme = 'light' | 'dark' | 'auto';

const THEME_KEY = 'theme';
const BG_KEY = 'gnb41_bg';
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

export const BACKGROUNDS = [
  { id: 'default', nom: 'Par défaut', css: '' },
  { id: 'ciel', nom: 'Ciel', css: 'linear-gradient(160deg,#e0f2fe,#f0f9ff)' },
  { id: 'menthe', nom: 'Menthe', css: 'linear-gradient(160deg,#dcfce7,#f0fdf4)' },
  { id: 'lavande', nom: 'Lavande', css: 'linear-gradient(160deg,#ede9fe,#f5f3ff)' },
  { id: 'peche', nom: 'Pêche', css: 'linear-gradient(160deg,#ffedd5,#fff7ed)' },
  { id: 'rose', nom: 'Rose', css: 'linear-gradient(160deg,#fce7f3,#fdf2f8)' },
  { id: 'ardoise', nom: 'Ardoise', css: '#e2e8f0' },
];

export function getThemePref(): Theme {
  const v = read(THEME_KEY);
  return v === 'dark' || v === 'auto' ? v : 'light';
}
export function getBgPref(): string {
  return read(BG_KEY) || 'default';
}

export function isDarkNow(): boolean {
  const t = getThemePref();
  if (t === 'dark') return true;
  if (t === 'auto') return window.matchMedia('(prefers-color-scheme: dark)').matches;
  return false;
}

export function applyAppearance() {
  const dark = isDarkNow();
  document.body.classList.toggle('dark-mode', dark);
  const bg = BACKGROUNDS.find((b) => b.id === getBgPref());
  if (!dark && bg && bg.css) {
    document.body.style.background = bg.css;
    document.body.style.backgroundAttachment = 'fixed';
  } else {
    document.body.style.background = '';
  }
}

export function setThemePref(t: Theme) {
  write(THEME_KEY, t);
  applyAppearance();
  emit();
}
export function setBgPref(id: string) {
  write(BG_KEY, id === 'default' ? null : id);
  applyAppearance();
  emit();
}

const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};
export const useThemePref = () => useSyncExternalStore(subscribe, getThemePref);
export const useBgPref = () => useSyncExternalStore(subscribe, getBgPref);

if (typeof window !== 'undefined') {
  applyAppearance();
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (getThemePref() === 'auto') { applyAppearance(); emit(); }
  });
}
