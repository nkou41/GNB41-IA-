import posthog from 'posthog-js';

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || '';
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';
let actif = false;

export function initAnalytics() {
  if (!POSTHOG_KEY) {
    console.warn('PostHog non configure (VITE_POSTHOG_KEY manquante)');
    return;
  }
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: true,
    capture_pageleave: true,
  });
  actif = true;
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
