import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { SimpleModeProvider } from './contexts/SimpleModeContext'
import { AIPreferencesProvider } from './contexts/AIPreferencesContext'
import { MockAuthProvider } from './contexts/MockAuthContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MockAuthProvider>
      <AIPreferencesProvider>
        <SimpleModeProvider>
          <App />
        </SimpleModeProvider>
      </AIPreferencesProvider>
    </MockAuthProvider>
  </StrictMode>,
)
