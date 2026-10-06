const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

export const pushSupported = () =>
  typeof window !== 'undefined' &&
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window;

async function csrf(): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/csrf-token`, { credentials: 'include' });
  const data = await res.json();
  return data.csrf_token;
}

async function post(path: string, body?: unknown) {
  const token = await csrf();
  return fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
    body: body ? JSON.stringify(body) : undefined,
  });
}

function toBytes(b64: string): Uint8Array {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export async function isPushEnabled(): Promise<boolean> {
  if (!pushSupported() || Notification.permission !== 'granted') return false;
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return false;
  return !!(await reg.pushManager.getSubscription());
}

export async function enablePush(): Promise<void> {
  if (!pushSupported()) throw new Error("Ce navigateur ne gère pas les notifications.");
  const perm = await Notification.requestPermission();
  if (perm !== 'granted') throw new Error("Autorisation refusée dans les réglages du navigateur.");

  await navigator.serviceWorker.register('/sw.js');
  const reg = await navigator.serviceWorker.ready;

  const keyRes = await fetch(`${API_BASE}/push/public-key`, { credentials: 'include' });
  const { public_key } = await keyRes.json();
  if (!public_key) throw new Error("Les notifications ne sont pas encore configurées sur le serveur.");

  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: toBytes(public_key) as BufferSource,
    });
  }
  const res = await post('/push/subscribe', sub.toJSON());
  if (!res.ok) throw new Error("Impossible d'enregistrer cet appareil.");
}

export async function disablePush(): Promise<void> {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = reg ? await reg.pushManager.getSubscription() : null;
  if (sub) {
    await post('/push/unsubscribe', { endpoint: sub.endpoint });
    await sub.unsubscribe();
  }
}

export async function sendTestPush(): Promise<number> {
  const res = await post('/push/test');
  if (!res.ok) return 0;
  const data = await res.json();
  return data.sent || 0;
}

export type PushStatus = 'unsupported' | 'ios-install' | 'denied' | 'enabled' | 'available';

const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
const isStandalone = () =>
  window.matchMedia('(display-mode: standalone)').matches ||
  (navigator as unknown as { standalone?: boolean }).standalone === true;

export async function pushStatus(): Promise<PushStatus> {
  if (!pushSupported()) return isIOS() && !isStandalone() ? 'ios-install' : 'unsupported';
  if (Notification.permission === 'denied') return 'denied';
  if (await isPushEnabled()) return 'enabled';
  return 'available';
}

/** Réinscrit silencieusement cet appareil au nom de l'utilisateur connecté */
export async function syncPush(): Promise<void> {
  if (!pushSupported() || Notification.permission !== 'granted') return;
  await navigator.serviceWorker.register('/sw.js');
  const reg = await navigator.serviceWorker.ready;
  const keyRes = await fetch(`${API_BASE}/push/public-key`, { credentials: 'include' });
  const { public_key } = await keyRes.json();
  if (!public_key) return;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: toBytes(public_key) as BufferSource,
    });
  }
  await post('/push/subscribe', sub.toJSON());
}
