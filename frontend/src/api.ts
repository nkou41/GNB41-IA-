const API_BASE = 'http://localhost:5001/api';

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Erreur serveur');
  return data;
}

async function requestForm(path: string, formData: FormData) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
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

  listWorkspaces: () => request('/workspaces'),
  createWorkspace: (nom: string) =>
    request('/workspaces', { method: 'POST', body: JSON.stringify({ nom }) }),
  getWorkspace: (workspaceId: string) => request(`/workspaces/${workspaceId}`),
  deleteWorkspace: (workspaceId: string) =>
    request(`/workspaces/${workspaceId}`, { method: 'DELETE' }),
  listMembers: (workspaceId: string) => request(`/workspaces/${workspaceId}/members`),
  addMember: (workspaceId: string, email: string) =>
    request(`/workspaces/${workspaceId}/members`, { method: 'POST', body: JSON.stringify({ email }) }),
  removeMember: (workspaceId: string, userId: string) =>
    request(`/workspaces/${workspaceId}/members/${userId}`, { method: 'DELETE' }),

  listProjects: (workspaceId: string) => request(`/projects/workspace/${workspaceId}`),
  createProject: (workspaceId: string, nom: string, prompt_initial: string, provider: string = 'claude') =>
    request(`/projects/workspace/${workspaceId}`, { method: 'POST', body: JSON.stringify({ nom, prompt_initial, provider }) }),
  getProject: (projectId: string) => request(`/projects/${projectId}`),
  regenerateProject: (projectId: string, prompt: string, provider?: string) =>
    request(`/projects/${projectId}/regenerate`, { method: 'POST', body: JSON.stringify({ prompt, provider }) }),
  listVersions: (projectId: string) => request(`/projects/${projectId}/versions`),
  deleteProject: (projectId: string) => request(`/projects/${projectId}`, { method: 'DELETE' }),
  exportProjectUrl: (projectId: string) => `${API_BASE}/projects/${projectId}/export`,
  duplicateProject: (projectId: string) => request(`/projects/${projectId}/duplicate`, { method: 'POST' }),
  listMessages: (projectId: string) => request(`/projects/${projectId}/messages`),
  chatProject: (projectId: string, message: string, provider?: string, image?: { data: string; mediaType: string; name: string }) =>
    request(`/projects/${projectId}/chat`, { method: 'POST', body: JSON.stringify({ message, provider, image }) }),
  listMarketplace: () => request('/marketplace'),
  getListing: (listingId: string) => request(`/marketplace/${listingId}`),
  myListings: () => request('/marketplace/mine'),
  deleteListing: (listingId: string) => request(`/marketplace/${listingId}`, { method: 'DELETE' }),
  createListing: (formData: FormData) => requestForm('/marketplace', formData),
  myPurchases: () => request('/marketplace/mine-purchases'),
  purchaseListing: (listingId: string) => request(`/marketplace/${listingId}/purchase`, { method: 'POST' }),
  updateListing: (listingId: string, data: any) => request(`/marketplace/${listingId}`, { method: 'PUT', body: JSON.stringify(data) }),
  adminDashboard: () => request('/marketplace/admin/dashboard'),
};
