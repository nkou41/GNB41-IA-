const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

export interface NotifCategory {
  id: string;
  label: string;
  description: string;
  active: boolean;
}

async function csrf(): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/csrf-token`, { credentials: 'include' });
  const data = await res.json();
  return data.csrf_token;
}

export async function fetchCategories(): Promise<NotifCategory[]> {
  const res = await fetch(`${API_BASE}/notifications/preferences`, { credentials: 'include' });
  if (!res.ok) throw new Error('Chargement impossible');
  const data = await res.json();
  return data.categories;
}

export async function saveCategory(categorie: string, active: boolean): Promise<void> {
  const token = await csrf();
  const res = await fetch(`${API_BASE}/notifications/preferences`, {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
    body: JSON.stringify({ categorie, active }),
  });
  if (!res.ok) throw new Error('Enregistrement impossible');
}
