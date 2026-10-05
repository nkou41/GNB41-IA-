import { useState, useEffect, useRef, type ReactElement, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import NotificationBell from './components/NotificationBell';
import { formatDate, formatDateTime, formatShortDateTime, formatTime, parseServerDate } from './lib/time';
import PublicNav from './components/PublicNav';
import Apropos from './pages/Apropos';
import Contact from './pages/Contact';
import Fonctionnalites from './pages/Fonctionnalites';
import Tarifs from './pages/Tarifs';
import Studio from './pages/Studio';
import Templates from './pages/Templates';
import Boutique from './pages/Boutique';
import Accueil from './pages/Accueil';
import AnimatedPlaceholder from './components/AnimatedPlaceholder';
import { identifyUser, trackEvent, resetAnalytics } from './analytics';
import { api } from './api';
import './App.css';
import { IconUser, IconMail, IconLock, IconSave, IconLink, IconLogOut, IconCheckCircle, IconInfoCircle, IconEye, IconEyeOff, IconArrowRight, IconArrowLeft, IconSettings, IconGooglePlay, IconPackage, IconHome, IconStore, IconGrid, IconMoon, IconSun, IconKey } from './Icons';

interface User {
  id: string;
  username: string;
  email: string;
  plan?: string;
  plan_expiry?: string | null;
  credits?: number;
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
  est_deploye?: boolean;
  memoire_projet?: string;
}

const echapperRegex = (t: string) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function construireMiniature(code: any): string | null {
  if (!code || typeof code !== 'string') return null;
  const brut = code.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  let data: any = null;
  try { data = JSON.parse(brut); } catch {}
  let h: string | null = null;
  if (data && Array.isArray(data.fichiers)) {
    const fichiers: any[] = data.fichiers;
    const page = fichiers.find((f) => typeof f.chemin === 'string' && f.chemin.endsWith('.html'));
    if (!page || typeof page.contenu !== 'string') return null;
    h = page.contenu as string;
    const nom = (f: any) => echapperRegex(String(f.chemin).split('/').pop() || '');
    fichiers.filter((f) => String(f.chemin).endsWith('.css')).forEach((f) => {
      const lien = new RegExp(`<link[^>]+href=["'][^"']*${nom(f)}["'][^>]*>`, 'i');
      const balise = `<style>\n${f.contenu}\n</style>`;
      h = lien.test(h as string) ? (h as string).replace(lien, () => balise) : (h as string).replace('</head>', () => balise + '</head>');
    });
    fichiers.filter((f) => String(f.chemin).endsWith('.js')).forEach((f) => {
      const src = new RegExp(`<script[^>]+src=["'][^"']*${nom(f)}["'][^>]*></script>`, 'i');
      const balise = `<script>\n${f.contenu}\n</script>`;
      h = src.test(h as string) ? (h as string).replace(src, () => balise) : (h as string).replace('</body>', () => balise + '</body>');
    });
  } else if (/<html|<!doctype/i.test(brut)) {
    h = brut;
  }
  if (!h) return null;
  const polyfill = '<script>try{window.localStorage.getItem("t")}catch(e){var m=function(){var d={};return{getItem:function(k){return d.hasOwnProperty(k)?d[k]:null},setItem:function(k,v){d[k]=String(v)},removeItem:function(k){delete d[k]},clear:function(){d={}},key:function(i){return Object.keys(d)[i]||null},get length(){return Object.keys(d).length}}};try{Object.defineProperty(window,"localStorage",{value:m(),configurable:true})}catch(x){}try{Object.defineProperty(window,"sessionStorage",{value:m(),configurable:true})}catch(x){}}</script>';
  return h.includes('<head>') ? h.replace('<head>', () => '<head>' + polyfill) : polyfill + h;
}

function MiniatureApp({ code }: { code: any }) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0);
  const [visible, setVisible] = useState(false);
  const html = useMemo(() => construireMiniature(code), [code]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const maj = () => setScale(el.clientWidth / 1280);
    maj();
    const ro = new ResizeObserver(maj);
    ro.observe(el);
    const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) { setVisible(true); io.disconnect(); } }, { rootMargin: '200px' });
    io.observe(el);
    return () => { ro.disconnect(); io.disconnect(); };
  }, [html]);
  if (!html) return null;
  return (
    <div ref={ref} className="home-thumb-frame" aria-hidden="true">
      {visible && scale > 0 && <iframe title="" tabIndex={-1} sandbox="allow-scripts" srcDoc={html} style={{ transform: `scale(${scale})` }} />}
    </div>
  );
}


function messageAuth(msg: string): string {
  if (/failed to fetch|networkerror|load failed|network request failed/i.test(msg)) {
    return "Impossible de joindre le serveur. Vérifiez votre connexion et réessayez dans un instant.";
  }
  return msg;
}

const LIBELLES_STATUT: Record<string, string> = { en_attente: 'En attente', paye: 'Payé', complete: 'Terminé', termine: 'Terminé', publie: 'Publié', brouillon: 'Brouillon', retire: 'Retirée', echoue: 'Échoué', annule: 'Annulé', erreur: 'Erreur', en_revue: 'En revue', refuse: 'Refusée', suspendu: 'Suspendue' };

function libelleStatut(statut: string): string {
  const cle = String(statut || '').toLowerCase();
  if (LIBELLES_STATUT[cle]) return LIBELLES_STATUT[cle];
  const t = cle.replace(/_/g, ' ');
  return t.charAt(0).toUpperCase() + t.slice(1);
}

function tonStatut(statut: string): string {
  const cle = String(statut || '').toLowerCase();
  if (['en_attente', 'echoue', 'annule', 'erreur', 'refuse', 'retire', 'suspendu'].includes(cle)) return 'warn';
  if (['paye', 'complete', 'termine', 'publie', 'actif', 'active', 'livre'].includes(cle)) return 'ok';
  return 'info';
}

const API_URL_PUBLIQUE: string = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001/api';

const MOTIFS_REVUE: Record<string, string> = { marque_detectee: 'Marque détectée', signalement: 'Signalée', modification: 'Modifiée', retrait_office: "Retrait d'office" };
const STATUTS_REVUE: [string, string][] = [['en_attente', 'À examiner'], ['approuve', 'Approuvées'], ['refuse', 'Refusées'], ['retire', 'Retirées'], ['en_ligne', 'En ligne']];

