import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './theme.css'
import App from './App.tsx'
import { ReadyGate } from './components/ReadyGate'
import { ErrorBoundary } from './components/ErrorBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <ReadyGate>
        <App />
      </ReadyGate>
    </ErrorBoundary>
  </StrictMode>,
)
