import posthog from 'posthog-js';

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || '';
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';
const CONSENT_KEY = 'gnb41_analytics_consent';
let actif = false;

export type Consent = 'accepted' | 'refused' | null;

export function getConsent(): Consent {
  try {
    const v = localStorage.getItem(CONSENT_KEY);
    return v === 'accepted' || v === 'refused' ? v : null;
  } catch {
    return null;
  }
}

export const analyticsConfigured = () => !!POSTHOG_KEY;

function demarrer() {
  if (actif || !POSTHOG_KEY) return;
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: true,
    capture_pageleave: true,
  });
  actif = true;
}

// Rien n'est collecté tant que le visiteur n'a pas accepté.
export function initAnalytics() {
  if (getConsent() === 'accepted') demarrer();
}

export function setConsent(choix: 'accepted' | 'refused') {
  try {
    localStorage.setItem(CONSENT_KEY, choix);
  } catch {
    /* stockage indisponible */
  }
  if (choix === 'accepted') {
    demarrer();
    try { posthog.opt_in_capturing(); } catch { /* ignore */ }
  } else if (actif) {
    try {
      posthog.opt_out_capturing();
      posthog.reset();
    } catch { /* ignore */ }
    actif = false;
  }
}

export function identifyUser(userId: string, properties?: Record<string, any>) {
  if (!actif) return;
  posthog.identify(userId, properties);
}

export function trackEvent(eventName: string, properties?: Record<string, any>) {
  if (!actif) return;
  posthog.capture(eventName, properties);
}

export function resetAnalytics() {
  if (!actif) return;
  posthog.reset();
}

export default posthog;
