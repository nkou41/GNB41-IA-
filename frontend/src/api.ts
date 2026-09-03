const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

let csrfToken: string | null = null;

async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const res = await fetch(`${API_BASE}/auth/csrf-token`, { credentials: 'include' });
  const data = await res.json();
  csrfToken = data.csrf_token;
  return csrfToken as string;
}

async function request(path: string, options: RequestInit = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (method !== 'GET') {
    headers['X-CSRFToken'] = await getCsrfToken();
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  });
  if (res.status === 400) {
    const cloned = res.clone();
    try {
      const errData = await cloned.json();
      if (errData.error && String(errData.error).toLowerCase().includes('csrf')) {
        csrfToken = null;
      }
    } catch {}
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ? `${data.error}: ${data.detail}` : (data.error || 'Erreur serveur'));
  return data;
}

async function requestForm(path: string, formData: FormData) {
  const token = await getCsrfToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': token },
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Erreur serveur');
  return data;
}

export const api = {
  register: (username: string, email: string, password: string) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ username, email, password }) }),
  login: (username: string, password: string) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  updateMe: (current_password: string, email?: string, password?: string) =>
    request('/auth/me', { method: 'PUT', body: JSON.stringify({ current_password, email, password }) }),
  forgotPassword: (email: string) =>
    request('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token: string, password: string) =>
    request('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, password }) }),
  confirmEmail: (token: string) =>
    request('/auth/confirm-email', { method: 'POST', body: JSON.stringify({ token }) }),

  createPayment: (plan: string) =>
    request('/billing/create-payment', { method: 'POST', body: JSON.stringify({ plan }) }),
  verifyPayment: (transactionId: number) =>
    request(`/billing/verify-payment/${transactionId}`),

  listWorkspaces: () => request('/workspaces'),
  createWorkspace: (nom: string) =>
    request('/workspaces', { method: 'POST', body: JSON.stringify({ nom }) }),
  getWorkspace: (workspaceId: string) => request(`/workspaces/${workspaceId}`),
  deleteWorkspace: (workspaceId: string) =>
    request(`/workspaces/${workspaceId}`, { method: 'DELETE' }),
  listMembers: (workspaceId: string) => request(`/workspaces/${workspaceId}/members`),
  getActivity: (workspaceId: string) => request(`/workspaces/${workspaceId}/activity`),
  addMember: (workspaceId: string, email: string, role: string = 'editeur') =>
    request(`/workspaces/${workspaceId}/members`, { method: 'POST', body: JSON.stringify({ email, role }) }),
  removeMember: (workspaceId: string, userId: string) =>
    request(`/workspaces/${workspaceId}/members/${userId}`, { method: 'DELETE' }),

  listProjects: (workspaceId: string) => request(`/projects/workspace/${workspaceId}`),
  createProject: (workspaceId: string, nom: string, prompt_initial: string, provider: string = 'claude', mode?: string) =>
    request(`/projects/workspace/${workspaceId}`, { method: 'POST', body: JSON.stringify({ nom, prompt_initial, provider, mode }) }),
  getProject: (projectId: string) => request(`/projects/${projectId}`),
  regenerateProject: (projectId: string, prompt: string, provider?: string, mode?: string) =>
    request(`/projects/${projectId}/regenerate`, { method: 'POST', body: JSON.stringify({ prompt, provider, mode }) }),
  listVersions: (projectId: string) => request(`/projects/${projectId}/versions`),
  restoreVersion: (projectId: string, versionId: string) => request(`/projects/${projectId}/versions/${versionId}/restore`, { method: 'POST' }),
  updateMemoireProjet: (projectId: string, memoire_projet: string) => request(`/projects/${projectId}/memoire`, { method: 'PUT', body: JSON.stringify({ memoire_projet }) }),
  deleteProject: (projectId: string) => request(`/projects/${projectId}`, { method: 'DELETE' }),
  exportProjectUrl: (projectId: string) => `${API_BASE}/projects/${projectId}/export`,
  duplicateProject: (projectId: string) => request(`/projects/${projectId}/duplicate`, { method: 'POST' }),
  listMessages: (projectId: string) => request(`/projects/${projectId}/messages`),
  chatProject: (projectId: string, message: string, provider?: string, image?: { data: string; mediaType: string; name: string }, mode?: string) =>
    request(`/projects/${projectId}/chat`, { method: 'POST', body: JSON.stringify({ message, provider, image, mode }) }),
  listMarketplace: () => request('/marketplace'),
  getListing: (listingId: string) => request(`/marketplace/${listingId}`),
  myListings: () => request('/marketplace/mine'),
  deleteListing: (listingId: string) => request(`/marketplace/${listingId}`, { method: 'DELETE' }),
  createListing: (formData: FormData) => requestForm('/marketplace', formData),
  myPurchases: () => request('/marketplace/mine-purchases'),
  purchaseListing: (listingId: string) => request(`/marketplace/${listingId}/purchase`, { method: 'POST' }),
  updateListing: (listingId: string, data: any) => request(`/marketplace/${listingId}`, { method: 'PUT', body: JSON.stringify(data) }),
  adminDashboard: () => request('/marketplace/admin/dashboard'),
  adminListUsers: (q?: string) => request(`/admin/users${q ? '?q=' + encodeURIComponent(q) : ''}`),
  adminUpdateUserRole: (userId: string, role: string) => request(`/admin/users/${userId}/role`, { method: 'PATCH', body: JSON.stringify({ role }) }),
  adminListWorkspaces: () => request('/admin/workspaces'),
  adminDeleteWorkspace: (workspaceId: string) => request(`/admin/workspaces/${workspaceId}`, { method: 'DELETE' }),
  adminRunEvaluation: (provider?: string) => request('/admin/evaluation/run', { method: 'POST', body: JSON.stringify({ provider: provider || 'claude' }) }),
  adminEvaluationHistory: () => request('/admin/evaluation/history'),
  adminStats: () => request('/admin/stats'),
  verifyPurchase: (purchaseId: string) => request(`/marketplace/purchase/${purchaseId}/verify`),
  updateFile: (projectId: string, chemin: string, contenu: string) =>
    request(`/projects/${projectId}/files`, { method: 'PUT', body: JSON.stringify({ chemin, contenu }) }),
  listAppTables: (projectId: string) => request(`/appdb/${projectId}/tables`),
  createAppTable: (projectId: string, nom: string, colonnes: any[]) =>
    request(`/appdb/${projectId}/tables`, { method: 'POST', body: JSON.stringify({ nom, colonnes }) }),
  deleteAppTable: (tableId: string) => request(`/appdb/tables/${tableId}`, { method: 'DELETE' }),
  listAppRows: (tableId: string) => request(`/appdb/tables/${tableId}/rows`),
  listAppKeys: (projectId: string) => request(`/appdb/${projectId}/keys`),
  createAppKey: (projectId: string) => request(`/appdb/${projectId}/keys`, { method: 'POST' }),
  revokeAppKey: (keyId: string) => request(`/appdb/keys/${keyId}`, { method: 'DELETE' }),
  deployProject: (projectId: string) => request(`/projects/${projectId}/deploy`, { method: 'POST' }),
  undeployProject: (projectId: string) => request(`/projects/${projectId}/undeploy`, { method: 'POST' }),
};
