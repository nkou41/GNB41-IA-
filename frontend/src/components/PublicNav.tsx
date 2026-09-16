import { api } from '../api';

type PublicPageType = 'accueil' | 'fonctionnalites' | 'tarifs' | 'templates' | 'apropos' | 'contact' | 'boutique' | null;

interface PublicNavProps {
  setPublicPage: (page: PublicPageType) => void;
  navigateTo: (path: string) => void;
  setShowAuth: (v: boolean) => void;
  setAuthMode: (v: 'login' | 'register') => void;
  setTemplatesList: (v: any[]) => void;
  setPublicListings: (v: any[]) => void;
  showPublicMenu: boolean;
  setShowPublicMenu: (v: boolean) => void;
}

export default function PublicNav({
  setPublicPage,
  navigateTo,
  setShowAuth,
  setAuthMode,
  setTemplatesList,
  setPublicListings,
  showPublicMenu,
  setShowPublicMenu,
}: PublicNavProps) {
  return (
    <>
      <div className="public-navbar">
        <span className="public-navbar-logo" onClick={() => { setPublicPage(null); navigateTo('/'); }}>GNB41 IA</span>
        <div className="public-navbar-links">
          <span onClick={() => { setPublicPage(null); navigateTo('/'); }}>Accueil</span>
          <span onClick={() => { setPublicPage('fonctionnalites'); navigateTo('/fonctionnalites'); }}>Fonctionnalités</span>
          <span onClick={() => { setPublicPage('tarifs'); navigateTo('/tarifs'); }}>Tarifs</span>
          <span onClick={() => { setPublicPage('templates'); api.listTemplates().then(setTemplatesList).catch(() => {}); navigateTo('/templates'); }}>Templates</span>
          <span onClick={() => { setPublicPage('boutique'); api.listMarketplace().then((res: any) => setPublicListings(res.listings)).catch(() => {}); navigateTo('/boutique'); }}>Boutique</span>
          <span onClick={() => { setPublicPage('apropos'); navigateTo('/a-propos'); }}>À propos</span>
          <span onClick={() => { setPublicPage('contact'); navigateTo('/contact'); }}>Contact</span>
        </div>
        <button className="public-navbar-cta" onClick={() => { setPublicPage(null); setShowAuth(true); setAuthMode('login'); navigateTo('/'); }}>Se connecter</button>
        <button type="button" className="public-navbar-burger" onClick={() => setShowPublicMenu(!showPublicMenu)}>☰</button>
      </div>
      {showPublicMenu && (
        <div className="public-navbar-mobile-menu">
          <span onClick={() => { setShowPublicMenu(false); setPublicPage(null); navigateTo('/'); }}>Accueil</span>
          <span onClick={() => { setShowPublicMenu(false); setPublicPage('fonctionnalites'); navigateTo('/fonctionnalites'); }}>Fonctionnalités</span>
          <span onClick={() => { setShowPublicMenu(false); setPublicPage('tarifs'); navigateTo('/tarifs'); }}>Tarifs</span>
          <span onClick={() => { setShowPublicMenu(false); setPublicPage('templates'); api.listTemplates().then(setTemplatesList).catch(() => {}); navigateTo('/templates'); }}>Templates</span>
          <span onClick={() => { setShowPublicMenu(false); setPublicPage('boutique'); api.listMarketplace().then((res: any) => setPublicListings(res.listings)).catch(() => {}); navigateTo('/boutique'); }}>Boutique</span>
          <span onClick={() => { setShowPublicMenu(false); setPublicPage('apropos'); navigateTo('/a-propos'); }}>À propos</span>
          <span onClick={() => { setShowPublicMenu(false); setPublicPage('contact'); navigateTo('/contact'); }}>Contact</span>
        </div>
      )}
    </>
  );
}
