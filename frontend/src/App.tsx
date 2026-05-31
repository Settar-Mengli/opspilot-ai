import { useEffect, useRef, useState, useCallback } from 'react'
import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import { getHealth } from './api/client'
import { Brand } from './components/Brand'
import { AssistantPill } from './components/AssistantPill'
import { HealthBell } from './components/HealthBell'
import { NotifyPanel } from './components/NotifyPanel'
import { MobileDock } from './components/MobileDock'
import { VoiceOverlay } from './components/VoiceOverlay'
import { Onboarding } from './components/Onboarding'
import { DashboardPage } from './pages/DashboardPage'
import { AllItemsPage } from './pages/AllItemsPage'
import { BriefingPage } from './pages/BriefingPage'
import { useUserName } from './hooks/useUserName'
import { useAssistantName } from './hooks/useAssistantName'
import { useGlobalShortcut } from './hooks/useGlobalShortcut'

const MOCK_NOTIFICATIONS = [
  { id: '1', text: 'SRE acknowledged the checkout outage. Tracking response.', time: '12 minutes ago' },
  { id: '2', text: 'Customer ticket #4032 has been viewed by support lead.', time: '28 minutes ago' },
  { id: '3', text: '3 new items came in overnight — all medium priority.', time: '1 hour ago' },
]

function App() {
  const [healthy, setHealthy] = useState(true)
  const [notifyOpen, setNotifyOpen] = useState(false)
  const [voiceOpen, setVoiceOpen] = useState(false)
  const [userName, setUserName] = useUserName()
  const [assistantName, setAssistantName, hasChosenAssistant] = useAssistantName()
  const askPilotRef = useRef<HTMLInputElement>(null)

  const focusAskPilot = useCallback(() => {
    askPilotRef.current?.focus()
  }, [])

  useGlobalShortcut('k', focusAskPilot)

  useEffect(() => {
    getHealth().then(setHealthy).catch(() => setHealthy(false))
  }, [])

  if (userName === null || !hasChosenAssistant) {
    return <Onboarding onComplete={(user, assistant) => {
      setUserName(user)
      setAssistantName(assistant)
    }} />
  }

  return (
    <div className="app-shell">
      <header className="top-nav">
        <Brand />
        <nav className="nav-tabs" aria-label="Primary">
          <NavLink to="/dashboard" className={({isActive}) => `nav-tab ${isActive ? 'active' : ''}`}>Dashboard</NavLink>
          <NavLink to="/items" className={({isActive}) => `nav-tab ${isActive ? 'active' : ''}`}>All items</NavLink>
          <NavLink to="/briefing" className={({isActive}) => `nav-tab ${isActive ? 'active' : ''}`}>Briefing</NavLink>
        </nav>
        <div className="nav-right">
          <HealthBell hasNotifications={true} onClick={() => setNotifyOpen(o => !o)} />
          <AssistantPill assistantName={assistantName} />
        </div>
      </header>

      <NotifyPanel open={notifyOpen} notifications={MOCK_NOTIFICATIONS} />

      {!healthy && (
        <div className="api-banner">
          <span>API unavailable. OpsPilot could not reach the backend.</span>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}

      <main className="content-shell">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage userName={userName} assistantName={assistantName} askPilotRef={askPilotRef} onMicClick={() => setVoiceOpen(true)} />} />
          <Route path="/items" element={<AllItemsPage />} />
          <Route path="/briefing" element={<BriefingPage />} />
        </Routes>
      </main>

      <MobileDock assistantName={assistantName} onMicClick={() => setVoiceOpen(true)} />
      <VoiceOverlay open={voiceOpen} onClose={() => setVoiceOpen(false)} />
    </div>
  )
}

export default App
