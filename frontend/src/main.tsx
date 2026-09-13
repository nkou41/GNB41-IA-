import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './ErrorBoundary.tsx'
import WebContainerTest from './WebContainerTest.tsx'
import { initAnalytics } from './analytics'

initAnalytics()

// TEMPORAIRE: test isole de WebContainerTest.
// Mettre WEBCONTAINER_TEST_MODE a false pour revenir a l'app normale.
const WEBCONTAINER_TEST_MODE = false

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        {WEBCONTAINER_TEST_MODE ? <WebContainerTest /> : <App />}
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
)
