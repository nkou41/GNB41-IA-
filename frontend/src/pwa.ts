import { useSyncExternalStore } from 'react';
import { registerSW } from 'virtual:pwa-register';

let needRefresh = false;
let updater: ((reload?: boolean) => Promise<void>) | null = null;
const listeners = new Set<() => void>();

export function initPwa() {
  updater = registerSW({
    immediate: true,
    onNeedRefresh() {
      needRefresh = true;
      listeners.forEach((l) => l());
    },
  });
}

export function applyUpdate() {
  if (updater) updater(true);
}

export const useNeedRefresh = () =>
  useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => needRefresh
  );
