import PublicNav from '../components/PublicNav';
import AnimatedPlaceholder from '../components/AnimatedPlaceholder';

interface AccueilProps {
  navProps: any;
  landingPrompt: string;
  setLandingPrompt: (v: string) => void;
  landingModel: string;
  setLandingModel: (v: string) => void;
  agentMode: string;
  setAgentMode: (v: string) => void;
  handleLandingSubmit: (e: React.FormEvent) => void;
}

export default function Accueil({
  navProps,
  landingPrompt,
  setLandingPrompt,
  landingModel,
  setLandingModel,
  agentMode,
  setAgentMode,
  handleLandingSubmit,
}: AccueilProps) {
  const { setShowAuth, setAuthMode } = navProps;
  return (
    <div className="landing">
      <PublicNav {...navProps} />
      <div className="landing-hero">
        <img src="/logo.png" alt="GNB41 IA" className="app-logo app-logo-lg" />
        <h1>GNB41 IA</h1>
        <p className="landing-tagline">Décrivez votre application. L'IA la construit pour vous.</p>
        <div className="landing-badge">⚡ IA &bull; Code &bull; Apps &bull; Web</div>

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
              <option value="mistral">Modèle: Mistral</option>
              <option value="claude">Modèle: Claude</option>
              <option value="openai">Modèle: GPT</option>
              <option value="gemini">Modèle: Gemini</option>
            </select>
            <select value={agentMode} onChange={(e) => setAgentMode(e.target.value)} className="landing-select">
              <option value="auto">Agent: Auto</option>
              <option value="creation">Agent: Création</option>
              <option value="modification">Agent: Modification</option>
              <option value="style">Agent: Design/Style</option>
              <option value="contenu">Agent: Contenu</option>
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
      <button type="button" className="landing-float-btn" title="Assistant" onClick={() => { setShowAuth(true); setAuthMode('register'); }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="8" width="18" height="12" rx="2"/><circle cx="8.5" cy="14" r="1.5" fill="#fff"/><circle cx="15.5" cy="14" r="1.5" fill="#fff"/><path d="M12 8V4"/><circle cx="12" cy="3" r="1" fill="#fff"/></svg>
      </button>
      <div className="landing-features">
        <div className="feature-card landing-feature-row">
          <span className="feature-icon feature-icon-blue">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
          </span>
          <span className="feature-text">
            <h3>Espaces de travail</h3>
            <p>Organisez vos projets par équipe ou par thème, avec des collaborateurs invités.</p>
          </span>
          <span className="feature-chevron">›</span>
        </div>
        <div className="feature-card landing-feature-row">
          <span className="feature-icon feature-icon-purple">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </span>
          <span className="feature-text">
            <h3>Génération IA</h3>
            <p>Décrivez votre idée en langage naturel, obtenez du code fonctionnel.</p>
          </span>
          <span className="feature-chevron">›</span>
        </div>
        <div className="feature-card landing-feature-row">
          <span className="feature-icon feature-icon-green">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </span>
          <span className="feature-text">
            <h3>Itération rapide</h3>
            <p>Régénérez, affinez, gardez un historique complet de chaque version.</p>
          </span>
          <span className="feature-chevron">›</span>
        </div>
        <div className="landing-decor-tagline">Transformez vos idées<br/>en applications !</div>
      </div>
    </div>
  );
}
