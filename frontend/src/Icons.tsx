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
export const IconEye = (props: IconProps) => base(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></>, props);
export const IconEyeOff = (props: IconProps) => base(<><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c6.5 0 10 8 10 8a17.4 17.4 0 0 1-3.13 4.12M6.6 6.6C3.9 8.3 2 12 2 12s3.5 8 10 8a9.27 9.27 0 0 0 5.4-1.6"/><path d="M14.12 14.12A3 3 0 1 1 9.88 9.88"/><line x1="2" y1="2" x2="22" y2="22"/></>, props);
export const IconArrowRight = (props: IconProps) => base(<><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></>, props);
export const IconSettings = (props: IconProps) => base(<><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></>, props);
export const IconGooglePlay = ({ size = 20, className = '' }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className}>
    <path d="M4 2.5c-.4.2-.6.6-.6 1.1v17c0 .5.2.9.6 1.1l9.6-9.6-9.6-9.6Z" fill="#00D2FF"/>
    <path d="M17 9.4l-3-1.7-9-5.2 9.4 9.5 2.6-2.6Z" fill="#00F076"/>
    <path d="M17 14.6l-2.6-2.6-9.4 9.5 9-5.2 3-1.7Z" fill="#FF3A44"/>
    <path d="M17 9.4L14.4 12l2.6 2.6 3.7-2.1c.6-.4.6-1.4 0-1.8L17 9.4Z" fill="#FFCA00"/>
  </svg>
);
export const IconArrowLeft = (props: IconProps) => base(<><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></>, props);
export const IconHome = (props: IconProps) => base(<><path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5"/></>, props);
export const IconStore = (props: IconProps) => base(<><path d="M3 9l1.5-5h15L21 9"/><path d="M3 9v10a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V9"/><path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/></>, props);
export const IconGrid = (props: IconProps) => base(<><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>, props);
export const IconMoon = (props: IconProps) => base(<><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z"/></>, props);
export const IconSun = (props: IconProps) => base(<><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>, props);
export const IconKey = (props: IconProps) => base(<><circle cx="7.5" cy="15.5" r="5.5"/><path d="M21 2l-9.6 9.6M15.5 7.5L18 10M18.5 4.5L21 7"/></>, props);
export const IconCopy = (props: IconProps) => base(<><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></>, props);
