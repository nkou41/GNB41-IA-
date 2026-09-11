// Systeme d'icones partage - style line-icons minimaliste (coherent avec les
// icones que l'IA genere dans les applications produites par la plateforme).
// Toutes les icones suivent le meme gabarit: viewBox 24x24, trait fin, coins arrondis.

type IconProps = { size?: number; className?: string };

const base = (children: React.ReactNode, { size = 20, className = '' }: IconProps = {}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    {children}
  </svg>
);

export const IconUser = (props: IconProps) => base(<><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/></>, props);
export const IconSmartphone = (props: IconProps) => base(<><rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/></>, props);
export const IconMail = (props: IconProps) => base(<><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></>, props);
export const IconLock = (props: IconProps) => base(<><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></>, props);
export const IconSave = (props: IconProps) => base(<><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/></>, props);
export const IconLink = (props: IconProps) => base(<><path d="M9 17H7a5 5 0 0 1 0-10h2"/><path d="M15 7h2a5 5 0 0 1 0 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/></>, props);
export const IconLogOut = (props: IconProps) => base(<><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></>, props);
export const IconCheckCircle = (props: IconProps) => base(<><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></>, props);
export const IconInfoCircle = (props: IconProps) => base(<><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></>, props);
export const IconPackage = (props: IconProps) => base(<><path d="M21 8l-9-5-9 5 9 5 9-5Z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/></>, props);
export const IconBell = (props: IconProps) => base(<><path d="M6 8a6 6 0 0 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 12 6 8Z"/><path d="M10 19a2 2 0 0 0 4 0"/></>, props);
