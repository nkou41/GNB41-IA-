import { useTimeZone } from './time';

const PAR_FUSEAU: Record<string, string> = {
  'Africa/Porto-Novo': 'XOF', 'Africa/Lome': 'XOF', 'Africa/Abidjan': 'XOF', 'Africa/Dakar': 'XOF',
  'Africa/Bamako': 'XOF', 'Africa/Ouagadougou': 'XOF', 'Africa/Niamey': 'XOF', 'Africa/Bissau': 'XOF',
  'Africa/Douala': 'XAF', 'Africa/Libreville': 'XAF', 'Africa/Brazzaville': 'XAF',
  'Africa/Lagos': 'NGN', 'Africa/Accra': 'GHS', 'Africa/Conakry': 'GNF', 'Africa/Kinshasa': 'CDF',
  'Africa/Casablanca': 'MAD', 'Africa/Algiers': 'DZD', 'Africa/Tunis': 'TND',
  'Europe/Paris': 'EUR', 'Europe/Brussels': 'EUR', 'Europe/Zurich': 'CHF', 'Europe/London': 'GBP',
  'America/Toronto': 'CAD', 'America/New_York': 'USD', 'Asia/Shanghai': 'CNY',
};

export function currencyForTimeZone(tz: string): string {
  return PAR_FUSEAU[tz] || 'USD';
}

export function useCurrency(): string {
  return currencyForTimeZone(useTimeZone());
}

/** Montant en unités principales (ex. 5200 XOF, 12.5 EUR) */
export function formatMoney(montant: number, devise: string): string {
  try {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: devise }).format(montant);
  } catch {
    return `${montant} ${devise}`;
  }
}

/** Montant stocké en centimes (boutique) */
export function formatCentimes(centimes: number, devise: string): string {
  return formatMoney(centimes / 100, devise);
}

/** Prix d'un abonnement : XOF pour la zone CFA quand il est renseigné, sinon dollars */
export function planPrice(plan: { prix_usd?: number | null; prix_xof?: number | null }, devise: string): string {
  const xof = Number(plan.prix_xof ?? 0);
  const usd = Number(plan.prix_usd ?? 0);
  if (xof === 0 && usd === 0) return formatMoney(0, devise === 'XOF' ? 'XOF' : 'USD');
  if (devise === 'XOF' && xof > 0) return formatMoney(xof, 'XOF');
  return formatMoney(usd, 'USD');
}
