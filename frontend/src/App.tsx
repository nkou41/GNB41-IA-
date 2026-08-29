import { useState, useEffect, useRef } from 'react';
import NotificationBell from './components/NotificationBell';
import { identifyUser, trackEvent, resetAnalytics } from './analytics';
import { api } from './api';
import './App.css';

interface User {
  id: string;
  username: string;
  email: string;
  plan?: string;
  plan_expiry?: string | null;
}

interface Workspace {
  id: string;
  nom: string;
  owner_id: string;
  project_count: number;
}

interface Project {
  id: string;
  nom: string;
  prompt_initial: string;
  statut: string;
  code_genere?: string;
  erreur_message?: string;
  provider?: string;
}

function AnimatedPlaceholder({ text, active }: { text: string; active: boolean }) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    if (!active) { setDisplayed(''); return; }
    let i = 0;
    let deleting = false;
    let cancelled = false;
    let timeout: ReturnType<typeof setTimeout> | null = null;

    function tick() {
      if (cancelled) return;
      if (!deleting) {
        i++;
        setDisplayed(text.slice(0, i));
        if (i >= text.length) {
          timeout = setTimeout(() => { if (!cancelled) { deleting = true; tick(); } }, 1800);
          return;
        }
        timeout = setTimeout(tick, 45);
      } else {
        i--;
        setDisplayed(text.slice(0, i));
        if (i <= 0) {
          deleting = false;
          timeout = setTimeout(tick, 400);
          return;
        }
        timeout = setTimeout(tick, 20);
      }
    }
    timeout = setTimeout(tick, 300);
    return () => {
      cancelled = true;
      if (timeout) clearTimeout(timeout);
    };
  }, [text, active]);

  return <span className="animated-placeholder" style={{ visibility: active ? 'visible' : 'hidden' }}>{displayed}<span className="animated-cursor">|</span></span>;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true); // TODO: nettoyage complet prévu plus tard
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [confirmToken, setConfirmToken] = useState<string | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<'checking' | 'approved' | 'pending' | 'error' | null>(null);
  const [marketPaymentStatus, setMarketPaymentStatus] = useState<'checking' | 'approved' | 'pending' | 'error' | null>(null);
  const [confirmStatus, setConfirmStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [confirmMessage, setConfirmMessage] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState('');
  const [resetStatus, setResetStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [resetMessage, setResetMessage] = useState('');
  const [adminStats, setAdminStats] = useState<any | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showMarketplace, setShowMarketplace] = useState(false);
  const [marketplaceListings, setMarketplaceListings] = useState<any[]>([]);
  const [showMesVentes, setShowMesVentes] = useState(false);
  const [myListingsList, setMyListingsList] = useState<any[]>([]);
  const [showMesAchats, setShowMesAchats] = useState(false);
  const [myPurchasesList, setMyPurchasesList] = useState<any[]>([]);
  const [purchaseLoadingId, setPurchaseLoadingId] = useState<string | null>(null);
  const [showAdminDashboard, setShowAdminDashboard] = useState(false);
  const [showLegal, setShowLegal] = useState<'cgv' | 'mentions' | null>(null);
  const [showPublishForm, setShowPublishForm] = useState(false);
  const [publishTitre, setPublishTitre] = useState('');
  const [publishDescription, setPublishDescription] = useState('');
  const [publishPrix, setPublishPrix] = useState('');
  const [publishSourceType, setPublishSourceType] = useState<'gnb41' | 'externe_zip' | 'externe_lien'>('gnb41');
  const [publishProjectId, setPublishProjectId] = useState('');
  const [publishLienExterne, setPublishLienExterne] = useState('');
  const [publishFile, setPublishFile] = useState<File | null>(null);
  const [publishImage, setPublishImage] = useState<File | null>(null);
  const [publishCategorie, setPublishCategorie] = useState('autre');
  const [publishTags, setPublishTags] = useState('');
  const [publishLoading, setPublishLoading] = useState(false);
  const [publishError, setPublishError] = useState('');
  const [showVersions, setShowVersions] = useState(false);
  const [versions, setVersions] = useState<any[]>([]);
  const [showAuth, setShowAuth] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotMessage, setForgotMessage] = useState('');
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState<string>('');
  const [editorSaving, setEditorSaving] = useState(false);
  const [editorDirty, setEditorDirty] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [attachedImage, setAttachedImage] = useState<{ data: string; mediaType: string; name: string } | null>(null);
  const [showProviderMenu, setShowProviderMenu] = useState(false);
  const [chatProvider, setChatProvider] = useState('claude');
  const [previewTab, setPreviewTab] = useState<'apercu' | 'code' | 'donnees'>('apercu');
  const [appTables, setAppTables] = useState<any[]>([]);
  const [appKeys, setAppKeys] = useState<any[]>([]);
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null);
  const [selectedTableRows, setSelectedTableRows] = useState<any[]>([]);
  const [newKeyRevealed, setNewKeyRevealed] = useState<string | null>(null);
  const [quickPrompt, setQuickPrompt] = useState('');
  const [quickProvider, setQuickProvider] = useState('claude');
  const [quickLoading, setQuickLoading] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [darkMode, setDarkMode] = useState<boolean>(() => localStorage.getItem('theme') === 'dark');

  useEffect(() => {
    document.body.classList.toggle('dark-mode', darkMode);
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);
  const [showWorkspaceSettings, setShowWorkspaceSettings] = useState(false);
  const [workspaceSettingsTab, setWorkspaceSettingsTab] = useState<'membres' | 'activite' | 'general'>('membres');
  const [wsMembers, setWsMembers] = useState<any[]>([]);
  const [wsActivityLogs, setWsActivityLogs] = useState<any[]>([]);
  const [wsInviteEmail, setWsInviteEmail] = useState('');
  const [wsInviteRole, setWsInviteRole] = useState('editeur');
  const [wsInviteError, setWsInviteError] = useState('');
  const [landingPrompt, setLandingPrompt] = useState('');
  const [landingModel, setLandingModel] = useState('claude');
  const [recentProjects, setRecentProjects] = useState<any[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');


  const [settingsEmail, setSettingsEmail] = useState('');
  const [settingsPassword, setSettingsPassword] = useState('');
  const [settingsCurrentPassword, setSettingsCurrentPassword] = useState('');
  const [settingsMsg, setSettingsMsg] = useState('');
  const [settingsError, setSettingsError] = useState('');


  useEffect(() => {
    api.me().then(setUser).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (showWorkspaceSettings && activeWorkspace) {
      api.listMembers(activeWorkspace.id).then(setWsMembers).catch(() => {});
      api.getActivity(activeWorkspace.id).then(setWsActivityLogs).catch(() => {});
    }
  }, [showWorkspaceSettings, activeWorkspace]);

  useEffect(() => {
    if (!user) return;
    const path = window.location.pathname;

    if (path === '/marketplace') {
      setShowMarketplace(true);
    } else if (path === '/mes-achats') {
      setShowMesAchats(true);
    } else if (path === '/mes-ventes') {
      setShowMesVentes(true);
    } else if (path === '/administration') {
      setShowAdminDashboard(true);
    } else if (path === '/parametres') {
      setShowSettings(true);
    } else if (path === '/mentions-legales') {
      setShowLegal('mentions');
    } else if (path === '/cgv') {
      setShowLegal('cgv');
    } else if (path.startsWith('/projet/')) {
      const projectId = path.replace('/projet/', '');
      if (projectId) {
        api.getProject(projectId).then((p) => {
          setActiveProject(p);
        }).catch(() => {
          window.history.replaceState({}, '', '/');
        });
      }
    }
  }, [user]);

  const navigateTo = (path: string) => {
    window.history.pushState({}, '', path);
  };

  useEffect(() => {
    const handlePopState = () => {
      window.location.reload();
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (user) {
      api.listWorkspaces().then(async (ws) => {
        setWorkspaces(ws);
        try {
          const projectLists = await Promise.all(ws.map((w: Workspace) => api.listProjects(w.id).catch(() => [])));
          const allProjects = projectLists.flatMap((list: Project[], idx: number) => list.map((p) => ({ ...p, parentWorkspaceId: ws[idx].id })));
          const sorted = allProjects.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
          setRecentProjects(sorted.slice(0, 6));
        } catch {}
      }).catch(() => {});
      setSettingsEmail(user.email);
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    const params = new URLSearchParams(window.location.search);
    const sharedProjectId = params.get('project');
    if (!sharedProjectId) return;

    api.getProject(sharedProjectId).then(async (project) => {
      const workspace = await api.getWorkspace(project.workspace_id);
      setActiveWorkspace(workspace);
      setActiveProject(project);
      window.history.replaceState({}, '', window.location.pathname);
    }).catch(() => {
      alert("Ce projet n'existe pas ou vous n'y avez pas accès.");
      window.history.replaceState({}, '', window.location.pathname);
    });
  }, [user]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (window.location.pathname === '/reset-password' && token) {
      setResetToken(token);
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (window.location.pathname === '/confirm-email' && token) {
      setConfirmToken(token);
      api.confirmEmail(token)
        .then((res) => { setConfirmStatus('success'); setConfirmMessage(res.message); })
        .catch((err) => { setConfirmStatus('error'); setConfirmMessage(err.message || 'Lien invalide ou expire'); });
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const transactionId = params.get('id') || params.get('transaction_id');
    if (window.location.pathname === '/payment-callback' && transactionId) {
      setPaymentStatus('checking');
      api.verifyPayment(Number(transactionId))
        .then((res) => {
          if (res.status === 'approved') setPaymentStatus('approved');
          else setPaymentStatus('pending');
        })
        .catch(() => setPaymentStatus('error'));
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const purchaseId = params.get('purchase_id');
    if (window.location.pathname === '/marketplace-callback' && purchaseId) {
      setMarketPaymentStatus('checking');
      api.verifyPurchase(purchaseId)
        .then((res) => {
          if (res.statut === 'complete') setMarketPaymentStatus('approved');
          else if (res.statut === 'echoue') setMarketPaymentStatus('error');
          else setMarketPaymentStatus('pending');
        })
        .catch(() => setMarketPaymentStatus('error'));
    }
  }, []);

  useEffect(() => {
    if (activeWorkspace) {
      api.listProjects(activeWorkspace.id).then(setProjects).catch(() => {});
    }
  }, [activeWorkspace]);

  useEffect(() => {
    if (showMarketplace) {
      api.listMarketplace().then((res) => setMarketplaceListings(res.listings)).catch(() => {});
    }
  }, [showMarketplace]);

  useEffect(() => {
    if (showMesVentes) {
      api.myListings().then(setMyListingsList).catch(() => {});
    }
  }, [showMesVentes]);

  useEffect(() => {
    if (showMesAchats) {
      api.myPurchases().then(setMyPurchasesList).catch(() => {});
    }
  }, [showMesAchats]);

  useEffect(() => {
    if (showAdminDashboard) {
      api.adminDashboard().then(setAdminStats).catch(() => {});
    }
  }, [showAdminDashboard]);

  useEffect(() => {
    if (activeProject) {
      api.listMessages(activeProject.id).then(setChatMessages).catch(() => {});
    } else {
      setChatMessages([]);
    }
  }, [activeProject?.id]);

  useEffect(() => {
    if (activeProject) {
      setChatProvider(activeProject.provider || 'claude');
    }
  }, [activeProject?.id]);

  const handleLandingSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!landingPrompt.trim()) return;
    setQuickPrompt(landingPrompt);
    setQuickProvider(landingModel);
    setShowAuth(true);
    setAuthMode('register');
  };

  const handleQuickStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickPrompt.trim()) return;
    setQuickLoading(true);
    try {
      let targetWorkspace = workspaces[0];
      if (!targetWorkspace) {
        targetWorkspace = await api.createWorkspace('Mes projets');
        setWorkspaces([targetWorkspace]);
      }
      const nom = quickPrompt.slice(0, 40);
      const project = await api.createProject(targetWorkspace.id, nom, quickPrompt, quickProvider);
      trackEvent('project_created', { provider: quickProvider });
      setQuickPrompt('');
      setActiveWorkspace(targetWorkspace);
      setActiveProject(project);
    } catch (err: any) {
      alert(`Erreur: ${err.message}`);
    } finally {
      setQuickLoading(false);
    }
  };

  const [upgradeLoading, setUpgradeLoading] = useState(false);

  const handleUpgrade = async (plan: string) => {
    setUpgradeLoading(true);
    try {
      const res = await api.createPayment(plan);
      window.location.href = res.payment_url;
    } catch (err: any) {
      alert(err.message || "Erreur lors de la creation du paiement");
      setUpgradeLoading(false);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const result = authMode === 'login'
        ? await api.login(username, password)
        : await api.register(username, email, password);
      setUser(result);
      identifyUser(String(result.id), { username: result.username, email: result.email });
      trackEvent(authMode === 'login' ? 'user_logged_in' : 'user_registered');
      if (authMode === 'register') {
        trackEvent('welcome_notification_triggered');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleLogout = async () => {
    trackEvent('user_logged_out');
    resetAnalytics();
    await api.logout();
    setUser(null);
    setWorkspaces([]);
    setActiveWorkspace(null);
    setActiveProject(null);
  };


  const handleWsInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) return;
    setWsInviteError('');
    try {
      const m = await api.addMember(activeWorkspace.id, wsInviteEmail, wsInviteRole);
      setWsMembers([...wsMembers, m]);
      setWsInviteEmail('');
    } catch (err: any) {
      setWsInviteError(err.message);
    }
  };

  const handleWsRemoveMember = async (userId: string) => {
    if (!activeWorkspace) return;
    if (!confirm('Retirer ce membre ?')) return;
    await api.removeMember(activeWorkspace.id, userId);
    setWsMembers(wsMembers.filter((m) => m.user_id !== userId));
  };

  const handleUpdateSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSettingsError('');
    setSettingsMsg('');
    try {
      const updated = await api.updateMe(settingsCurrentPassword, settingsEmail, settingsPassword || undefined);
      setUser(updated);
      setSettingsMsg('Profil mis à jour');
      setSettingsPassword('');
      setSettingsCurrentPassword('');
    } catch (err: any) {
      setSettingsError(err.message);
    }
  };

  const handlePurchase = async (listingId: string) => {
    setPurchaseLoadingId(listingId);
    try {
      const result = await api.purchaseListing(listingId);
      trackEvent('marketplace_purchase_initiated', { listing_id: listingId });
      if (result.payment_url) {
        window.location.href = result.payment_url;
      } else {
        alert('Achat enregistre, mais aucune page de paiement recue.');
        setPurchaseLoadingId(null);
      }
    } catch (err: any) {
      alert(`Erreur: ${err.message}`);
      setPurchaseLoadingId(null);
    }
  };

  const handlePublishListing = async (e: React.FormEvent) => {
    e.preventDefault();
    setPublishError('');
    if (!publishTitre.trim() || !publishDescription.trim() || !publishPrix.trim()) {
      setPublishError('Titre, description et prix sont requis.');
      return;
    }
    if (publishSourceType === 'gnb41' && !publishProjectId) {
      setPublishError('Sélectionnez un projet à publier.');
      return;
    }
    if (publishSourceType === 'externe_zip' && !publishFile) {
      setPublishError('Sélectionnez un fichier .zip.');
      return;
    }
    if (publishSourceType === 'externe_lien' && !publishLienExterne.trim()) {
      setPublishError('Indiquez un lien externe.');
      return;
    }

    setPublishLoading(true);
    try {
      const formData = new FormData();
      formData.append('titre', publishTitre);
      formData.append('description', publishDescription);
      formData.append('prix_centimes', String(Math.round(parseFloat(publishPrix) * 100)));
      formData.append('source_type', publishSourceType);
      if (publishSourceType === 'gnb41') formData.append('project_id', publishProjectId);
      if (publishSourceType === 'externe_zip' && publishFile) formData.append('fichier', publishFile);
      if (publishSourceType === 'externe_lien') formData.append('lien_externe', publishLienExterne);
      if (publishImage) formData.append('image', publishImage);
      formData.append('categorie', publishCategorie);
      formData.append('tags', publishTags);

      await api.createListing(formData);
      trackEvent('listing_published', { categorie: publishCategorie, source_type: publishSourceType });
      setShowPublishForm(false);
      setPublishTitre('');
      setPublishDescription('');
      setPublishPrix('');
      setPublishProjectId('');
      setPublishLienExterne('');
      setPublishFile(null);
      setPublishImage(null);
      setPublishCategorie('autre');
      setPublishTags('');
      const res = await api.listMarketplace();
      setMarketplaceListings(res.listings);
    } catch (err: any) {
      setPublishError(err.message);
    } finally {
      setPublishLoading(false);
    }
  };

  if (loading) return <div className="center"><div className="spinner"></div></div>;

  if (marketPaymentStatus) {
    return (
      <div className="landing">
        <div className="landing-hero">
          <img src="/logo.png" alt="GNB41 IA" className="app-logo app-logo-lg" />
          <h1>Paiement de votre achat</h1>
          {marketPaymentStatus === 'checking' && <p className="landing-tagline">Verification du paiement en cours...</p>}
          {marketPaymentStatus === 'approved' && (
            <>
              <p className="landing-tagline">Paiement confirme ! Votre achat est disponible dans "Mes achats".</p>
              <button onClick={() => { setMarketPaymentStatus(null); window.history.replaceState({}, '', '/'); window.location.reload(); }}>Continuer</button>
            </>
          )}
          {marketPaymentStatus === 'pending' && <p className="landing-tagline">Paiement en attente de confirmation. Cela peut prendre quelques instants.</p>}
          {marketPaymentStatus === 'error' && <p style={{color: 'red'}}>Le paiement a echoue ou a ete annule.</p>}
        </div>
      </div>
    );
  }

  if (paymentStatus) {
    return (
      <div className="landing">
        <div className="landing-hero">
          <img src="/logo.png" alt="GNB41 IA" className="app-logo app-logo-lg" />
          <h1>Paiement</h1>
          {paymentStatus === 'checking' && <p className="landing-tagline">Verification du paiement en cours...</p>}
          {paymentStatus === 'approved' && (
            <>
              <p className="landing-tagline">Paiement confirme ! Votre compte est maintenant Pro.</p>
              <button onClick={() => { setPaymentStatus(null); window.history.replaceState({}, '', '/'); window.location.reload(); }}>Continuer</button>
            </>
          )}
          {paymentStatus === 'pending' && <p className="landing-tagline">Paiement en attente de confirmation. Cela peut prendre quelques instants.</p>}
          {paymentStatus === 'error' && <p style={{color: 'red'}}>Erreur lors de la verification du paiement.</p>}
        </div>
      </div>
    );
  }

  if (confirmToken) {
    return (
      <div className="landing">
        <div className="landing-hero">
          <img src="/logo.png" alt="GNB41 IA" className="app-logo app-logo-lg" />
          <h1>Confirmation de l'email</h1>
          {confirmStatus === 'loading' && <p className="landing-tagline">Verification en cours...</p>}
          {confirmStatus === 'success' && (
            <>
              <p className="landing-tagline">{confirmMessage}</p>
              <button onClick={() => { setConfirmToken(null); window.history.replaceState({}, '', '/'); setShowAuth(true); }}>Se connecter</button>
            </>
          )}
          {confirmStatus === 'error' && <p style={{color: 'red'}}>{confirmMessage}</p>}
        </div>
      </div>
    );
  }


  if (resetToken) {
    const handleResetSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      if (resetPassword.length < 8) {
        setResetMessage('Le mot de passe doit contenir au moins 8 caracteres');
        setResetStatus('error');
        return;
      }
      if (resetPassword !== resetPasswordConfirm) {
        setResetMessage('Les mots de passe ne correspondent pas');
        setResetStatus('error');
        return;
      }
      setResetStatus('loading');
      try {
        await api.resetPassword(resetToken, resetPassword);
        setResetStatus('success');
        setResetMessage('Mot de passe reinitialise avec succes. Vous pouvez vous connecter.');
      } catch (err: any) {
        setResetStatus('error');
        setResetMessage(err.message || 'Lien invalide ou expire');
      }
    };
    return (
      <div className="landing">
        <div className="landing-hero">
          <img src="/logo.png" alt="GNB41 IA" className="app-logo app-logo-lg" />
          <h1>Reinitialiser le mot de passe</h1>
          {resetStatus === 'success' ? (
            <p className="landing-tagline">{resetMessage}</p>
          ) : (
            <form onSubmit={handleResetSubmit} className="landing-prompt-form">
              <input
                type="password"
                placeholder="Nouveau mot de passe"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
              />
              <input
                type="password"
                placeholder="Confirmer le mot de passe"
                value={resetPasswordConfirm}
                onChange={(e) => setResetPasswordConfirm(e.target.value)}
              />
              {resetStatus === 'error' && <p style={{color: 'red'}}>{resetMessage}</p>}
              <button type="submit" disabled={resetStatus === 'loading'}>
                {resetStatus === 'loading' ? 'Envoi...' : 'Reinitialiser'}
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  if (!user && !showAuth) {
    return (
      <div className="landing">
        <div className="landing-hero">
          <img src="/logo.png" alt="GNB41 IA" className="app-logo app-logo-lg" />
          <h1>GNB41 IA</h1>
          <p className="landing-tagline">Décrivez votre application. L'IA la construit pour vous.</p>

          <form onSubmit={handleLandingSubmit} className="landing-prompt-form">
            <div className="textarea-wrap">
              <textarea
                placeholder=""
                value={landingPrompt}
                onChange={(e) => {
                  setLandingPrompt(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = e.target.scrollHeight + 'px';
                }}
                rows={2}
                className="auto-grow-textarea"
                ref={(el) => { if (el) { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; } }}
              />
              <AnimatedPlaceholder text="Décrivez l'application que vous souhaitez créer..." active={!landingPrompt} />
            </div>
            <div className="landing-prompt-toolbar">
              <button type="button" className="icon-btn"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></button>
              <div className="landing-divider" />
              <select value={landingModel} onChange={(e) => setLandingModel(e.target.value)} className="landing-select">
                <option value="claude">Modèle: Claude</option>
                <option value="openai">Modèle: GPT</option>
                <option value="gemini">Modèle: Gemini</option>
              </select>
              <select className="landing-select">
                <option>Créateur</option>
              </select>
              <div className="toolbar-spacer" />
              <button type="button" className="icon-btn" title="Message vocal">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
              </button>
              <button type="submit" className="landing-send-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
              </button>
            </div>
          </form>

          <p className="landing-login" onClick={() => { setShowAuth(true); setAuthMode('login'); }}>
            Déjà un compte ? Se connecter
          </p>
        </div>
        <div className="landing-features">
          <div className="feature-card">
            <h3>Espaces de travail</h3>
            <p>Organisez vos projets par équipe ou par thème, avec des collaborateurs invités.</p>
          </div>
          <div className="feature-card">
            <h3>Génération IA</h3>
            <p>Décrivez votre idée en langage naturel, obtenez du code fonctionnel.</p>
          </div>
          <div className="feature-card">
            <h3>Itération rapide</h3>
            <p>Régénérez, affinez, gardez un historique complet de chaque version.</p>
          </div>
        </div>
      </div>
    );
  }

  if (!user && showForgotPassword) {
    const handleForgotSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      setForgotMessage("Envoi en cours...");
      try {
        const res = await api.forgotPassword(forgotEmail);
        setForgotMessage(res.message);
      } catch (err: any) {
        setForgotMessage(err.message || "Erreur, veuillez reessayer");
      }
    };
    return (
      <div className="auth-container">
        <h1 onClick={() => { setShowAuth(false); setShowForgotPassword(false); }} style={{ cursor: "pointer" }}>GNB41 IA</h1>
        <form onSubmit={handleForgotSubmit} className="auth-form">
          <h2>Mot de passe oublie</h2>
          <input placeholder="Email" type="email" value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} required />
          {forgotMessage && <p className="error">{forgotMessage}</p>}
          <button type="submit">Envoyer le lien</button>
          <p className="switch" onClick={() => { setShowForgotPassword(false); setForgotMessage(""); }}>
            Retour a la connexion
          </p>
        </form>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="auth-container">
        <h1 onClick={() => setShowAuth(false)} style={{ cursor: "pointer" }}>GNB41 IA</h1>
        <form onSubmit={handleAuth} className="auth-form">
          <h2>{authMode === "login" ? "Connexion" : "Inscription"}</h2>
          <input placeholder="Nom d'utilisateur" value={username} onChange={(e) => setUsername(e.target.value)} required />
          {authMode === "register" && (
            <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          )}
          <input placeholder="Mot de passe" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {authMode === "login" && (
            <p className="switch" onClick={() => { setShowForgotPassword(true); setForgotMessage(""); }} style={{ textAlign: "right", fontSize: "0.85em" }}>
              Mot de passe oublie ?
            </p>
          )}
          {error && <p className="error">{error}</p>}
          <button type="submit">{authMode === "login" ? "Se connecter" : "S'inscrire"}</button>
          <p className="switch" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>
            {authMode === "login" ? "Pas de compte ? S'inscrire" : "Deja un compte ? Se connecter"}
          </p>
        </form>
      </div>
    );
  }

  // Vue mentions legales / CGV
  if (showLegal) {
    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <h1 onClick={() => { setShowLegal(null); navigateTo('/marketplace'); }}>← Retour</h1>
        </header>
        <div style={{ padding: '1.5rem', maxWidth: '700px', lineHeight: 1.6 }}>
          {showLegal === 'mentions' ? (
            <>
              <h2>Mentions légales</h2>
              <p style={{ marginTop: '1rem' }}><strong>Éditeur du site</strong></p>
              <p>[Nom / Raison sociale — particulier ou société]<br/>
              [Adresse complète]<br/>
              [Numéro SIRET — si applicable, sinon indiquer "Entreprise individuelle non immatriculée" selon votre statut]<br/>
              [Email de contact]<br/>
              [Numéro de téléphone — optionnel]</p>

              <p style={{ marginTop: '1rem' }}><strong>Hébergement</strong></p>
              <p>[Nom de l'hébergeur]<br/>
              [Adresse de l'hébergeur]</p>

              <p style={{ marginTop: '1rem' }}><strong>Directeur de publication</strong></p>
              <p>[Nom du responsable]</p>
            </>
          ) : (
            <>
              <h2>Conditions Générales de Vente</h2>

              <p style={{ marginTop: '1rem' }}><strong>1. Objet</strong></p>
              <p>Les présentes conditions régissent la vente d'applications numériques entre vendeurs et acheteurs sur la plateforme GNB41 IA.</p>

              <p style={{ marginTop: '1rem' }}><strong>2. Prix</strong></p>
              <p>Les prix sont indiqués en euros. Une commission de 20% est prélevée par la plateforme sur chaque vente.</p>

              <p style={{ marginTop: '1rem' }}><strong>3. Livraison</strong></p>
              <p>L'application (code source et/ou accès) est mise à disposition de l'acheteur immédiatement après confirmation du paiement.</p>

              <p style={{ marginTop: '1rem' }}><strong>4. Droit de rétractation</strong></p>
              <p>Conformément à la législation sur le contenu numérique non fourni sur support matériel, le droit de rétractation ne s'applique pas une fois le téléchargement commencé, sauf accord exprès du vendeur.</p>

              <p style={{ marginTop: '1rem' }}><strong>5. Responsabilité</strong></p>
              <p>Le vendeur est seul responsable du contenu, de la qualité et de la légalité de l'application vendue. La plateforme agit en tant qu'intermédiaire technique.</p>

              <p style={{ marginTop: '1rem' }}><strong>6. Litiges</strong></p>
              <p>[Adresse email de contact pour tout litige]. À défaut de résolution amiable, les tribunaux compétents seront ceux du ressort de [ville/juridiction].</p>

              <p style={{ marginTop: '1.5rem', fontStyle: 'italic', color: '#8a7f68' }}>
                Ce document est un modèle et doit être complété/validé par un professionnel du droit avant mise en ligne publique.
              </p>
            </>
          )}
        </div>
      </div>
    );
  }

  // Vue Administration
  if (showAdminDashboard) {
    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <h1 onClick={() => { setShowAdminDashboard(false); navigateTo('/marketplace'); }}>← Boutique</h1>
          <div className="marketplace-header-actions">
            <NotificationBell />
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>

        <div className="marketplace-title-row">
          <div>
            <h2>Administration</h2>
            <p>Statistiques globales de la plateforme</p>
          </div>
        </div>

        {!adminStats ? (
          <div className="marketplace-empty">
            <p>Chargement...</p>
          </div>
        ) : (
          <>
            <div className="admin-stats-grid">
              <div className="admin-stat-card admin-stat-blue">
                <span className="admin-stat-label">Annonces publiées</span>
                <span className="admin-stat-value">{adminStats.listings_publies}</span>
                <span className="admin-stat-sub">sur {adminStats.total_listings} au total</span>
              </div>
              <div className="admin-stat-card admin-stat-purple">
                <span className="admin-stat-label">Ventes complétées</span>
                <span className="admin-stat-value">{adminStats.total_ventes}</span>
              </div>
              <div className="admin-stat-card admin-stat-green">
                <span className="admin-stat-label">Chiffre d'affaires</span>
                <span className="admin-stat-value">{(adminStats.total_chiffre_affaires_centimes / 100).toFixed(2)} €</span>
              </div>
              <div className="admin-stat-card admin-stat-amber">
                <span className="admin-stat-label">Commission (20%)</span>
                <span className="admin-stat-value">{(adminStats.total_commission_centimes / 100).toFixed(2)} €</span>
              </div>
            </div>

            <div style={{ padding: '0 1.5rem 2rem' }}>
              <h3 style={{ marginBottom: '0.8rem', color: '#2b2410' }}>Dernières ventes</h3>
              {adminStats.dernieres_ventes.length === 0 ? (
                <p style={{ color: '#8a7f68' }}>Aucune vente pour le moment.</p>
              ) : (
                <div className="admin-sales-table">
                  {adminStats.dernieres_ventes.map((v: any) => (
                    <div key={v.id} className="admin-sales-row">
                      <span className="admin-sales-titre">{v.titre}</span>
                      <span className="admin-sales-prix">{(v.prix_paye_centimes / 100).toFixed(2)} €</span>
                      <span className={`marketplace-badge ${v.statut === 'complete' ? '' : 'admin-badge-pending'}`}>{v.statut}</span>
                      <span className="admin-sales-date">{new Date(v.created_at).toLocaleDateString('fr-FR')}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    );
  }

  // Vue Mes achats
  if (showMesAchats) {
    const totalDepense = myPurchasesList.reduce((sum, p) => sum + p.prix_paye_centimes, 0);

    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <h1 onClick={() => { setShowMesAchats(false); navigateTo('/marketplace'); }}>← Boutique</h1>
          <div className="marketplace-header-actions">
            <NotificationBell />
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>

        <div className="marketplace-title-row">
          <div>
            <h2>Mes achats</h2>
            <p>{myPurchasesList.length} achat{myPurchasesList.length !== 1 ? 's' : ''} · {(totalDepense / 100).toFixed(2)} EUR dépensés</p>
          </div>
        </div>

        {myPurchasesList.length === 0 ? (
          <div className="marketplace-empty">
            <p>Vous n'avez encore rien acheté.</p>
          </div>
        ) : (
          <div className="marketplace-grid">
            {myPurchasesList.map((p) => (
              <div key={p.id} className="marketplace-card">
                <div className="marketplace-card-footer">
                  <span className="marketplace-price">{(p.prix_paye_centimes / 100).toFixed(2)} EUR</span>
                  <span className="marketplace-badge">{p.statut}</span>
                </div>
                <p className="marketplace-card-desc">
                  Acheté le {new Date(p.created_at).toLocaleDateString('fr-FR')}
                </p>
                {p.statut === 'en_attente' && (
                  <button
                    type="button"
                    className="btn-publish"
                    style={{ marginTop: '0.5rem', justifyContent: 'center', width: '100%' }}
                    onClick={async () => {
                      const res = await api.verifyPurchase(p.id);
                      setMyPurchasesList((prev) => prev.map((x) => (x.id === p.id ? res : x)));
                    }}
                  >
                    Verifier le paiement
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Vue Mes ventes
  if (showMesVentes) {
    const totalRevenus = myListingsList.reduce((sum, l) => sum + (l.revenus_centimes || 0), 0);
    const totalVentes = myListingsList.reduce((sum, l) => sum + (l.nb_ventes || 0), 0);

    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <h1 onClick={() => { setShowMesVentes(false); navigateTo('/marketplace'); }}>← Boutique</h1>
          <div className="marketplace-header-actions">
            <NotificationBell />
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>

        <div className="marketplace-title-row">
          <div>
            <h2>Mes ventes</h2>
            <p>{totalVentes} vente{totalVentes !== 1 ? 's' : ''} · {(totalRevenus / 100).toFixed(2)} EUR de revenus</p>
          </div>
        </div>

        {myListingsList.length === 0 ? (
          <div className="marketplace-empty">
            <p>Vous n'avez publié aucune application pour le moment.</p>
          </div>
        ) : (
          <div className="marketplace-grid">
            {myListingsList.map((l) => (
              <div key={l.id} className="marketplace-card">
                <h3>{l.titre}</h3>
                <p className="marketplace-card-desc">{l.description}</p>
                <div className="marketplace-card-footer">
                  <span className="marketplace-price">{(l.prix_centimes / 100).toFixed(2)} {l.devise}</span>
                  <span className="marketplace-badge">{l.statut}</span>
                </div>
                <div className="marketplace-card-footer" style={{ borderTop: 'none', paddingTop: 0 }}>
                  <span style={{ fontSize: '0.8rem', color: '#8a7f68' }}>{l.nb_ventes || 0} vente{l.nb_ventes !== 1 ? 's' : ''}</span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{((l.revenus_centimes || 0) / 100).toFixed(2)} EUR</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Vue boutique
  if (showMarketplace) {
    const sourceIcon = (type: string) => {
      if (type === 'externe_zip') {
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>;
      }
      if (type === 'externe_lien') {
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>;
      }
      return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>;
    };

    const sourceLabel = (type: string) => {
      if (type === 'externe_zip') return 'Fichier ZIP';
      if (type === 'externe_lien') return 'Lien externe';
      return 'GNB41 IA';
    };

    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <h1 onClick={() => { setShowMarketplace(false); navigateTo('/'); }}>← GNB41 IA</h1>
          <div className="marketplace-header-actions">
            <NotificationBell />
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>

        <div className="marketplace-title-row">
          <div>
            <h2>Boutique d'applications</h2>
            <p>Découvrez et publiez des applications prêtes à l'emploi</p>
          </div>
          {user.email === 'nkougnarigo226@gmail.com' && (
            <button className="btn-publish is-cancel" onClick={() => { setShowAdminDashboard(true); navigateTo('/administration'); }} style={{ marginRight: '0.6rem' }}>
              Administration
            </button>
          )}
          <button className="btn-publish is-cancel" onClick={() => { setShowMesAchats(true); navigateTo('/mes-achats'); }} style={{ marginRight: '0.6rem' }}>
            Mes achats
          </button>
          <button className="btn-publish is-cancel" onClick={() => { setShowMesVentes(true); navigateTo('/mes-ventes'); }} style={{ marginRight: '0.6rem' }}>
            Mes ventes
          </button>
          <button className={`btn-publish ${showPublishForm ? 'is-cancel' : ''}`} onClick={() => setShowPublishForm(!showPublishForm)}>
            {showPublishForm ? (
              'Annuler'
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Publier une application
              </>
            )}
          </button>
        </div>

        {showPublishForm && (
          <div className="marketplace-form-panel">
            <form onSubmit={handlePublishListing} className="auth-form">
              <input placeholder="Titre de l'application" value={publishTitre} onChange={(e) => setPublishTitre(e.target.value)} />
              <textarea placeholder="Description" value={publishDescription} onChange={(e) => setPublishDescription(e.target.value)} rows={3} />
              <input placeholder="Prix (€)" type="number" step="0.01" min="0" value={publishPrix} onChange={(e) => setPublishPrix(e.target.value)} />

              <label style={{ fontSize: '0.85rem', color: '#8a7f68' }}>
                Image de présentation (optionnel — sinon capture automatique pour les liens)
              </label>
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setPublishImage(e.target.files?.[0] || null)} />

              <select value={publishCategorie} onChange={(e) => setPublishCategorie(e.target.value)}>
                <option value="productivite">Productivité</option>
                <option value="ecommerce">E-commerce</option>
                <option value="jeux">Jeux</option>
                <option value="utilitaires">Utilitaires</option>
                <option value="education">Éducation</option>
                <option value="sante">Santé</option>
                <option value="finance">Finance</option>
                <option value="social">Social</option>
                <option value="autre">Autre</option>
              </select>

              <input placeholder="Tags (séparés par des virgules)" value={publishTags} onChange={(e) => setPublishTags(e.target.value)} />

              <select value={publishSourceType} onChange={(e) => setPublishSourceType(e.target.value as any)}>
                <option value="gnb41">Projet généré sur GNB41 IA</option>
                <option value="externe_zip">Application externe (fichier .zip)</option>
                <option value="externe_lien">Application externe (lien)</option>
              </select>

              {publishSourceType === 'gnb41' && (
                <select value={publishProjectId} onChange={(e) => setPublishProjectId(e.target.value)}>
                  <option value="">Choisir un projet...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.nom}</option>
                  ))}
                </select>
              )}

              {publishSourceType === 'externe_zip' && (
                <input type="file" accept=".zip" onChange={(e) => setPublishFile(e.target.files?.[0] || null)} />
              )}

              {publishSourceType === 'externe_lien' && (
                <input placeholder="https://..." value={publishLienExterne} onChange={(e) => setPublishLienExterne(e.target.value)} />
              )}

              {publishError && <p className="error">{publishError}</p>}
              <button type="submit" className="btn-publish" disabled={publishLoading} style={{ justifyContent: 'center' }}>
                {publishLoading ? 'Publication...' : 'Publier'}
              </button>
            </form>
          </div>
        )}

        {marketplaceListings.length === 0 ? (
          <div className="marketplace-empty">
            <p>Aucune application publiée pour le moment.</p>
          </div>
        ) : (
          <div className="marketplace-grid">
            {marketplaceListings.map((l) => {
              const openLink = l.source_type === 'externe_lien' ? l.lien_externe : `https://favor-legendary-edge-cultural.trycloudflare.com/api/marketplace/${l.id}/preview`;
              const copyLink = () => {
                navigator.clipboard.writeText(openLink).catch(() => {});
              };
              const bannerUrl = l.image_url && l.image_url.startsWith('/') ? `https://favor-legendary-edge-cultural.trycloudflare.com${l.image_url}` : l.image_url;
              return (
                <div key={l.id} className="marketplace-card">
                  {bannerUrl && (
                    <div className="marketplace-card-banner">
                      <img
                        src={bannerUrl}
                        alt=""
                        onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = 'none'; }}
                      />
                    </div>
                  )}
                  <div className="marketplace-card-icon">
                    {l.favicon_url ? (
                      <>
                        <img
                          src={l.favicon_url}
                          alt=""
                          width="24"
                          height="24"
                          onError={(e) => {
                            const img = e.currentTarget;
                            img.style.display = 'none';
                            const fallback = img.nextElementSibling as HTMLElement;
                            if (fallback) fallback.style.display = 'flex';
                          }}
                        />
                        <span style={{ display: 'none' }}>{sourceIcon(l.source_type)}</span>
                      </>
                    ) : sourceIcon(l.source_type)}
                  </div>
                  <h3>{l.titre}</h3>
                  <p className="marketplace-card-desc">{l.description}</p>
                  <div className="marketplace-card-footer">
                    <span className="marketplace-price">{(l.prix_centimes / 100).toFixed(2)} {l.devise}</span>
                    <span className="marketplace-badge">{sourceLabel(l.source_type)}</span>
                  </div>
                  {l.source_type !== 'externe_zip' && (
                    <div className="marketplace-card-links">
                      <a href={openLink} target="_blank" rel="noopener noreferrer" className="marketplace-link-btn">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                        Ouvrir
                      </a>
                      <button type="button" onClick={copyLink} className="marketplace-link-btn">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                        Copier
                      </button>
                    </div>
                  )}
                  {l.vendeur_id !== user.id && (
                    <button
                      type="button"
                      className="btn-publish"
                      style={{ marginTop: '0.5rem', justifyContent: 'center', width: '100%' }}
                      disabled={purchaseLoadingId === l.id}
                      onClick={() => handlePurchase(l.id)}
                    >
                      {purchaseLoadingId === l.id ? 'Achat...' : 'Acheter'}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
        <div style={{ padding: '1.5rem', textAlign: 'center', fontSize: '0.8rem', color: '#a89f8c' }}>
          <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setShowLegal('cgv')}>Conditions Générales de Vente</span>
          {' · '}
          <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setShowLegal('mentions')}>Mentions légales</span>
        </div>
      </div>
    );
  }

  // Vue paramètres
  if (showSettings) {
    return (
      <div className="dashboard">
        <header>
          <h1 onClick={() => { setShowSettings(false); navigateTo('/'); }} style={{ cursor: 'pointer' }}>← GNB41 IA</h1>
          <div>
            <NotificationBell />
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>
        <main>
          <h2>Paramètres du compte</h2>
          <form onSubmit={handleUpdateSettings} className="auth-form" style={{ margin: '1rem 0' }}>
            <input placeholder="Email" type="email" value={settingsEmail} onChange={(e) => setSettingsEmail(e.target.value)} />
            <input placeholder="Nouveau mot de passe (optionnel)" type="password" value={settingsPassword} onChange={(e) => setSettingsPassword(e.target.value)} />
            <input placeholder="Mot de passe actuel (requis)" type="password" value={settingsCurrentPassword} onChange={(e) => setSettingsCurrentPassword(e.target.value)} required />
            {settingsError && <p className="error">{settingsError}</p>}
            {settingsMsg && <p className="success">{settingsMsg}</p>}
            <button type="submit">Enregistrer</button>
          </form>
        </main>
      </div>
    );
  }

  // Vue détail projet (chat + aperçu live)
  if (activeProject) {
    const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = reader.result as string;
          const base64 = dataUrl.split(',')[1];
          setAttachedImage({ data: base64, mediaType: file.type, name: file.name });
        };
        reader.readAsDataURL(file);
        e.target.value = '';
        return;
      }

      const textExtensions = ['.txt', '.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css', '.json', '.md', '.csv'];
      const isTextFile = textExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
      if (!isTextFile) {
        alert("Type de fichier non supporté. Utilisez une image, ou un fichier texte/code (.txt, .js, .py, .html, .css, .json, .md, .csv).");
        e.target.value = '';
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        const fence = String.fromCharCode(96, 96, 96);
        const bloc = 'Fichier joint "' + file.name + '":\n' + fence + '\n' + text + '\n' + fence + '\n\n';
        setChatInput((prev) => bloc + prev);
      };
      reader.readAsText(file);
      e.target.value = '';
    };

    const toggleVoiceInput = () => {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("La reconnaissance vocale n'est pas supportée par ce navigateur.");
        return;
      }
      if (isListening) {
        setIsListening(false);
        return;
      }
      const recognition = new SpeechRecognition();
      recognition.lang = 'fr-FR';
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setChatInput((prev) => (prev ? prev + ' ' + transcript : transcript));
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);

      recognition.start();
      setIsListening(true);
    };

    const handleShare = () => {
      const url = `${window.location.origin}/?project=${activeProject.id}`;
      navigator.clipboard.writeText(url).then(() => {
        alert('Lien du projet copié dans le presse-papiers !');
      }).catch(() => {});
    };

    const handleDuplicate = async () => {
      try {
        const copy = await api.duplicateProject(activeProject.id);
        setProjects([...projects, copy]);
        setActiveProject(copy);
        alert('Projet dupliqué avec succès.');
      } catch (err: any) {
        alert(`Erreur: ${err.message}`);
      }
    };

    const copyMessage = (text: string) => {
      navigator.clipboard.writeText(text).catch(() => {});
    };

    const toggleVersions = () => {
      if (!showVersions) {
        api.listVersions(activeProject.id).then(setVersions).catch(() => {});
      }
      setShowVersions(!showVersions);
    };

    const runGeneration = async (messageText: string, imageToSend: typeof attachedImage) => {
      setChatMessages((prev) => [...prev, { role: 'user', content: messageText, created_at: new Date().toISOString(), hasImage: !!imageToSend }]);
      setChatLoading(true);
      try {
        const result = await api.chatProject(activeProject.id, messageText, chatProvider, imageToSend || undefined);
        setActiveProject(result.project);
        setProjects(projects.map((p) => (p.id === result.project.id ? result.project : p)));
        setChatMessages((prev) => [...prev, result.assistant_message]);
      } catch (err: any) {
        setChatMessages((prev) => [...prev, { role: 'assistant', content: `Erreur: ${err.message}`, created_at: new Date().toISOString() }]);
      } finally {
        setChatLoading(false);
      }
    };

    const sendChat = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!chatInput.trim() && !attachedImage) return;
      const messageText = chatInput || '(voir image jointe)';
      const imageToSend = attachedImage;
      setChatInput('');
      setAttachedImage(null);
      await runGeneration(messageText, imageToSend);
    };

    let parsedFiles: any = null;
    if (activeProject.code_genere) {
      try { parsedFiles = JSON.parse(activeProject.code_genere); } catch {}
    }

    const previewContent = (() => {
      if (!parsedFiles || !parsedFiles.fichiers) return null;
      const htmlFile = parsedFiles.fichiers.find((f: any) => f.chemin.endsWith('.html'));
      return htmlFile ? htmlFile.contenu : null;
    })();

    return (
      <div className="workspace-builder">
      {showUpgradeModal && (
        <div className="modal-overlay" onClick={() => setShowUpgradeModal(false)}>
          <div className="upgrade-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowUpgradeModal(false)}>×</button>
            <h2>Choisissez votre plan</h2>
            <p className="modal-subtitle">Le paiement n'est pas encore disponible — ceci est un aperçu des offres à venir.</p>
            <div className="plans-grid">
              <div className="plan-card">
                <h3>Gratuit</h3>
                <p className="plan-price">0€<span>/mois</span></p>
                <ul>
                  <li>3 projets par espace de travail</li>
                  <li>1 espace de travail</li>
                  <li>Génération IA limitée</li>
                </ul>
                <button className="plan-btn plan-btn-current" disabled>Plan actuel</button>
              </div>
              <div className="plan-card plan-card-highlight">
                <span className="plan-badge">Populaire</span>
                <h3>Pro</h3>
                <p className="plan-price">19€<span>/mois</span></p>
                <ul>
                  <li>Projets illimités</li>
                  <li>Espaces de travail illimités</li>
                  <li>Tous les fournisseurs IA</li>
                  <li>Support prioritaire</li>
                </ul>
                <button className="plan-btn plan-btn-primary" disabled={upgradeLoading} onClick={() => handleUpgrade('pro')}>{upgradeLoading ? 'Redirection...' : 'Passer au Pro'}</button>
              </div>
              <div className="plan-card">
                <h3>Entreprise</h3>
                <p className="plan-price">Sur devis</p>
                <ul>
                  <li>Tout Pro inclus</li>
                  <li>Déploiement dédié</li>
                  <li>SLA garanti</li>
                </ul>
                <button className="plan-btn" disabled>Nous contacter</button>
              </div>
            </div>
          </div>
        </div>
      )}
        <header>
          <div>
            <button className="toolbar-icon-btn" title="Retour" onClick={() => { setActiveProject(null); navigateTo('/'); }}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
            </button>
            <span>{activeProject.nom}</span>
            <button className="toolbar-icon-btn" title="Partager" onClick={handleShare}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
            </button>
            <button className="toolbar-icon-btn" title="Dupliquer" onClick={handleDuplicate}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
            <button className="toolbar-icon-btn" title="Historique des versions" onClick={toggleVersions}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
            </button>
            <a href={api.exportProjectUrl(activeProject.id)} className="toolbar-icon-btn" title="Télécharger (.zip)" download>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </a>
            <button className="toolbar-icon-btn" title="Paramètres du workspace" onClick={() => setShowWorkspaceSettings(true)}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            </button>
          </div>
        </header>

        {showWorkspaceSettings && (
          <div className="ws-settings-overlay" onClick={() => setShowWorkspaceSettings(false)}>
            <div className="ws-settings-panel" onClick={(e) => e.stopPropagation()}>
              <div className="ws-settings-header">
                <h3>Paramètres du workspace</h3>
                <button className="modal-close" onClick={() => setShowWorkspaceSettings(false)}>×</button>
              </div>
              <div className="ws-settings-tabs">
                <button className={workspaceSettingsTab === 'membres' ? 'active' : ''} onClick={() => setWorkspaceSettingsTab('membres')}>Membres</button>
                <button className={workspaceSettingsTab === 'activite' ? 'active' : ''} onClick={() => setWorkspaceSettingsTab('activite')}>Activité</button>
                <button className={workspaceSettingsTab === 'general' ? 'active' : ''} onClick={() => setWorkspaceSettingsTab('general')}>Général</button>
              </div>
              <div className="ws-settings-content">
                {workspaceSettingsTab === 'membres' && (
                  <>
                    {activeWorkspace?.owner_id === user.id && (
                      <form onSubmit={handleWsInvite} className="new-workspace-form">
                        <input placeholder="Email à inviter" type="email" value={wsInviteEmail} onChange={(e) => setWsInviteEmail(e.target.value)} />
                        <select value={wsInviteRole} onChange={(e) => setWsInviteRole(e.target.value)} className="role-select">
                          <option value="editeur">Éditeur</option>
                          <option value="lecteur">Lecteur</option>
                        </select>
                        <button type="submit">Inviter</button>
                      </form>
                    )}
                    {wsInviteError && <p className="error">{wsInviteError}</p>}
                    <ul className="members-list">
                      {wsMembers.map((m) => (
                        <li key={m.user_id}>
                          <span>{m.username} ({m.email}) — {m.role}</span>
                          {activeWorkspace?.owner_id === user.id && m.role !== 'owner' && (
                            <button className="delete-btn" onClick={() => handleWsRemoveMember(m.user_id)}>×</button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {workspaceSettingsTab === 'activite' && (
                  <ul className="activity-list">
                    {wsActivityLogs.length === 0 && <li>Aucune activité récente</li>}
                    {wsActivityLogs.map((log) => {
                      const labels: Record<string, string> = {
                        project_created: 'a créé le projet',
                        project_deleted: 'a supprimé le projet',
                        member_added: 'a invité',
                        member_removed: 'a retiré',
                      };
                      const label = labels[log.action] || log.action;
                      return (
                        <li key={log.id}>
                          <strong>{log.username}</strong> {label} {log.details && <em>{log.details}</em>}
                          <span className="activity-date"> — {new Date(log.created_at).toLocaleString('fr-FR')}</span>
                        </li>
                      );
                    })}
                  </ul>
                )}
                {workspaceSettingsTab === 'general' && (
                  <div className="ws-general">
                    <p><strong>Nom :</strong> {activeWorkspace?.nom}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="preview-tabs">
          <button className={`preview-tab ${previewTab === 'apercu' ? 'active' : ''}`} onClick={() => setPreviewTab('apercu')}>Aperçu</button>
          <button className={`preview-tab ${previewTab === 'code' ? 'active' : ''}`} onClick={() => setPreviewTab('code')}>Code</button>
          <button className={`preview-tab ${previewTab === 'donnees' ? 'active' : ''}`} onClick={() => { setPreviewTab('donnees'); if (activeProject) { api.listAppTables(activeProject.id).then(setAppTables).catch(() => {}); api.listAppKeys(activeProject.id).then(setAppKeys).catch(() => {}); } }}>Base de donnees</button>
        </div>

        {showVersions && (
          <div className="detail-section versions-panel">
            <ul className="versions-list">
              {versions.map((v) => (
                <li key={v.id}>
                  <span className={`statut statut-${v.statut}`}>{v.statut}</span>
                  <p>{v.prompt}</p>
                  <span className="version-date">{new Date(v.created_at).toLocaleString('fr-FR')}</span>
                </li>
              ))}
              {versions.length === 0 && <p>Aucune version dans l'historique.</p>}
            </ul>
          </div>
        )}

        <div className="builder-layout">
          <div className="builder-chat">
            <p className={`statut statut-${activeProject.statut}`}>{activeProject.statut}</p>

            <div className="chat-messages">
              <div className="chat-msg chat-msg-user">
                <p>{activeProject.prompt_initial}</p>
              </div>
              {chatMessages.map((m, i) => (
                <div key={i} className={`chat-msg chat-msg-${m.role} ${m.pending ? 'pending-msg' : ''}`}>
                  <p>{(() => {
                    if (m.role === 'assistant' && m.content.trim().startsWith('{') && m.content.includes('"fichiers"')) {
                      return "J'ai genere le code de votre application. Consultez l'apercu ou l'onglet Code ci-contre.";
                    }
                    return m.content;
                  })()}</p>
                  <div className="chat-msg-actions">
                    {m.created_at && <span className="msg-time">{new Date(m.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>}
                    <button type="button" className="msg-action-btn" title="Copier" onClick={() => copyMessage(m.content)}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="chat-msg chat-msg-assistant typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              )}
            </div>

            <form onSubmit={sendChat} className="chat-input-form">
              {attachedImage && (
                <div className="attached-image-preview">
                  <img src={`data:${attachedImage.mediaType};base64,${attachedImage.data}`} alt={attachedImage.name} />
                  <span>{attachedImage.name}</span>
                  <button type="button" onClick={() => setAttachedImage(null)}>×</button>
                </div>
              )}
              <textarea
                placeholder="Demandez une modification ou une nouvelle fonctionnalité..."
                value={chatInput}
                onChange={(e) => {
                  setChatInput(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
                }}
                rows={2}
                ref={(el) => { if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 200) + 'px'; } }}
              />
              <div className="chat-input-toolbar">
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  accept=".txt,.js,.jsx,.ts,.tsx,.py,.html,.css,.json,.md,.csv,image/*"
                  onChange={handleFileAttach}
                />
                <button type="button" className="icon-btn" title="Ajouter un fichier" onClick={() => fileInputRef.current?.click()}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>

                <div className="provider-dropdown">
                  <button type="button" className="provider-pill" onClick={() => setShowProviderMenu(!showProviderMenu)}>
                    {chatProvider === 'openai' ? 'GPT' : chatProvider === 'gemini' ? 'Gemini' : chatProvider === 'mistral' ? 'Mistral' : 'Claude'}
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="6 9 12 15 18 9"/></svg>
                  </button>
                  {showProviderMenu && (
                    <div className="provider-menu">
                      {[['claude', 'Claude (Anthropic)'], ['openai', 'GPT (OpenAI)'], ['gemini', 'Gemini (Google)'], ['mistral', 'Mistral (Mistral AI)']].map(([val, label]) => (
                        <button
                          type="button"
                          key={val}
                          className={`provider-menu-item ${chatProvider === val ? 'active' : ''}`}
                          onClick={() => { setChatProvider(val); setShowProviderMenu(false); }}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="toolbar-spacer" />

                <button type="button" className={`icon-btn ${isListening ? 'icon-btn-active' : ''}`} title="Message vocal" onClick={toggleVoiceInput}>
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                </button>

                <button type="submit" className="send-btn" disabled={chatLoading} title="Envoyer">
                  {chatLoading ? <div className="spinner"></div> : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
                  )}
                </button>
              </div>
            </form>
          </div>

          <div className="builder-preview">
            {activeProject.statut === 'erreur' ? (
              <div className="detail-section error-box">
                <h3>Erreur</h3>
                <p>{activeProject.erreur_message}</p>
              </div>
            ) : previewTab === 'apercu' ? (
              previewContent ? (
                <iframe
                  title="Aperçu"
                  srcDoc={previewContent}
                  className="preview-iframe"
                  sandbox="allow-scripts"
                />
              ) : (
                <div className="preview-empty">
                  <p>L'aperçu apparaîtra ici une fois l'application générée.</p>
                </div>
              )
            ) : previewTab === 'donnees' ? (
              <div className="code-editor-layout">
                <div className="code-editor-sidebar">
                  <p className="stack-badge">Tables</p>
                  {appTables.map((t: any) => (
                    <button
                      key={t.id}
                      type="button"
                      className={`code-editor-file-btn ${selectedTableId === t.id ? 'active' : ''}`}
                      onClick={() => {
                        setSelectedTableId(t.id);
                        api.listAppRows(t.id).then(setSelectedTableRows).catch(() => setSelectedTableRows([]));
                      }}
                    >
                      {t.nom}
                    </button>
                  ))}
                  {appTables.length === 0 && <p style={{ fontSize: '0.78rem', color: '#8a7f68', padding: '0.5rem' }}>Aucune table declaree pour ce projet.</p>}
                </div>
                <div className="code-editor-main">
                  <div className="code-editor-toolbar">
                    <span className="code-editor-filename">
                      {selectedTableId ? appTables.find((t: any) => t.id === selectedTableId)?.nom : 'Cles API'}
                    </span>
                  </div>
                  <div style={{ padding: '1rem', overflow: 'auto', flex: 1 }}>
                    {selectedTableId ? (
                      <>
                        <p style={{ fontSize: '0.8rem', color: '#8a7f68', marginBottom: '0.6rem' }}>{selectedTableRows.length} ligne(s)</p>
                        {selectedTableRows.map((row: any) => (
                          <pre key={row.id} className="code-block" style={{ fontSize: '0.75rem', marginBottom: '0.5rem' }}>{JSON.stringify(row.data, null, 2)}</pre>
                        ))}
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn-publish"
                          style={{ marginBottom: '1rem' }}
                          onClick={async () => {
                            if (!activeProject) return;
                            const res = await api.createAppKey(activeProject.id);
                            setNewKeyRevealed(res.key);
                            const keys = await api.listAppKeys(activeProject.id);
                            setAppKeys(keys);
                          }}
                        >
                          + Nouvelle cle API
                        </button>
                        {newKeyRevealed && (
                          <div style={{ padding: '0.8rem', background: darkMode ? '#4a3f1a' : '#fef3c7', color: darkMode ? '#f0e6c0' : 'inherit', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.78rem', wordBreak: 'break-all' }}>
                            Copiez cette cle maintenant, elle ne sera plus affichee : <strong>{newKeyRevealed}</strong>
                          </div>
                        )}
                        {appKeys.map((k: any) => (
                          <div key={k.id} className="admin-sales-row" style={{ gridTemplateColumns: '1fr auto' }}>
                            <span>{k.key_prefix}... {k.revoked ? '(revoquee)' : ''}</span>
                            {!k.revoked && (
                              <button
                                type="button"
                                className="marketplace-link-btn"
                                onClick={async () => {
                                  await api.revokeAppKey(k.id);
                                  if (activeProject) {
                                    const keys = await api.listAppKeys(activeProject.id);
                                    setAppKeys(keys);
                                  }
                                }}
                              >
                                Revoquer
                              </button>
                            )}
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : parsedFiles && parsedFiles.fichiers ? (
              <div className="code-editor-layout">
                <div className="code-editor-sidebar">
                  <p className="stack-badge">{parsedFiles.stack}</p>
                  {parsedFiles.fichiers.map((f: any, i: number) => (
                    <button
                      key={i}
                      type="button"
                      className={`code-editor-file-btn ${previewFile === f.chemin ? 'active' : ''}`}
                      onClick={() => {
                        if (editorDirty && previewFile && !confirm('Modifications non enregistrees. Changer de fichier quand meme ?')) return;
                        setPreviewFile(f.chemin);
                        setEditorContent(f.contenu);
                        setEditorDirty(false);
                      }}
                    >
                      {f.chemin}
                    </button>
                  ))}
                </div>
                <div className="code-editor-main">
                  {previewFile ? (
                    <>
                      <div className="code-editor-toolbar">
                        <span className="code-editor-filename">{previewFile}</span>
                        <button
                          type="button"
                          className="btn-publish"
                          disabled={!editorDirty || editorSaving}
                          onClick={async () => {
                            if (!activeProject || !previewFile) return;
                            setEditorSaving(true);
                            try {
                              const updated = await api.updateFile(activeProject.id, previewFile, editorContent);
                              setActiveProject(updated);
                              setProjects(projects.map((p) => (p.id === updated.id ? updated : p)));
                              setEditorDirty(false);
                            } catch (err: any) {
                              alert(`Erreur: ${err.message}`);
                            } finally {
                              setEditorSaving(false);
                            }
                          }}
                        >
                          {editorSaving ? 'Enregistrement...' : editorDirty ? 'Enregistrer' : 'Enregistre'}
                        </button>
                      </div>
                      <textarea
                        className="code-editor-textarea"
                        value={editorContent}
                        onChange={(e) => { setEditorContent(e.target.value); setEditorDirty(true); }}
                        spellCheck={false}
                      />
                    </>
                  ) : (
                    <div className="preview-empty">
                      <p>Selectionnez un fichier a gauche pour l'editer.</p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="preview-empty">
                <p>Le code apparaîtra ici une fois l'application générée.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
  // Vue liste projets d'un workspace

  // Vue accueil rapide (type Base44) - écran unique après connexion
  return (
    <div className="dashboard">
      {showUpgradeModal && (
        <div className="modal-overlay" onClick={() => setShowUpgradeModal(false)}>
          <div className="upgrade-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowUpgradeModal(false)}>×</button>
            <h2>Choisissez votre plan</h2>
            <p className="modal-subtitle">Le paiement n'est pas encore disponible — ceci est un aperçu des offres à venir.</p>
            <div className="plans-grid">
              <div className="plan-card">
                <h3>Gratuit</h3>
                <p className="plan-price">0€<span>/mois</span></p>
                <ul>
                  <li>3 projets par espace de travail</li>
                  <li>1 espace de travail</li>
                  <li>Génération IA limitée</li>
                </ul>
                <button className="plan-btn plan-btn-current" disabled>Plan actuel</button>
              </div>
              <div className="plan-card plan-card-highlight">
                <span className="plan-badge">Populaire</span>
                <h3>Pro</h3>
                <p className="plan-price">19€<span>/mois</span></p>
                <ul>
                  <li>Projets illimités</li>
                  <li>Espaces de travail illimités</li>
                  <li>Tous les fournisseurs IA</li>
                  <li>Support prioritaire</li>
                </ul>
                <button className="plan-btn plan-btn-primary" disabled={upgradeLoading} onClick={() => handleUpgrade('pro')}>{upgradeLoading ? 'Redirection...' : 'Passer au Pro'}</button>
              </div>
              <div className="plan-card">
                <h3>Entreprise</h3>
                <p className="plan-price">Sur devis</p>
                <ul>
                  <li>Tout Pro inclus</li>
                  <li>Déploiement dédié</li>
                  <li>SLA garanti</li>
                </ul>
                <button className="plan-btn" disabled>Nous contacter</button>
              </div>
            </div>
          </div>
        </div>
      )}
      <header className="header-minimal">
        <button className="hamburger-btn" onClick={() => setShowMenu(!showMenu)} aria-label="Menu">
          <span></span><span></span><span></span>
        </button>
        <img src="/logo.png" alt="GNB41 IA" className="app-logo-center" />
        <div className="header-spacer" />
        {showMenu && (
          <>
            <div className="menu-overlay" onClick={() => setShowMenu(false)} />
            <nav className="side-menu">
              <div className="side-menu-user">
                <span className="side-menu-username">{user.username}</span>
                {user.plan === 'pro' && user.plan_expiry && (
                  <span className="side-menu-plan">Pro jusqu'au {new Date(user.plan_expiry).toLocaleDateString('fr-FR')}</span>
                )}
              </div>
              <NotificationBell />
              <button className="side-menu-item upgrade-btn" onClick={() => { setShowMenu(false); setShowUpgradeModal(true); }}>✦ Mettre à niveau</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); }}>Accueil</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); document.querySelector('.recent-section')?.scrollIntoView({ behavior: 'smooth' }); }}>Projets</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); setShowMarketplace(true); setShowSettings(false); navigateTo('/marketplace'); }}>Boutique</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); setShowSettings(true); navigateTo('/parametres'); }}>Paramètres</button>
              <button className="side-menu-item" onClick={() => setDarkMode(!darkMode)}>{darkMode ? '☀️ Mode clair' : '🌙 Mode sombre'}</button>
              <button className="side-menu-item side-menu-logout" onClick={handleLogout}>Déconnexion</button>
            </nav>
          </>
        )}
      </header>

      <main className="quickstart-main">
        <h2 className="quickstart-greeting">Bonjour {user.username}. <span className="accent-dot">•</span><br/>Que construirez-vous ensuite ?</h2>

        <form onSubmit={handleQuickStart} className="quickstart-form">
          <div className="textarea-wrap">
            <textarea
              placeholder=""
              value={quickPrompt}
              onChange={(e) => {
                setQuickPrompt(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = e.target.scrollHeight + 'px';
              }}
              rows={2}
              className="auto-grow-textarea"
              ref={(el) => { if (el) { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; } }}
            />
            <AnimatedPlaceholder text="Décrivez l'application que vous souhaitez créer..." active={!quickPrompt} />
          </div>
          <div className="quickstart-toolbar">
            <button type="button" className="icon-btn"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></button>
            <select value={quickProvider} onChange={(e) => setQuickProvider(e.target.value)} className="provider-select">
              <option value="claude">Claude</option>
              <option value="openai">GPT</option>
              <option value="gemini">Gemini</option>
              <option value="mistral">Mistral</option>
            </select>
            <div className="toolbar-spacer" />
            <button type="submit" className="send-btn" disabled={quickLoading}>
              {quickLoading ? <div className="spinner"></div> : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
              )}
            </button>
          </div>
        </form>

        {recentProjects.length > 0 && (
          <div className="recent-section">
            <h3>Récents</h3>
            <div className="workspace-grid">
              {recentProjects.map((p: any) => (
                <div key={p.id} className="workspace-card" onClick={() => {
                  const ws = workspaces.find((w) => w.id === p.parentWorkspaceId);
                  if (ws) setActiveWorkspace(ws);
                  setActiveProject(p);
                  navigateTo(`/projet/${p.id}`);
                }}>
                  <div className="workspace-card-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
                  </div>
                  <h3>{p.nom}</h3>
                  <div className="workspace-card-footer">
                    <span className={`statut-badge statut-badge-${p.statut}`}>
                      {p.statut === 'genere' ? 'Prêt' : p.statut === 'en_generation' ? 'En cours' : p.statut === 'erreur' ? 'Erreur' : p.statut}
                    </span>
                    <span className="workspace-card-date">{new Date(p.created_at).toLocaleDateString('fr-FR')}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