function PanneauModeration() {
  const [statut, setStatut] = useState('en_attente');
  const [items, setItems] = useState<any[]>([]);
  const [annonces, setAnnonces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState('');
  const [motifs, setMotifs] = useState<Record<string, string>>({});
  const [occupe, setOccupe] = useState<string | null>(null);

  const lienApercu = (id: string) => `${API_URL_PUBLIQUE}/marketplace/${id}/preview`;

  const charger = (s: string) => {
    setLoading(true);
    setErreur('');
    const requete = s === 'en_ligne'
      ? api.listMarketplace().then((res: any) => { setAnnonces(res.listings || []); })
      : api.listReviews(s).then((res: any) => { setItems(res.reviews || []); });
    requete
      .catch((err: any) => { setItems([]); setAnnonces([]); setErreur(err.message); })
      .finally(() => setLoading(false));
  };
  useEffect(() => { charger(statut); }, [statut]);

  const decider = async (rv: any, decision: 'approuver' | 'refuser' | 'retirer') => {
    const motif = (motifs[rv.id] || '').trim();
    if (decision !== 'approuver' && motif.length < 5) {
      setErreur('Un motif de 5 caractères minimum est requis pour refuser ou retirer.');
      return;
    }
    const texte = {
      approuver: 'Approuver cette annonce ? Elle sera mise en ligne.',
      refuser: 'Refuser cette annonce ? Le vendeur sera notifié avec votre motif.',
      retirer: 'Retirer cette annonce ? Le vendeur sera notifié avec votre motif.',
    }[decision];
    if (!window.confirm(texte)) return;
    setOccupe(rv.id);
    setErreur('');
    try {
      await api.decideReview(rv.id, decision, motif);
      setItems((prev) => prev.filter((x) => x.id !== rv.id));
    } catch (err: any) {
      setErreur(err.message);
    } finally {
      setOccupe(null);
    }
  };

  const retirer = async (a: any) => {
    const motif = (motifs[a.id] || '').trim();
    if (motif.length < 5) {
      setErreur('Un motif de 5 caractères minimum est requis pour retirer une annonce.');
      return;
    }
    if (!window.confirm(`Retirer « ${a.titre} » ? Le vendeur sera notifié avec votre motif.`)) return;
    setOccupe(a.id);
    setErreur('');
    try {
      await api.retirerAnnonce(a.id, motif);
      setAnnonces((prev) => prev.filter((x) => x.id !== a.id));
    } catch (err: any) {
      setErreur(err.message);
    } finally {
      setOccupe(null);
    }
  };

  const date = (iso: string | null) => iso ? formatShortDateTime(iso) : '';
  const vide = statut === 'en_ligne' ? annonces.length === 0 : items.length === 0;

  return (
    <div className="mod-panel">
      <div className="mod-chips" role="tablist" aria-label="Statut des dossiers">
        {STATUTS_REVUE.map(([val, label]) => (
          <button key={val} type="button" role="tab" aria-selected={statut === val} className={statut === val ? 'active' : ''} onClick={() => setStatut(val)}>{label}</button>
        ))}
      </div>
      {erreur && <p className="mod-error" role="alert">{erreur}</p>}
      {loading ? (
        <p className="mod-empty">Chargement…</p>
      ) : vide ? (
        <p className="mod-empty">{statut === 'en_attente' ? 'Aucune annonce à examiner.' : statut === 'en_ligne' ? 'Aucune annonce en ligne.' : 'Aucun dossier dans cette catégorie.'}</p>
      ) : statut === 'en_ligne' ? (
        <div className="mod-list">
          {annonces.map((a) => (
            <article key={a.id} className="mod-card">
              <div className="mod-head">
                <h3>{a.titre}</h3>
                <span className="mod-badge">{(a.prix_centimes / 100).toFixed(2)} {a.devise}</span>
              </div>
              <p className="mod-meta">{[date(a.created_at), a.categorie].filter(Boolean).join(' · ')}</p>
              {a.description && <p className="mod-desc">{a.description}</p>}
              {a.source_type === 'gnb41' && (
                <a className="mod-link" href={lienApercu(a.id)} target="_blank" rel="noopener noreferrer">Voir l'application</a>
              )}
              <textarea
                className="mod-motif"
                rows={2}
                maxLength={1000}
                placeholder="Motif du retrait (obligatoire)"
                value={motifs[a.id] || ''}
                onChange={(e) => setMotifs({ ...motifs, [a.id]: e.target.value })}
              />
              <div className="mod-actions un">
                <button type="button" className="mod-no" disabled={occupe === a.id} onClick={() => retirer(a)}>Retirer l'annonce</button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="mod-list">
          {items.map((rv) => (
            <article key={rv.id} className="mod-card">
              <div className="mod-head">
                <h3>{rv.listing_titre || 'Annonce'}</h3>
                <span className="mod-badge">{MOTIFS_REVUE[rv.motif] || rv.motif}</span>
              </div>
              <p className="mod-meta">
                {rv.vendeur_email || 'Vendeur inconnu'} · {date(rv.created_at)}
                {rv.listing ? ` · ${(rv.listing.prix_centimes / 100).toFixed(2)} ${rv.listing.devise}` : ' · annonce supprimée'}
              </p>
              {rv.terme && <p className="mod-term">Détecté : {rv.terme}</p>}
              {rv.listing && rv.listing.description && <p className="mod-desc">{rv.listing.description}</p>}
              {rv.listing && rv.listing.source_type === 'gnb41' && (
                <a className="mod-link" href={lienApercu(rv.listing_id)} target="_blank" rel="noopener noreferrer">Voir l'application</a>
              )}
              {rv.justification && (
                <div className="mod-block">
                  <span>Justification du vendeur</span>
                  <p>{rv.justification}</p>
                </div>
              )}
              {rv.signalements && rv.signalements.length > 0 && (
                <div className="mod-block">
                  <span>Signalements ({rv.signalements.length})</span>
                  {rv.signalements.map((sg: any, i: number) => (
                    <p key={i}>{sg.motif}{sg.details ? ` : ${sg.details}` : ''}</p>
                  ))}
                </div>
              )}
              {statut === 'en_attente' ? (
                <>
                  <textarea
                    className="mod-motif"
                    rows={2}
                    maxLength={1000}
                    placeholder="Motif (obligatoire pour refuser ou retirer)"
                    value={motifs[rv.id] || ''}
                    onChange={(e) => setMotifs({ ...motifs, [rv.id]: e.target.value })}
                  />
                  <div className="mod-actions">
                    <button type="button" className="mod-ok" disabled={occupe === rv.id} onClick={() => decider(rv, 'approuver')}>Approuver</button>
                    <button type="button" className="mod-no" disabled={occupe === rv.id} onClick={() => decider(rv, 'refuser')}>Refuser</button>
                    <button type="button" className="mod-no" disabled={occupe === rv.id} onClick={() => decider(rv, 'retirer')}>Retirer</button>
                  </div>
                </>
              ) : (
                <p className="mod-decision">{rv.decision_motif || 'Aucun motif enregistré'}{rv.decided_at ? ` · ${date(rv.decided_at)}` : ''}</p>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
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
  const [adminTab, setAdminTab] = useState<'boutique' | 'moderation' | 'utilisateurs' | 'workspaces' | 'evaluation'>('boutique');
  const [adminUsers, setAdminUsers] = useState<any[]>([]);
  const [adminWorkspaces, setAdminWorkspaces] = useState<any[]>([]);
  const [adminUsersLoading, setAdminUsersLoading] = useState(false);
  const [adminWorkspacesLoading, setAdminWorkspacesLoading] = useState(false);
  const [adminEvalSuites, setAdminEvalSuites] = useState<any[]>([]);
  const [adminEvalLoading, setAdminEvalLoading] = useState(false);
  const [adminEvalRunning, setAdminEvalRunning] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showMarketplace, setShowMarketplace] = useState(false);
  const [showStudio, setShowStudio] = useState(false);
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
  const [publishDroits, setPublishDroits] = useState(false);
  const [publishJustification, setPublishJustification] = useState('');
  const [publishNeedsJustif, setPublishNeedsJustif] = useState(false);
  const [report, setReport] = useState<{ target: any; motif: string; details: string; msg: string; ok: boolean; loading: boolean } | null>(null);
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
  const [liveUrl, setLiveUrl] = useState<string | null>(null);
  const [deployLoading, setDeployLoading] = useState(false);
  const [showPublishTemplate, setShowPublishTemplate] = useState(false);
  const [templateNom, setTemplateNom] = useState('');
  const [templateDesc, setTemplateDesc] = useState('');
  const [templateCategorie, setTemplateCategorie] = useState('autre');
  const [templatePublishing, setTemplatePublishing] = useState(false);
  const [showTemplatesGallery, setShowTemplatesGallery] = useState(false);
  const [publicPage, setPublicPage] = useState<'accueil' | 'fonctionnalites' | 'tarifs' | 'templates' | 'apropos' | 'contact' | 'boutique' | null>(null);
  const [publicListings, setPublicListings] = useState<any[]>([]);
  const [showPublicMenu, setShowPublicMenu] = useState(false);
  const [templatesList, setTemplatesList] = useState<any[]>([]);
  const [templatePreviews, setTemplatePreviews] = useState<Record<string, string>>({});
  useEffect(() => {
    if (!showTemplatesGallery || Object.keys(templatePreviews).length > 0) return;
    api.listTemplatePreviews().then((d: any) => { if (d && typeof d === 'object') setTemplatePreviews(d); }).catch(() => {});
  }, [showTemplatesGallery]);
  const [plansList, setPlansList] = useState<any[]>([]);

  useEffect(() => {
    api.getPlans().then((res: any) => setPlansList(res.plans || [])).catch(() => {});
  }, []);
  const [editorContent, setEditorContent] = useState<string>('');
  const [editorSaving, setEditorSaving] = useState(false);
  const [editorDirty, setEditorDirty] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [attachedImage, setAttachedImage] = useState<{ data: string; mediaType: string; name: string } | null>(null);
  const [showProviderMenu, setShowProviderMenu] = useState(false);
  const [showAgentModeMenu, setShowAgentModeMenu] = useState(false);
  const [chatProvider, setChatProvider] = useState('mistral');
  const [previewTab, setPreviewTab] = useState<'apercu' | 'code' | 'donnees' | 'memoire'>('apercu');
  const [memoireDraft, setMemoireDraft] = useState('');
  const [memoireMsg, setMemoireMsg] = useState('');
  const [erreursPreview, setErreursPreview] = useState<string[]>([]);
  const [appTables, setAppTables] = useState<any[]>([]);
  const [appKeys, setAppKeys] = useState<any[]>([]);
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null);
  const [selectedTableRows, setSelectedTableRows] = useState<any[]>([]);
  const [newKeyRevealed, setNewKeyRevealed] = useState<string | null>(null);
  const [quickPrompt, setQuickPrompt] = useState('');
  const [quickProvider, setQuickProvider] = useState('mistral');
  const [agentMode, setAgentMode] = useState('auto');
  const [quickLoading, setQuickLoading] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [darkMode, setDarkMode] = useState<boolean>(() => localStorage.getItem('theme') === 'dark');
  const [ouvertureId, setOuvertureId] = useState<string | number | null>(null);
  const [menuProjetId, setMenuProjetId] = useState<string | number | null>(null);
  const [vueMobile, setVueMobile] = useState<'chat' | 'apercu'>('apercu');
  useEffect(() => { if (activeProject?.id) setVueMobile('apercu'); }, [activeProject?.id]); // studio-ouvre-apercu
  const [menuStudio, setMenuStudio] = useState(false);

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
  const [landingModel, setLandingModel] = useState('mistral');
  const [recentProjects, setRecentProjects] = useState<any[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');


  const [settingsEmail, setSettingsEmail] = useState('');
  const [googlePlayStatut, setGooglePlayStatut] = useState<any | null>(null);
  const [googlePlayLoading, setGooglePlayLoading] = useState(false);
  const [googlePlayPackageInput, setGooglePlayPackageInput] = useState('');
  const [afficherNouveauMdp, setAfficherNouveauMdp] = useState(false);
  const [afficherMdpActuel, setAfficherMdpActuel] = useState(false);
  const [afficherMdpAuth, setAfficherMdpAuth] = useState(false);
  const [settingsPassword, setSettingsPassword] = useState('');
  const [settingsCurrentPassword, setSettingsCurrentPassword] = useState('');
  const [settingsMsg, setSettingsMsg] = useState('');
  const [settingsError, setSettingsError] = useState('');


  useEffect(() => {
    api.me().then(setUser).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const ecouteurErreurs = (event: MessageEvent) => {
      if (event.data && event.data.source === 'gnb41-preview-error') {
        setErreursPreview((prev) => [...prev.slice(-9), event.data.message]);
      }
    };
    window.addEventListener('message', ecouteurErreurs);
    return () => window.removeEventListener('message', ecouteurErreurs);
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

  const navigate = useNavigate();
  const location = useLocation();
  const navigateTo = (path: string) => {
    navigate(path);
  };

  useEffect(() => {
    const path = location.pathname;
    const syncMap: Record<string, () => void> = {
      '/': () => { setPublicPage(null); setShowAdminDashboard(false); setShowMarketplace(false); setShowMesAchats(false); setShowMesVentes(false); setShowSettings(false); },
      '/a-propos': () => setPublicPage('apropos'),
      '/fonctionnalites': () => setPublicPage('fonctionnalites'),
      '/tarifs': () => setPublicPage('tarifs'),
      '/templates': () => { setPublicPage('templates'); api.listTemplates().then(setTemplatesList).catch(() => {}); },
      '/boutique': () => { setPublicPage('boutique'); api.listMarketplace().then((res: any) => setPublicListings(res.listings)).catch(() => {}); },
      '/contact': () => setPublicPage('contact'),
      '/administration': () => setShowAdminDashboard(true),
      '/marketplace': () => setShowMarketplace(true),
      '/studio': () => setShowStudio(true),
      '/mes-achats': () => setShowMesAchats(true),
      '/mes-ventes': () => setShowMesVentes(true),
      '/parametres': () => setShowSettings(true),
    };
    const action = syncMap[path];
    if (action) {
      action();
    } else if (!path.startsWith('/projet/')) {
      setActiveProject(null);
    }
  }, [location.pathname]);

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
    if (showSettings) {
      setGooglePlayLoading(true);
      api.googlePlayStatut().then(setGooglePlayStatut).catch(() => {}).finally(() => setGooglePlayLoading(false));
    }
  }, [showSettings]);

  useEffect(() => {
    if (showAdminDashboard) {
      api.adminDashboard().then(setAdminStats).catch(() => {});
    }
  }, [showAdminDashboard]);

  useEffect(() => {
    if (showAdminDashboard && adminTab === 'utilisateurs') {
      setAdminUsersLoading(true);
      api.adminListUsers().then((res) => setAdminUsers(res.users)).catch(() => {}).finally(() => setAdminUsersLoading(false));
    }
    if (showAdminDashboard && adminTab === 'workspaces') {
      setAdminWorkspacesLoading(true);
      api.adminListWorkspaces().then((res) => setAdminWorkspaces(res.workspaces)).catch(() => {}).finally(() => setAdminWorkspacesLoading(false));
    }
    if (showAdminDashboard && adminTab === 'evaluation') {
      setAdminEvalLoading(true);
      api.adminEvaluationHistory().then((res) => setAdminEvalSuites(res.suites)).catch(() => {}).finally(() => setAdminEvalLoading(false));
    }
  }, [showAdminDashboard, adminTab]);

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
      const project = await api.createProject(targetWorkspace.id, '', quickPrompt, quickProvider, agentMode === 'auto' ? undefined : agentMode);
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

  const [upgradingPlan, setUpgradingPlan] = useState<string | null>(null);

  const handleUpgrade = async (plan: string) => {
    setUpgradingPlan(plan);
    try {
      const res = await api.createPayment(plan);
      window.location.href = res.payment_url;
    } catch (err: any) {
      alert(err.message || "Erreur lors de la creation du paiement");
      setUpgradingPlan(null);
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

  const handleReport = async () => {
    if (!report) return;
    if (report.motif === 'autre' && report.details.trim().length < 10) {
      setReport({ ...report, msg: 'Précisez votre signalement (10 caractères minimum).', ok: false });
      return;
    }
    setReport({ ...report, loading: true, msg: '' });
    try {
      await api.reportListing(report.target.id, report.motif, report.details);
      setReport((r) => r && { ...r, loading: false, ok: true, msg: 'Merci, votre signalement a été enregistré.' });
      setTimeout(() => setReport(null), 1800);
    } catch (err: any) {
      setReport((r) => r && { ...r, loading: false, ok: false, msg: err.message });
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
    if (!publishDroits) {
      setPublishError('Vous devez certifier détenir les droits sur cette application.');
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
      formData.append('droits_certifies', '1');
      if (publishNeedsJustif) formData.append('justification', publishJustification);

      const created: any = await api.createListing(formData);
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
      setPublishDroits(false);
      setPublishJustification('');
      setPublishNeedsJustif(false);
      if (created && created.statut === 'en_revue') alert('Votre annonce a été envoyée pour examen. Vous serez notifié de la décision.');
      const res = await api.listMarketplace();
      setMarketplaceListings(res.listings);
    } catch (err: any) {
      if (/marque prot[ée]g[ée]e/i.test(String(err.message)) && /justification/i.test(String(err.message))) setPublishNeedsJustif(true);
      setPublishError(err.message);
    } finally {
      setPublishLoading(false);
    }
  };

  if (loading) return (
    <div className="dashboard">
      <div className="skeleton-header">
        <div className="skeleton-block skeleton-hamburger" />
        <div className="skeleton-block skeleton-logo" />
        <div className="skeleton-block skeleton-spacer-el" />
      </div>
      <main className="quickstart-main">
        <div className="skeleton-block skeleton-greeting" />
        <div className="skeleton-block skeleton-form" />
        <div className="skeleton-block skeleton-section-title" />
        <div className="workspace-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="workspace-card skeleton-card">
              <div className="skeleton-block skeleton-card-icon" />
              <div className="skeleton-block skeleton-card-title" />
              <div className="skeleton-block skeleton-card-footer" />
            </div>
          ))}
        </div>
      </main>
    </div>
  );

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
    const navProps = { setPublicPage, navigateTo, setShowAuth, setAuthMode, setTemplatesList, setPublicListings, showPublicMenu, setShowPublicMenu };
    const publicPageRegistry: Record<string, ReactElement> = {
      fonctionnalites: <Fonctionnalites navProps={navProps} />,
      tarifs: <Tarifs navProps={navProps} plansList={plansList} />,
      templates: <Templates navProps={navProps} templatesList={templatesList} />,
      boutique: <Boutique navProps={navProps} publicListings={publicListings} />,
      apropos: <Apropos navProps={navProps} />,
      contact: <Contact navProps={navProps} />,
    };
    if (publicPage && publicPageRegistry[publicPage]) {
      return publicPageRegistry[publicPage];
    }
    return (
      <Accueil
        navProps={navProps}
        landingPrompt={landingPrompt}
        setLandingPrompt={setLandingPrompt}
        landingModel={landingModel}
        setLandingModel={setLandingModel}
        agentMode={agentMode}
        setAgentMode={setAgentMode}
        handleLandingSubmit={handleLandingSubmit}
      />
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
        <div className="auth-card">
          <h1 className="auth-card-logo" onClick={() => { setShowAuth(false); setShowForgotPassword(false); }} style={{ cursor: "pointer" }}>GNB41 IA</h1>
          <form onSubmit={handleForgotSubmit} className="auth-form auth-form-v2">
            <h2>Mot de passe oublie</h2>
            <div className="settings-input-pill-wrap">
              <label><IconMail size={16} /> Email</label>
              <input placeholder="Email" type="email" value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} required />
            </div>
            {forgotMessage && <p className="error">{forgotMessage}</p>}
            <button type="submit" className="auth-submit-btn">
              Envoyer le lien <IconArrowRight size={16} />
            </button>
            <p className="switch" onClick={() => { setShowForgotPassword(false); setForgotMessage(""); }}>
              Retour a la connexion
            </p>
          </form>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1 className="auth-card-logo" onClick={() => setShowAuth(false)} style={{ cursor: "pointer" }}>GNB41 IA</h1>
          <form onSubmit={handleAuth} className="auth-form auth-form-v2">
            <h2>{authMode === "login" ? "Connexion" : "Inscription"}</h2>
            <div className="settings-input-pill-wrap">
              <label><IconUser size={16} /> Nom d'utilisateur</label>
              <input placeholder="Nom d'utilisateur" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>
            {authMode === "register" && (
              <div className="settings-input-pill-wrap">
                <label><IconMail size={16} /> Email</label>
                <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
            )}
            <div className="settings-input-pill-wrap">
              <label><IconLock size={16} /> Mot de passe</label>
              <input placeholder="Mot de passe" type={afficherMdpAuth ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} required />
              <button type="button" className="settings-input-trailing" onClick={() => setAfficherMdpAuth(!afficherMdpAuth)}>
                {afficherMdpAuth ? <IconEyeOff size={16} /> : <IconEye size={16} />}
              </button>
            </div>
            {authMode === "login" && (
              <p className="switch" onClick={() => { setShowForgotPassword(true); setForgotMessage(""); }} style={{ textAlign: "right", fontSize: "0.85em" }}>
                Mot de passe oublie ?
              </p>
            )}
            {error && <p className="auth-error" role="alert">{messageAuth(String(error))}</p>}
            <button type="submit" className="auth-submit-btn">
              {authMode === "login" ? "Se connecter" : "S'inscrire"} <IconArrowRight size={16} />
            </button>
            <p className="switch" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>
              {authMode === "login" ? "Pas de compte ? S'inscrire" : "Deja un compte ? Se connecter"}
            </p>
          </form>
        </div>
      </div>
    );
  }

  // Vue galerie de templates
  if (showTemplatesGallery) {
    return (
      <div className="marketplace-page tpl-page">
        <header className="marketplace-header">
          <button type="button" className="app-header-back" onClick={() => { setShowTemplatesGallery(false); navigateTo('/'); }}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">GNB41 IA</span>
          </button>
          <div className="marketplace-header-actions">
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>

        <div className="marketplace-title-row">
          <div>
            <h2>Galerie de templates</h2>
            <p>Démarrez instantanément à partir d'une application déjà créée</p>
          </div>
        </div>

        {templatesList.length === 0 ? (
          <div className="marketplace-empty">
            <p>Aucun template disponible pour le moment.</p>
          </div>
        ) : (
          <div className="tpl-grid">
            {templatesList.map((t: any) => {
              const utiliser = async () => {
                let targetWorkspace = workspaces[0];
                if (!targetWorkspace) {
                  targetWorkspace = await api.createWorkspace('Mes projets');
                  setWorkspaces([targetWorkspace]);
                }
                const nom = window.prompt('Nom du nouveau projet :', t.nom) || t.nom;
                try {
                  const project = await api.useTemplate(t.id, targetWorkspace.id, nom);
                  setActiveWorkspace(targetWorkspace);
                  setActiveProject(project);
                  setShowTemplatesGallery(false);
                  navigateTo(`/projet/${project.id}`);
                } catch (err: any) {
                  alert(`Erreur: ${err.message}`);
                }
              };
              return (
                <div key={t.id} className="home-card tpl-card">
                  <div className="home-thumb">
                    <div className="home-thumb-fallback"><IconGrid size={40} /></div>
                    <MiniatureApp code={templatePreviews[t.id]} />
                    {t.categorie && <span className="home-badge home-badge-info">{t.categorie}</span>}
                  </div>
                  <div className="tpl-body">
                    <h3 className="home-card-name">{t.nom}</h3>
                    {t.description && <p className="tpl-desc">{t.description}</p>}
                    <button type="button" className="tpl-use" onClick={utiliser}>Utiliser ce template</button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Vue mentions legales / CGV
  if (showLegal) {
    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <button type="button" className="app-header-back" onClick={() => { setShowLegal(null); navigateTo('/marketplace'); }}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">Retour</span>
          </button>
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
          <button type="button" className="app-header-back" onClick={() => { setShowAdminDashboard(false); navigateTo('/marketplace'); }}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">Boutique</span>
          </button>
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

        <div className="admin-tabs" style={{ display: 'flex', gap: '0.6rem', padding: '0 1.5rem 1rem' }}>
          <button onClick={() => setAdminTab('boutique')} className={adminTab === 'boutique' ? 'btn-publish' : 'btn-publish is-cancel'}>Boutique</button>
          <button onClick={() => setAdminTab('utilisateurs')} className={adminTab === 'utilisateurs' ? 'btn-publish' : 'btn-publish is-cancel'}>Utilisateurs</button>
          <button onClick={() => setAdminTab('workspaces')} className={adminTab === 'workspaces' ? 'btn-publish' : 'btn-publish is-cancel'}>Workspaces</button>
          <button onClick={() => setAdminTab('evaluation')} className={adminTab === 'evaluation' ? 'btn-publish' : 'btn-publish is-cancel'}>Evaluation IA</button>
          <button onClick={() => setAdminTab('moderation')} className={adminTab === 'moderation' ? 'btn-publish' : 'btn-publish is-cancel'}>Modération</button>
        </div>

        {adminTab === 'moderation' && <PanneauModeration />}

        {adminTab === 'boutique' && (
        !adminStats ? (
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
                      <span className="admin-sales-date">{formatDate(v.created_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )
        )}

        {adminTab === 'utilisateurs' && (
          <div style={{ padding: '0 1.5rem 2rem' }}>
            {adminUsersLoading ? <p>Chargement...</p> : (
              <div className="admin-sales-table">
                {adminUsers.map((u: any) => (
                  <div key={u.id} className="admin-sales-row">
                    <span className="admin-sales-titre">{u.username} ({u.email})</span>
                    <span className="admin-sales-date">{formatDate(u.created_at)}</span>
                    <select value={u.role} onChange={(e) => api.adminUpdateUserRole(u.id, e.target.value).then(() => api.adminListUsers().then((res) => setAdminUsers(res.users)))}>
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                      <option value="superadmin">superadmin</option>
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {adminTab === 'workspaces' && (
          <div style={{ padding: '0 1.5rem 2rem' }}>
            {adminWorkspacesLoading ? <p>Chargement...</p> : (
              <div className="admin-sales-table">
                {adminWorkspaces.map((w: any) => (
                  <div key={w.id} className="admin-sales-row">
                    <span className="admin-sales-titre">{w.nom} — {w.owner_email}</span>
                    <span className="admin-sales-date">{w.member_count} membre(s)</span>
                    <button className="btn-publish is-cancel" onClick={() => { if (confirm('Supprimer ce workspace ?')) api.adminDeleteWorkspace(w.id).then(() => api.adminListWorkspaces().then((res) => setAdminWorkspaces(res.workspaces))); }}>Supprimer</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {adminTab === 'evaluation' && (
          <div style={{ padding: '0 1.5rem 2rem' }}>
            <button
              className="btn-publish"
              disabled={adminEvalRunning}
              onClick={() => {
                setAdminEvalRunning(true);
                api.adminRunEvaluation('mistral')
                  .then(() => api.adminEvaluationHistory().then((res) => setAdminEvalSuites(res.suites)))
                  .catch(() => {})
                  .finally(() => setAdminEvalRunning(false));
              }}
              style={{ marginBottom: '1rem' }}
            >
              {adminEvalRunning ? 'Execution en cours...' : 'Lancer la suite d\'evaluation'}
            </button>
            {adminEvalLoading ? <p>Chargement...</p> : adminEvalSuites.length === 0 ? (
              <p>Aucune execution pour le moment.</p>
            ) : (
              adminEvalSuites.map((suite: any) => (
                <div key={suite.suite_id} style={{ marginBottom: '1.5rem' }}>
                  <h3 style={{ fontSize: '0.95rem', opacity: 0.7 }}>
                    {formatDateTime(suite.created_at)}
                  </h3>
                  <div className="admin-sales-table">
                    {suite.runs.map((r: any) => (
                      <div key={r.id} className="admin-sales-row">
                        <span className="admin-sales-titre">{r.prompt}</span>
                        <span className={`marketplace-badge ${r.statut === 'pret' ? '' : 'admin-badge-pending'}`}>{r.statut}</span>
                        <span className="admin-sales-sub">
                          {r.a_comprehension ? 'comprehension ok' : 'comprehension manquante'} · {r.a_plan ? 'plan ok' : 'plan manquant'} · {r.nb_avertissements} avertissement(s)
                        </span>
                        <span className="admin-sales-date">{r.duree_ms ? (r.duree_ms / 1000).toFixed(1) + ' s' : '-'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    );
  }

  // Vue Mes achats
  if (showMesAchats) {
    const totalDepense = myPurchasesList.reduce((sum, p) => sum + p.prix_paye_centimes, 0);

    return (
      <div className="marketplace-page acv-page">
        <header className="marketplace-header">
          <button type="button" className="app-header-back" onClick={() => { setShowMesAchats(false); navigateTo('/marketplace'); }}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">Boutique</span>
          </button>
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
          <div className="acv-empty">
            <p>Vous n'avez encore rien acheté.</p>
          </div>
        ) : (
          <div className="acv-grid">
            {myPurchasesList.map((p) => (
              <div key={p.id} className="acv-card">
                <div className="acv-top">
                  <span className="acv-price">{(p.prix_paye_centimes / 100).toFixed(2)} EUR</span>
                  <span className={`acv-badge acv-badge-${tonStatut(p.statut)}`}>{libelleStatut(p.statut)}</span>
                </div>
                <p className="acv-date">
                  Acheté le {formatDate(p.created_at)}
                </p>
                {p.statut === 'en_attente' && (
                  <button
                    type="button"
                    className="acv-btn"
                    onClick={async () => {
                      const res = await api.verifyPurchase(p.id);
                      setMyPurchasesList((prev) => prev.map((x) => (x.id === p.id ? res : x)));
                    }}
                  >
                    Vérifier le paiement
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
      <div className="marketplace-page acv-page">
        <header className="marketplace-header">
          <button type="button" className="app-header-back" onClick={() => { setShowMesVentes(false); navigateTo('/marketplace'); }}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">Boutique</span>
          </button>
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
          <div className="acv-empty">
            <p>Vous n'avez publié aucune application pour le moment.</p>
          </div>
        ) : (
          <div className="acv-grid">
            {myListingsList.map((l) => (
              <div key={l.id} className="acv-card">
                <h3 className="acv-title">{l.titre}</h3>
                <p className="acv-desc">{l.description}</p>
                <div className="acv-top">
                  <span className="acv-price">{(l.prix_centimes / 100).toFixed(2)} {l.devise}</span>
                  <span className={`acv-badge acv-badge-${tonStatut(l.statut)}`}>{libelleStatut(l.statut)}</span>
                </div>
                <div className="acv-stats">
                  <span>{l.nb_ventes || 0} vente{l.nb_ventes !== 1 ? 's' : ''}</span>
                  <strong>{((l.revenus_centimes || 0) / 100).toFixed(2)} EUR</strong>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Vue boutique
  if (showStudio) {
    return <Studio user={user} onBack={() => { setShowStudio(false); navigateTo('/'); }} />;
  }

  if (showStudio) {
    return <Studio user={user} onBack={() => { setShowStudio(false); navigateTo('/'); }} />;
  }

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
          <button type="button" className="app-header-back" onClick={() => { setShowMarketplace(false); navigateTo('/'); }}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">GNB41 IA</span>
          </button>
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

              <label className="droits-check">
                <input type="checkbox" checked={publishDroits} onChange={(e) => setPublishDroits(e.target.checked)} />
                <span>Je certifie détenir les droits sur tous les noms, logos, images, sons et personnages de cette application, et j'accepte qu'elle soit retirée en cas de réclamation d'un titulaire de droits.</span>
              </label>

              {publishError && <p className="error">{publishError}</p>}
              {publishNeedsJustif && (
                <textarea
                  className="justif-field"
                  rows={4}
                  maxLength={2000}
                  placeholder="Justification : licence, autorisation écrite du titulaire des droits… (20 caractères minimum)"
                  value={publishJustification}
                  onChange={(e) => setPublishJustification(e.target.value)}
                />
              )}
              <button type="submit" className="btn-publish" disabled={publishLoading || !publishDroits} style={{ justifyContent: 'center' }}>
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
              const openLink = l.source_type === 'externe_lien' ? l.lien_externe : `${API_URL_PUBLIQUE}/marketplace/${l.id}/preview`;
              const copyLink = () => {
                navigator.clipboard.writeText(openLink).catch(() => {});
              };
              const bannerUrl = l.image_url && l.image_url.startsWith('/') ? `${API_URL_PUBLIQUE.replace(/\/api\/?$/, '')}${l.image_url}` : l.image_url;
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
                  {l.vendeur_id !== user.id && (
                    <button type="button" className="report-link" onClick={() => setReport({ target: l, motif: 'contrefacon', details: '', msg: '', ok: false, loading: false })}>
                      Signaler
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
        {report && (
          <div className="report-overlay" onClick={() => setReport(null)}>
            <div className="report-sheet" role="dialog" aria-modal="true" aria-label="Signaler cette annonce" onClick={(e) => e.stopPropagation()}>
              <h3>Signaler cette annonce</h3>
              <p className="report-title">{report.target.titre}</p>
              <label className="report-label">Motif</label>
              <select value={report.motif} onChange={(e) => setReport({ ...report, motif: e.target.value })}>
                <option value="contrefacon">Contrefaçon ou marque non autorisée</option>
                <option value="contenu_illegal">Contenu illégal ou dangereux</option>
                <option value="autre">Autre</option>
              </select>
              <label className="report-label">Détails {report.motif === 'autre' ? '(requis)' : '(facultatif)'}</label>
              <textarea rows={4} maxLength={2000} value={report.details} onChange={(e) => setReport({ ...report, details: e.target.value })} />
              {report.msg && <p className={`report-msg ${report.ok ? 'is-ok' : 'is-error'}`} role="status">{report.msg}</p>}
              <div className="report-actions">
                <button type="button" className="report-cancel" onClick={() => setReport(null)}>Fermer</button>
                <button type="button" className="report-send" disabled={report.loading || report.ok} onClick={handleReport}>{report.loading ? 'Envoi…' : 'Envoyer'}</button>
              </div>
            </div>
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
          <button className="app-header-back" onClick={() => { setShowSettings(false); navigateTo('/'); }}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">GNB41 IA</span>
          </button>
          <div>
            <NotificationBell />
            <span>{user.username}</span>
            <button onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>
        <main className="settings-page-main">
          <div className="settings-header-card">
            <div className="settings-icon-badge"><IconSettings /></div>
            <div>
              <h2 className="settings-page-title" style={{ marginBottom: 0 }}>Paramètres du compte</h2>
              <p className="settings-page-subtitle" style={{ marginBottom: 0 }}>Gérez vos informations personnelles et vos connexions de publication.</p>
            </div>
          </div>

          <div className="settings-card">
            <div className="settings-card-header">
              <div className="settings-icon-badge soft"><IconUser /></div>
              <div>
                <h2>Informations personnelles</h2>
                <p>Votre email et votre mot de passe de connexion</p>
              </div>
            </div>
            <form onSubmit={handleUpdateSettings}>
              <label className="settings-field-icon-label"><IconMail /> Email</label>
              <div className="settings-input-pill-wrap">
                <input placeholder="Email" type="email" value={settingsEmail} onChange={(e) => setSettingsEmail(e.target.value)} />
                {settingsEmail && <span className="settings-input-trailing ok"><IconCheckCircle size={18} /></span>}
              </div>

              <label className="settings-field-icon-label"><IconLock /> Nouveau mot de passe (optionnel)</label>
              <div className="settings-input-pill-wrap">
                <input placeholder="Entrez un nouveau mot de passe" type={afficherNouveauMdp ? 'text' : 'password'} value={settingsPassword} onChange={(e) => setSettingsPassword(e.target.value)} />
                <button type="button" className="settings-input-trailing" onClick={() => setAfficherNouveauMdp(!afficherNouveauMdp)}>
                  {afficherNouveauMdp ? <IconEyeOff size={18} /> : <IconEye size={18} />}
                </button>
              </div>

              <label className="settings-field-icon-label"><IconLock /> Mot de passe actuel (requis)</label>
              <div className="settings-input-pill-wrap">
                <input placeholder="Entrez votre mot de passe actuel" type={afficherMdpActuel ? 'text' : 'password'} value={settingsCurrentPassword} onChange={(e) => setSettingsCurrentPassword(e.target.value)} required />
                <button type="button" className="settings-input-trailing" onClick={() => setAfficherMdpActuel(!afficherMdpActuel)}>
                  {afficherMdpActuel ? <IconEyeOff size={18} /> : <IconEye size={18} />}
                </button>
              </div>

              {settingsError && <p className="error">{settingsError}</p>}
              {settingsMsg && <p className="success">{settingsMsg}</p>}
              <button type="submit" className="settings-btn-gradient"><IconSave size={18} /> Enregistrer <IconArrowRight size={18} /></button>
            </form>
          </div>

          <div className="settings-card">
            <div className="settings-card-header">
              <div className="settings-icon-badge soft"><IconGooglePlay size={26} /></div>
              <div>
                <h2>Publication mobile (Google Play)</h2>
                <p>Connectez votre compte développeur pour publier vos apps</p>
              </div>
            </div>

            {googlePlayLoading ? <p>Chargement...</p> : googlePlayStatut && (
              googlePlayStatut.connecte ? (
                <div>
                  <span className="settings-status-pill connecte">
                    <IconCheckCircle />
                    Connecté
                  </span>
                  <p style={{ marginTop: '0.8rem', fontSize: '0.9rem', color: '#4a4432' }}>Package : <strong>{googlePlayStatut.package_name}</strong></p>
                  <button
                    className="btn-publish is-cancel settings-btn-icon"
                    style={{ marginTop: '0.8rem' }}
                    onClick={() => { if (confirm('Déconnecter votre compte Google Play ?')) api.googlePlayDeconnecter().then(setGooglePlayStatut).catch(() => {}); }}
                  >
                    <IconLogOut size={16} /> Déconnecter
                  </button>
                </div>
              ) : (
                googlePlayStatut.service_account_email ? (
                  <div>
                    <div className="settings-step">
                      <div className="settings-step-number">1</div>
                      <div className="settings-step-content">
                        <p>Dans votre Play Console, section "Utilisateurs et autorisations", invitez cet email avec le role Gestionnaire de version :</p>
                        <div className="settings-email-box">{googlePlayStatut.service_account_email}</div>
                      </div>
                    </div>
                    <div className="settings-step">
                      <div className="settings-step-number">2</div>
                      <div className="settings-step-content">
                        <p>Une fois l'invitation acceptee, entrez le nom de package de votre app :</p>
                        <input placeholder="com.votresociete.votreapp" value={googlePlayPackageInput} onChange={(e) => setGooglePlayPackageInput(e.target.value)} style={{ width: '100%', boxSizing: 'border-box' }} />
                        <button
                          className="settings-btn-icon"
                          style={{ marginTop: '0.8rem' }}
                          onClick={() => {
                            if (!googlePlayPackageInput.trim()) return;
                            api.googlePlayConfirmer(googlePlayPackageInput.trim()).then(setGooglePlayStatut).catch(() => {});
                          }}
                        >
                          <IconLink size={16} /> Confirmer la connexion
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <span className="settings-status-pill deconnecte">
                      <IconCheckCircle />
                      Compte non connecté
                    </span>
                    <span className="settings-status-pill deconnecte">
                      <IconInfoCircle />
                      Bientôt disponible
                    </span>
                  </div>
                )
              )
            )}
          </div>
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
        const result = await api.chatProject(activeProject.id, messageText, chatProvider, imageToSend || undefined, agentMode === 'auto' ? undefined : agentMode);
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
      if (!htmlFile) return null;
      let html = htmlFile.contenu;

      const cssFiles = parsedFiles.fichiers.filter((f: any) => f.chemin.endsWith('.css'));
      const jsFiles = parsedFiles.fichiers.filter((f: any) => f.chemin.endsWith('.js'));

      cssFiles.forEach((cssFile: any) => {
        const linkPattern = new RegExp(`<link[^>]+href=["'][^"']*${cssFile.chemin.split('/').pop()}["'][^>]*>`, 'i');
        const styleTag = `<style>
${cssFile.contenu}
</style>`;
        if (linkPattern.test(html)) {
          html = html.replace(linkPattern, styleTag);
        } else {
          html = html.replace('</head>', `${styleTag}
</head>`);
        }
      });

      jsFiles.forEach((jsFile: any) => {
        const scriptPattern = new RegExp(`<script[^>]+src=["'][^"']*${jsFile.chemin.split('/').pop()}["'][^>]*></script>`, 'i');
        const scriptTag = `<script>
${jsFile.contenu}
</script>`;
        if (scriptPattern.test(html)) {
          html = html.replace(scriptPattern, scriptTag);
        } else {
          html = html.replace('</body>', `${scriptTag}
</body>`);
        }
      });

      const scriptPolyfillStorage = `<script>
      (function() {
        function creerStockageMemoire() {
          var donnees = {};
          return {
            getItem: function(cle) { return Object.prototype.hasOwnProperty.call(donnees, cle) ? donnees[cle] : null; },
            setItem: function(cle, valeur) { donnees[cle] = String(valeur); },
            removeItem: function(cle) { delete donnees[cle]; },
            clear: function() { donnees = {}; },
            key: function(i) { return Object.keys(donnees)[i] || null; },
            get length() { return Object.keys(donnees).length; }
          };
        }
        try { window.localStorage.getItem('test'); } catch (e) {
          try { Object.defineProperty(window, 'localStorage', { value: creerStockageMemoire(), configurable: true }); } catch (e2) {}
        }
        try { window.sessionStorage.getItem('test'); } catch (e) {
          try { Object.defineProperty(window, 'sessionStorage', { value: creerStockageMemoire(), configurable: true }); } catch (e2) {}
        }
      })();
      </script>`;

      const scriptCaptureErreurs = `<script>
      (function() {
        function envoyer(message) {
          try { window.parent.postMessage({ source: 'gnb41-preview-error', message: message }, '*'); } catch (e) {}
        }
        window.addEventListener('error', function(e) {
          envoyer((e && e.message) || 'Erreur inconnue');
        });
        window.addEventListener('unhandledrejection', function(e) {
          envoyer('Promesse rejetee: ' + ((e && e.reason && e.reason.message) || e.reason || 'raison inconnue'));
        });
      })();
      </script>`;
      const scriptsInjection = scriptPolyfillStorage + scriptCaptureErreurs;
      if (html.includes('<head>')) {
        html = html.replace('<head>', '<head>' + scriptsInjection);
      } else {
        html = scriptsInjection + html;
      }

      return html;
    })();

    return (
      <div className={`workspace-builder studio-vue-${vueMobile}`}>
      {showUpgradeModal && (
        <div className="modal-overlay" onClick={() => setShowUpgradeModal(false)}>
          <div className="upgrade-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowUpgradeModal(false)}>×</button>
            <h2>Choisissez votre plan</h2>
            <p className="modal-subtitle">Le paiement n'est pas encore disponible — ceci est un aperçu des offres à venir.</p>
            <div className="plans-grid">
              {plansList.map((p: any) => (
                <div key={p.id} className={`plan-card ${p.populaire ? 'plan-card-highlight' : ''}`}>
                  {p.populaire && <span className="plan-badge">Populaire</span>}
                  <h3>{p.nom}</h3>
                  <p className="plan-price">
                    {p.sur_devis ? 'Sur devis' : `${p.prix_usd}$`}
                    {!p.sur_devis && <span>/mois</span>}
                  </p>
                  {!p.sur_devis && p.credits != null && (
                    <p className="plan-credits">{p.credits} crédits de génération</p>
                  )}
                  <ul>
                    {(p.features || []).map((f: string, i: number) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                  {user?.plan === p.slug ? (
                    <button className="plan-btn plan-btn-current" disabled>Plan actuel</button>
                  ) : p.sur_devis ? (
                    <button className="plan-btn" disabled>Nous contacter</button>
                  ) : (
                    <button className="plan-btn plan-btn-primary" disabled={upgradingPlan === p.slug} onClick={() => handleUpgrade(p.slug)}>{upgradingPlan === p.slug ? 'Redirection...' : `Passer à ${p.nom}`}</button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
        <header>
          <div className="studio-bar">
            <button type="button" className="app-header-back" onClick={() => { setActiveProject(null); navigateTo('/'); }}>
              <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
              <span className="app-header-back-title app-header-back-title-clip">{activeProject.nom}</span>
            </button>
            <div className="studio-actions">
              <button
              className={`toolbar-icon-btn studio-publish${activeProject.est_deploye ? ' is-live' : ''}`}
              title={activeProject.est_deploye ? "Déployée (toucher pour voir le lien)" : "Publier l'application"}
              disabled={deployLoading}
              onClick={async () => {
                if (activeProject.est_deploye) {
                  const base = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001/api';
                  setLiveUrl(`${base}/projects/${activeProject.id}/live/`);
                  return;
                }
                setDeployLoading(true);
                try {
                  const derniere: any = await api.latestWarnings(activeProject.id);
                  if (derniere && derniere.avertissements) {
                    const liste = JSON.parse(derniere.avertissements);
                    if (liste.length > 0) {
                      const suite = window.confirm(
                        'Des points a verifier ont ete detectes sur la derniere generation :\n\n' + liste.join('\n') + '\n\nDeployer quand meme ?'
                      );
                      if (!suite) { setDeployLoading(false); return; }
                    }
                  }
                } catch {}

                try {
                  const res = await api.deployProject(activeProject.id);
                  setActiveProject(res.project);
                  setLiveUrl(res.live_url);
                } catch (err: any) {
                  alert(`Erreur: ${err.message}`);
                } finally {
                  setDeployLoading(false);
                }
              }}
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke={activeProject.est_deploye ? '#22c55e' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg><span>{deployLoading ? 'Publication…' : activeProject.est_deploye ? 'En ligne' : 'Publier'}</span></button>
              <div className="studio-menu-wrap">
              <button type="button" className="toolbar-icon-btn studio-more" aria-label="Plus d'actions" aria-expanded={menuStudio} onClick={() => setMenuStudio(!menuStudio)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg>
              </button>
              {menuStudio && (
                <>
                  <div className="studio-overlay" onClick={() => setMenuStudio(false)} />
                  <div className="studio-menu" role="menu">
                    <button type="button" role="menuitem" onClick={(e) => { setMenuStudio(false); (handleShare as any)(e); }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
                      Partager
                    </button>
                    <button type="button" role="menuitem" onClick={(e) => { setMenuStudio(false); (handleDuplicate as any)(e); }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                      Dupliquer
                    </button>
                    <button type="button" role="menuitem" onClick={(e) => { setMenuStudio(false); (toggleVersions as any)(e); }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                      Historique des versions
                    </button>
                    {activeProject.est_deploye && (
                      <button type="button" role="menuitem" className="studio-depublier" onClick={async () => {
                        setMenuStudio(false);
                        if (!window.confirm("Retirer l'application de la publication ? Son lien public ne fonctionnera plus.")) return;
                        try {
                          await api.undeployProject(activeProject.id);
                          setActiveProject({ ...activeProject, est_deploye: false });
                          setLiveUrl(null);
                        } catch (err: any) { alert(`Erreur: ${err.message}`); }
                      }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="4.9" y1="4.9" x2="19.1" y2="19.1"/></svg>
                        Dépublier
                      </button>
                    )}
                    <button type="button" role="menuitem" onClick={() => { setMenuStudio(false); setShowPublishTemplate(true); }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                      Publier dans les templates
                    </button>
                    <button type="button" role="menuitem" onClick={() => { setMenuStudio(false); setShowWorkspaceSettings(true); }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/></svg>
                      Paramètres de l'espace
                    </button>
                  </div>
                </>
              )}
            </div>
            </div>
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
                          <span className="activity-date"> — {formatDateTime(log.created_at)}</span>
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

        {liveUrl && (
          <div style={{ padding: '0.6rem 1rem', background: '#dcfce7', display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.82rem', color: '#166534' }}>App en ligne :</span>
            <a href={liveUrl} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.82rem', color: '#166534', fontWeight: 600, wordBreak: 'break-all' }}>{liveUrl}</a>
            <button
              type="button"
              className="marketplace-link-btn"
              onClick={() => navigator.clipboard.writeText(liveUrl).catch(() => {})}
            >
              Copier
            </button>
            <button
              type="button"
              className="marketplace-link-btn"
              onClick={async () => {
                if (!activeProject) return;
                await api.undeployProject(activeProject.id);
                setActiveProject({ ...activeProject, est_deploye: false });
                setLiveUrl(null);
              }}
            >
              Depublier
            </button>
          </div>
        )}

        <div className="studio-switch" role="tablist" aria-label="Affichage du projet">
          <button type="button" role="tab" aria-selected={vueMobile === 'chat'} className={vueMobile === 'chat' ? 'active' : ''} onClick={() => setVueMobile('chat')}>Chat IA</button>
          <button type="button" role="tab" aria-selected={vueMobile === 'apercu'} className={vueMobile === 'apercu' ? 'active' : ''} onClick={() => setVueMobile('apercu')}>Aperçu</button>
        </div>

        <div className="preview-tabs">
          <button className={`preview-tab ${previewTab === 'apercu' ? 'active' : ''}`} onClick={() => setPreviewTab('apercu')}>Aperçu</button>
          <button className={`preview-tab ${previewTab === 'code' ? 'active' : ''}`} onClick={() => setPreviewTab('code')}>Code</button>
          <button className={`preview-tab ${previewTab === 'donnees' ? 'active' : ''}`} onClick={() => { setPreviewTab('donnees'); if (activeProject) { api.listAppTables(activeProject.id).then(setAppTables).catch(() => {}); api.listAppKeys(activeProject.id).then(setAppKeys).catch(() => {}); } }}>Base de données</button>
          <button className={`preview-tab ${previewTab === 'memoire' ? 'active' : ''}`} onClick={() => { setPreviewTab('memoire'); setMemoireDraft(activeProject?.memoire_projet || ''); }}>Mémoire</button>
        </div>

        {showVersions && (
          <div className="detail-section versions-panel">
            <ul className="versions-list">
              {versions.map((v, idx) => {
                const ancienne = versions[idx + 1];
                let diffTexte = '';
                if (v.statut === 'pret' && v.code_genere && ancienne && ancienne.statut === 'pret' && ancienne.code_genere) {
                  try {
                    const fichiersActuels: any[] = JSON.parse(v.code_genere).fichiers || [];
                    const fichiersAnciens: any[] = JSON.parse(ancienne.code_genere).fichiers || [];
                    const mapAncien = new Map(fichiersAnciens.map((f: any) => [f.chemin, f.contenu]));
                    const mapActuel = new Map(fichiersActuels.map((f: any) => [f.chemin, f.contenu]));
                    let ajoutes = 0, modifies = 0, supprimes = 0;
                    mapActuel.forEach((contenu, chemin) => {
                      if (!mapAncien.has(chemin)) ajoutes++;
                      else if (mapAncien.get(chemin) !== contenu) modifies++;
                    });
                    mapAncien.forEach((_contenu, chemin) => {
                      if (!mapActuel.has(chemin)) supprimes++;
                    });
                    const parts = [];
                    if (ajoutes) parts.push(`+${ajoutes} ajouté(s)`);
                    if (modifies) parts.push(`~${modifies} modifié(s)`);
                    if (supprimes) parts.push(`-${supprimes} supprimé(s)`);
                    diffTexte = parts.join(', ');
                  } catch {}
                }
                return (
                <li key={v.id} className="ver-card">
                  <span className={`statut statut-${v.statut} ver-statut`}>{({ pret: 'Prêt', genere: 'Prêt', erreur: 'Échec', en_generation: 'En cours', en_attente: 'En attente' } as Record<string, string>)[v.statut] || v.statut}</span>
                  <p className="ver-prompt">{v.prompt}</p>
                  <span className="ver-meta">{formatShortDateTime(v.created_at)}</span>
                  {v.duree_generation_ms != null && (
                    <span className="ver-meta">{(v.duree_generation_ms / 1000).toFixed(1)} s</span>
                  )}
                  {v.agent_type && (
                    <span className="ver-meta">{v.agent_type}</span>
                  )}
                  {diffTexte && (
                    <span className="ver-meta ver-diff">{diffTexte}</span>
                  )}
                  {v.statut === 'pret' && v.code_genere && (
                    <button
                      type="button"
                      className="ver-restore"
                      onClick={async () => {
                        if (!activeProject) return;
                        if (!window.confirm('Restaurer cette version ? Le code actuel du projet sera remplacé.')) return;
                        try {
                          const updated = await api.restoreVersion(activeProject.id, v.id);
                          setActiveProject(updated);
                          const msgs = await api.listMessages(activeProject.id);
                          setChatMessages(msgs);
                          const vs = await api.listVersions(activeProject.id);
                          setVersions(vs);
                        } catch (err: any) {
                          alert('Erreur lors de la restauration : ' + err.message);
                        }
                      }}
                    >
                      Restaurer
                    </button>
                  )}
                </li>
                );
              })}
              {versions.length === 0 && <p className="ver-empty">Aucune version dans l'historique.</p>}
            </ul>
          </div>
        )}

        <button type="button" className="studio-fab" onClick={() => setVueMobile('chat')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Discutez pour modifier
        </button>

        <div className="builder-layout">
          <div className="builder-chat">
            <p className={`statut statut-${activeProject.statut} studio-statut`}>{({ pret: 'Prêt', genere: 'Prêt', en_generation: 'En cours', en_attente: 'En attente', erreur: 'Échec de génération' } as Record<string, string>)[activeProject.statut] || activeProject.statut}</p>

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
                    {m.created_at && <span className="msg-time">{formatTime(m.created_at)}</span>}
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

                <div className="provider-dropdown">
                  <button type="button" className="provider-pill" onClick={() => setShowAgentModeMenu(!showAgentModeMenu)}>
                    {({ creation: 'Création', modification: 'Modification', style: 'Design', contenu: 'Contenu', jeu: 'Jeu mobile', mobile: 'App mobile' } as Record<string, string>)[agentMode] || 'Agent: Auto'}
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="6 9 12 15 18 9"/></svg>
                  </button>
                  {showAgentModeMenu && (
                    <div className="provider-menu">
                      {[['auto', 'Auto (détection)'], ['creation', 'Création'], ['modification', 'Modification'], ['style', 'Design/Style'], ['contenu', 'Contenu'], ['jeu', 'Jeu mobile'], ['mobile', 'App mobile']].map(([val, label]) => (
                        <button
                          type="button"
                          key={val}
                          className={`provider-menu-item ${agentMode === val ? 'active' : ''}`}
                          onClick={() => { setAgentMode(val); setShowAgentModeMenu(false); }}
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
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <iframe
                    title="Aperçu"
                    srcDoc={previewContent}
                    className="preview-iframe"
                    sandbox="allow-scripts"
                    onLoad={() => setErreursPreview([])}
                  />
                  {erreursPreview.length > 0 && (
                    <div style={{ padding: '0.6rem 1rem', background: '#fef2f2', borderTop: '1px solid #fecaca', maxHeight: '140px', overflow: 'auto' }}>
                      <p style={{ fontSize: '0.78rem', fontWeight: 600, color: '#b91c1c', marginBottom: '0.3rem' }}>Erreurs JavaScript detectees dans l'apercu :</p>
                      {erreursPreview.map((err, i) => (
                        <p key={i} style={{ fontSize: '0.75rem', color: '#7f1d1d', fontFamily: 'monospace' }}>{err}</p>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="preview-empty">
                  <p>L'aperçu apparaîtra ici une fois l'application générée.</p>
                </div>
              )
            ) : previewTab === 'donnees' ? (
              <div className="code-editor-layout">
                <div className="code-editor-sidebar">
                  <p className="stack-badge">Tables</p>
                  <button type="button" className={`code-editor-file-btn ${!selectedTableId ? 'active' : ''}`} onClick={() => setSelectedTableId(null)}>Clés API</button>
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
                  {appTables.length === 0 && <p className="db-empty">Aucune table déclarée pour ce projet.</p>}
                </div>
                <div className="code-editor-main">
                  <div className="code-editor-toolbar">
                    <span className="code-editor-filename">
                      {selectedTableId ? appTables.find((t: any) => t.id === selectedTableId)?.nom : 'Clés API'}
                    </span>
                  </div>
                  <div className="db-body">
                    {selectedTableId ? (
                      <>
                        <p className="db-count">{selectedTableRows.length} ligne{selectedTableRows.length !== 1 ? 's' : ''}</p>
                        {selectedTableRows.map((row: any) => (
                          <pre key={row.id} className="db-row">{JSON.stringify(row.data, null, 2)}</pre>
                        ))}
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="db-btn"
                          onClick={async () => {
                            if (!activeProject) return;
                            const res = await api.createAppKey(activeProject.id);
                            setNewKeyRevealed(res.key);
                            const keys = await api.listAppKeys(activeProject.id);
                            setAppKeys(keys);
                          }}
                        >
                          + Nouvelle clé API
                        </button>
                        {newKeyRevealed && (
                          <div className="db-secret">
                            Copiez cette clé maintenant, elle ne sera plus affichée : <strong>{newKeyRevealed}</strong>
                          </div>
                        )}
                        {appKeys.map((k: any) => (
                          <div key={k.id} className="db-key-row">
                            <span className="db-key-prefix">{k.key_prefix}… {k.revoked ? '(révoquée)' : ''}</span>
                            {!k.revoked && (
                              <button
                                type="button"
                                className="db-revoke"
                                onClick={async () => {
                                  await api.revokeAppKey(k.id);
                                  if (activeProject) {
                                    const keys = await api.listAppKeys(activeProject.id);
                                    setAppKeys(keys);
                                  }
                                }}
                              >Révoquer</button>
                            )}
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : previewTab === 'memoire' ? (
              <div className="mem-body">
                <p className="mem-intro">
                  Règles et décisions techniques mémorisées pour ce projet. L'IA les respecte automatiquement à chaque génération, et y ajoute elle-même les décisions importantes qu'elle prend.
                </p>
                <textarea
                  value={memoireDraft}
                  onChange={(e) => setMemoireDraft(e.target.value)}
                  rows={12}
                  className="memoire-textarea"
                  placeholder="Aucune règle mémorisée pour l'instant."
                />
                <button
                  type="button"
                  className="mem-btn"
                  onClick={async () => {
                    if (!activeProject) return;
                    try {
                      const updated = await api.updateMemoireProjet(activeProject.id, memoireDraft);
                      setActiveProject(updated);
                      setMemoireMsg('Mémoire enregistrée.');
                      setTimeout(() => setMemoireMsg(''), 2500);
                    } catch (err: any) {
                      setMemoireMsg('Erreur: ' + err.message);
                    }
                  }}
                >
                  Enregistrer
                </button>
                {memoireMsg && <p className={`mem-msg ${memoireMsg.startsWith('Erreur') ? 'is-error' : ''}`} role="status">{memoireMsg}</p>}
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
                        if (editorDirty && previewFile && !confirm('Modifications non enregistrées. Changer de fichier quand même ?')) return;
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
                          {editorSaving ? 'Enregistrement…' : editorDirty ? 'Enregistrer' : 'Enregistré'}
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
                      <p>Sélectionnez un fichier pour l'éditer.</p>
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

        {showPublishTemplate && (
          <div className="modal-overlay" onClick={() => setShowPublishTemplate(false)}>
            <div className="upgrade-modal" onClick={(e) => e.stopPropagation()}>
              <button className="modal-close" onClick={() => setShowPublishTemplate(false)}>×</button>
              <h2>Publier comme template</h2>
              <p className="modal-subtitle">Ce template sera visible par tous les utilisateurs dans la galerie.</p>
              <form
                className="auth-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!activeProject) return;
                  setTemplatePublishing(true);
                  try {
                    await api.publishTemplate(activeProject.id, {
                      nom: templateNom || activeProject.nom,
                      description: templateDesc || activeProject.prompt_initial,
                      categorie: templateCategorie
                    });
                    setShowPublishTemplate(false);
                    setTemplateNom('');
                    setTemplateDesc('');
                    setTemplateCategorie('autre');
                    alert('Template publie avec succes !');
                  } catch (err: any) {
                    alert(`Erreur: ${err.message}`);
                  } finally {
                    setTemplatePublishing(false);
                  }
                }}
              >
                <input placeholder="Nom du template" value={templateNom} onChange={(e) => setTemplateNom(e.target.value)} />
                <textarea placeholder="Description" value={templateDesc} onChange={(e) => setTemplateDesc(e.target.value)} rows={3} />
                <select value={templateCategorie} onChange={(e) => setTemplateCategorie(e.target.value)}>
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
                <button type="submit" disabled={templatePublishing}>{templatePublishing ? 'Publication...' : 'Publier'}</button>
              </form>
            </div>
          </div>
        )}
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
              {plansList.map((p: any) => (
                <div key={p.id} className={`plan-card ${p.populaire ? 'plan-card-highlight' : ''}`}>
                  {p.populaire && <span className="plan-badge">Populaire</span>}
                  <h3>{p.nom}</h3>
                  <p className="plan-price">
                    {p.sur_devis ? 'Sur devis' : `${p.prix_usd}$`}
                    {!p.sur_devis && <span>/mois</span>}
                  </p>
                  {!p.sur_devis && p.credits != null && (
                    <p className="plan-credits">{p.credits} crédits de génération</p>
                  )}
                  <ul>
                    {(p.features || []).map((f: string, i: number) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                  {user?.plan === p.slug ? (
                    <button className="plan-btn plan-btn-current" disabled>Plan actuel</button>
                  ) : p.sur_devis ? (
                    <button className="plan-btn" disabled>Nous contacter</button>
                  ) : (
                    <button className="plan-btn plan-btn-primary" disabled={upgradingPlan === p.slug} onClick={() => handleUpgrade(p.slug)}>{upgradingPlan === p.slug ? 'Redirection...' : `Passer à ${p.nom}`}</button>
                  )}
                </div>
              ))}
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
                <div className="user-avatar">{user.username.charAt(0).toUpperCase()}</div>
                <div className="side-menu-user-info">
                  <span className="side-menu-username">{user.username}</span>
                  {user.plan === 'pro' && user.plan_expiry ? (
                    <span className="side-menu-plan">Pro jusqu'au {formatDate(user.plan_expiry)}</span>
                  ) : (
                    <span className="side-menu-plan side-menu-plan-free">Plan Gratuit</span>
                  )}
                  {user.credits != null && (
                    <span className="side-menu-credits">{user.credits} crédit{user.credits === 1 ? '' : 's'} restant{user.credits === 1 ? '' : 's'}</span>
                  )}
                </div>
              </div>
              <NotificationBell />
              <button className="side-menu-item upgrade-btn" onClick={() => { setShowMenu(false); setShowUpgradeModal(true); }}>✦ Mettre à niveau</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); }}><span className="side-menu-item-icon"><IconHome size={18} /></span>Accueil</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); document.querySelector('.recent-section')?.scrollIntoView({ behavior: 'smooth' }); }}><span className="side-menu-item-icon"><IconPackage size={18} /></span>Projets</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); setShowMarketplace(true); setShowSettings(false); navigateTo('/marketplace'); }}><span className="side-menu-item-icon"><IconStore size={18} /></span>Boutique</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); setShowStudio(true); navigateTo('/studio'); }}><span className="side-menu-item-icon"><IconKey size={18} /></span>Studio</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); setShowTemplatesGallery(true); api.listTemplates().then(setTemplatesList).catch(() => {}); navigateTo('/templates'); }}><span className="side-menu-item-icon"><IconGrid size={18} /></span>Galerie de templates</button>
              <button className="side-menu-item" onClick={() => { setShowMenu(false); setShowSettings(true); navigateTo('/parametres'); }}><span className="side-menu-item-icon"><IconSettings size={18} /></span>Paramètres</button>
              <button className="side-menu-item" onClick={() => setDarkMode(!darkMode)}><span className="side-menu-item-icon">{darkMode ? <IconSun size={18} /> : <IconMoon size={18} />}</span>{darkMode ? 'Mode clair' : 'Mode sombre'}</button>
              <button className="side-menu-item side-menu-logout" onClick={handleLogout}>Déconnexion</button>
            </nav>
          </>
        )}
      </header>

      <main className="quickstart-main">
        <div className="home-hero">
          <p className="home-hello">Bonjour {user.username}</p>
          <h2 className="home-title">Que construirez-vous ensuite ?</h2>
        </div>

        <form onSubmit={handleQuickStart} className="quickstart-form quickstart-card">
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

        {recentProjects.length === 0 && !quickLoading && (
          <div className="empty-state">
            <IconPackage size={40} />
            <h3>Aucun projet pour l'instant</h3>
            <p>Décrivez votre idée ci-dessus et l'IA génère votre première application.</p>
          </div>
        )}

        {recentProjects.length > 0 && (
          <section className="home-recents">
            <h3 className="home-section-title">Projets récents</h3>
            <div className="home-grid">
              {recentProjects.map((p: any) => {
                const st = (p.statut === 'genere' || p.statut === 'pret') ? ['ok', 'Prêt']
                  : p.statut === 'en_generation' ? ['info', 'En cours']
                  : p.statut === 'erreur' ? ['warn', 'Échec de génération']
                  : ['info', String(p.statut || 'Brouillon').replace(/_/g, ' ').replace(/^./, (c: string) => c.toUpperCase())];
                const ouvrir = () => {
                  const ws = workspaces.find((w) => w.id === p.parentWorkspaceId);
                  if (ws) setActiveWorkspace(ws);
                  setActiveProject(p);
                  navigateTo(`/projet/${p.id}`);
                };
                const depuis = (iso: string) => {
                  const d = (parseServerDate(iso).getTime() - Date.now()) / 1000;
                  const rtf = new Intl.RelativeTimeFormat('fr', { numeric: 'auto' });
                  const u: [Intl.RelativeTimeFormatUnit, number][] = [['year', 31536000], ['month', 2592000], ['day', 86400], ['hour', 3600], ['minute', 60]];
                  for (const [k, v] of u) { if (Math.abs(d) >= v) return rtf.format(Math.round(d / v), k); }
                  return "à l'instant";
                };
                return (
                  <div key={p.id} className="home-card" role="button" tabIndex={0} onClick={ouvrir} onKeyDown={(e) => { if (e.key === 'Enter') ouvrir(); }}>
                    <div className="home-thumb">
                      <div className="home-thumb-fallback"><IconPackage size={40} /></div>
                      {p.statut !== 'erreur' && <MiniatureApp code={p.code_genere} />}
                      {p.apercu && <img src={p.apercu} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.display = 'none'; }} />}
                      {st[0] !== 'ok' && <span className={`home-badge home-badge-${st[0]}`}>{st[1]}</span>}
                    </div>
                    <div onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
                      <button type="button" className="home-menu-btn" aria-label="Actions du projet" aria-expanded={menuProjetId === p.id} onClick={() => setMenuProjetId(menuProjetId === p.id ? null : p.id)}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg>
                      </button>
                      {menuProjetId === p.id && (
                        <>
                          <div className="home-menu-overlay" onClick={() => setMenuProjetId(null)} />
                          <div className="home-menu" role="menu">
                            <button type="button" role="menuitem" onClick={async () => {
                              setMenuProjetId(null);
                              const saisie = window.prompt('Nouveau nom du projet', p.nom);
                              if (saisie === null) return;
                              const nom = saisie.trim();
                              if (!nom || nom === p.nom) return;
                              if (nom.length > 120) { alert('Le nom est trop long (120 caractères maximum).'); return; }
                              const ancien = p.nom;
                              setRecentProjects((prev) => prev.map((x: any) => x.id === p.id ? { ...x, nom } : x));
                              try {
                                await api.renameProject(p.id, nom);
                              } catch (err: any) {
                                setRecentProjects((prev) => prev.map((x: any) => x.id === p.id ? { ...x, nom: ancien } : x));
                                alert(`Erreur: ${err.message}`);
                              }
                            }}>
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                              Renommer
                            </button>
                            <button type="button" role="menuitem" onClick={async () => {
                              setMenuProjetId(null);
                              try {
                                const res: any = await api.duplicateProject(p.id);
                                const np = res?.project || res;
                                if (np && np.id) setRecentProjects((prev) => [{ ...np, parentWorkspaceId: p.parentWorkspaceId }, ...prev].slice(0, 6));
                              } catch (err: any) { alert(`Erreur: ${err.message}`); }
                            }}>
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/></svg>
                              Dupliquer
                            </button>
                            <button type="button" role="menuitem" className="danger" onClick={async () => {
                              setMenuProjetId(null);
                              if (!window.confirm(`Supprimer « ${p.nom} » ? Cette action est définitive.`)) return;
                              try {
                                await api.deleteProject(p.id);
                                setRecentProjects((prev) => prev.filter((x: any) => x.id !== p.id));
                              } catch (err: any) { alert(`Erreur: ${err.message}`); }
                            }}>
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/></svg>
                              Supprimer
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                    <div className="home-card-row">
                      <div className="home-card-text">
                        <h4 className="home-card-name">
                          <span className="home-card-title">{p.nom}</span>
                          {p.est_deploye && <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>}
                        </h4>
                        <p className="home-card-author">par {user.username}</p>
                        <p className="home-card-date">{depuis(p.created_at)}</p>
                      </div>
                      <button
                        type="button"
                        className={`home-card-go ${ouvertureId === p.id ? 'is-opening' : ''}`}
                        disabled={ouvertureId !== null}
                        aria-label={`Ouvrir ${p.nom}`}
                        onKeyDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          setOuvertureId(p.id);
                          setTimeout(() => { setOuvertureId(null); ouvrir(); }, 700);
                        }}
                      >
                        {ouvertureId === p.id ? 'Modifier' : <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
