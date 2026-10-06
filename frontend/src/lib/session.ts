import { useSyncExternalStore } from 'react';

let active = false;
const listeners = new Set<() => void>();

export function setSessionActive(v: boolean) {
  if (v === active) return;
  active = v;
  listeners.forEach((l) => l());
}

export const useSessionActive = () =>
  useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => active
  );
