import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './ErrorBoundary.tsx'
import WebContainerTest from './WebContainerTest.tsx'
import { initAnalytics } from './analytics'

initAnalytics()

// TEMPORAIRE: test isole de WebContainerTest.
// Mettre WEBCONTAINER_TEST_MODE a false pour revenir a l'app normale.
const WEBCONTAINER_TEST_MODE = true

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      {WEBCONTAINER_TEST_MODE ? <WebContainerTest /> : <App />}
    </ErrorBoundary>
  </StrictMode>,
)
