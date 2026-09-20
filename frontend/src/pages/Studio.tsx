import { useEffect, useState } from 'react';
import { api } from '../api';
import { IconArrowLeft, IconKey, IconCopy, IconInfoCircle } from '../Icons';

export default function Studio({ user, onBack }: { user: any; onBack: () => void }) {
  const [overview, setOverview] = useState<any>(null);
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [nomNouvelleCle, setNomNouvelleCle] = useState('');
  const [envNouvelleCle, setEnvNouvelleCle] = useState('live');
  const [creationEnCours, setCreationEnCours] = useState(false);
  const [cleRevelee, setCleRevelee] = useState<string | null>(null);
  const [erreur, setErreur] = useState('');
  const [copie, setCopie] = useState(false);

  const estPro = user?.plan === 'pro';

  const charger = () => {
    if (!estPro) { setLoading(false); return; }
    Promise.all([api.studioOverview(), api.studioListKeys()])
      .then(([ov, ks]) => { setOverview(ov); setKeys(ks); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { charger(); }, []);

  const creerCle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nomNouvelleCle.trim()) return;
    setCreationEnCours(true);
    setErreur('');
    try {
      const res = await api.studioCreateKey(nomNouvelleCle.trim(), envNouvelleCle);
      setCleRevelee(res.key);
      setNomNouvelleCle('');
      charger();
    } catch (err: any) {
      setErreur(err.message || 'Erreur lors de la creation');
    } finally {
      setCreationEnCours(false);
    }
  };

  const revoquer = async (keyId: string) => {
    if (!window.confirm('Revoquer cette cle ? Toute application l\'utilisant cessera de fonctionner immediatement.')) return;
    await api.studioRevokeKey(keyId);
    charger();
  };

  if (!estPro) {
    return (
      <div className="marketplace-page">
        <header className="marketplace-header">
          <button type="button" className="app-header-back" onClick={onBack}>
            <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
            <span className="app-header-back-title">GNB41 IA</span>
          </button>
        </header>
        <div style={{ padding: '2rem 1.5rem', maxWidth: '520px', margin: '0 auto', textAlign: 'center' }}>
          <div className="landing-badge" style={{ margin: '0 auto 1rem' }}><IconKey size={28} /></div>
          <h2>Studio GNB41 IA</h2>
          <p style={{ color: '#8a7f68', marginTop: '0.6rem' }}>
            Le Studio (cles API developpeur, generation via API, dashboard d'usage) est reserve au plan Pro.
          </p>
          <a href="/tarifs" className="btn-publish" style={{ marginTop: '1.2rem', display: 'inline-flex' }}>Passer au Pro</a>
        </div>
      </div>
    );
  }

  return (
    <div className="marketplace-page">
      <header className="marketplace-header">
        <button type="button" className="app-header-back" onClick={onBack}>
          <span className="app-header-back-icon"><IconArrowLeft size={18} /></span>
          <span className="app-header-back-title">GNB41 IA</span>
        </button>
      </header>

      <div className="marketplace-title-row">
        <div>
          <h2>Studio</h2>
          <p>Cles API pour integrer GNB41 IA dans vos propres outils et applications</p>
        </div>
      </div>

      {overview && (
        <div className="admin-stats-grid">
          <div className="admin-stat-card admin-stat-blue">
            <span className="admin-stat-label">Cles actives</span>
            <span className="admin-stat-value">{overview.cles_actives}</span>
          </div>
          <div className="admin-stat-card admin-stat-purple">
            <span className="admin-stat-label">Appels (7 jours)</span>
            <span className="admin-stat-value">{overview.appels_7j}</span>
          </div>
          <div className="admin-stat-card admin-stat-green">
            <span className="admin-stat-label">Appels (30 jours)</span>
            <span className="admin-stat-value">{overview.appels_30j}</span>
          </div>
        </div>
      )}

      <div style={{ padding: '0 1.5rem 2rem', maxWidth: '640px' }}>
        <div className="settings-card" style={{ marginBottom: '1.2rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>Nouvelle cle</h3>
          <form onSubmit={creerCle} style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <div className="settings-input-pill-wrap">
              <label><IconKey size={16} /> Nom de la cle</label>
              <input placeholder="Ex : Production, App mobile..." value={nomNouvelleCle} onChange={(e) => setNomNouvelleCle(e.target.value)} required />
            </div>
            <div style={{ display: 'flex', gap: '0.6rem' }}>
              <button type="button" className={`preview-tab ${envNouvelleCle === 'live' ? 'active' : ''}`} onClick={() => setEnvNouvelleCle('live')}>Live</button>
              <button type="button" className={`preview-tab ${envNouvelleCle === 'test' ? 'active' : ''}`} onClick={() => setEnvNouvelleCle('test')}>Test</button>
            </div>
            {erreur && <p className="error">{erreur}</p>}
            <button type="submit" className="auth-submit-btn" disabled={creationEnCours} style={{ alignSelf: 'flex-start', padding: '0.7rem 1.4rem' }}>
              {creationEnCours ? 'Creation...' : 'Creer la cle'}
            </button>
          </form>
        </div>

        {cleRevelee && (
          <div className="settings-card" style={{ marginBottom: '1.2rem', border: '1px solid #6366f1' }}>
            <p style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#6366f1', fontWeight: 600, marginBottom: '0.6rem' }}>
              <IconInfoCircle size={16} /> Copiez cette cle maintenant, elle ne sera plus affichee
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', background: '#f7f5f0', padding: '0.7rem 1rem', borderRadius: '10px', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '0.82rem' }}>
              <span style={{ flex: 1 }}>{cleRevelee}</span>
              <button type="button" className="toolbar-icon-btn" onClick={() => { navigator.clipboard.writeText(cleRevelee); setCopie(true); setTimeout(() => setCopie(false), 2000); }}>
                <IconCopy size={16} />
              </button>
            </div>
            {copie && <p style={{ fontSize: '0.78rem', color: '#16a34a', marginTop: '0.4rem' }}>Copie !</p>}
            <button type="button" className="switch" onClick={() => setCleRevelee(null)} style={{ marginTop: '0.8rem' }}>Fermer</button>
          </div>
        )}

        <h3 style={{ marginBottom: '0.8rem' }}>Vos cles</h3>
        {loading ? (
          <p style={{ color: '#8a7f68' }}>Chargement...</p>
        ) : keys.length === 0 ? (
          <p style={{ color: '#8a7f68' }}>Aucune cle API pour l'instant.</p>
        ) : (
          <ul className="versions-list">
            {keys.map((k: any) => (
              <li key={k.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <p style={{ fontWeight: 600 }}>{k.nom} <span className="marketplace-badge">{k.environnement}</span></p>
                    <p className="version-date">{k.key_prefix}... {k.revoked && '(revoquee)'}</p>
                  </div>
                  {!k.revoked && (
                    <button type="button" className="marketplace-link-btn" onClick={() => revoquer(k.id)}>Revoquer</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
