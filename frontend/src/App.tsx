import { useEffect, useState, useCallback } from 'react'
import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import { getHealth, getTriage } from './api/client'
import { Brand } from './components/Brand'
import { AssistantPill } from './components/AssistantPill'
import { HealthBell } from './components/HealthBell'
import { NotifyPanel } from './components/NotifyPanel'
import { MobileDock } from './components/MobileDock'
import { VoiceOverlay } from './components/VoiceOverlay'
import { Onboarding } from './components/Onboarding'
import { AskPanel } from './components/AskPanel'
import { EveningPanel } from './components/EveningPanel'
import { ErrorBoundary } from './components/ErrorBoundary'
import { DashboardPage } from './pages/DashboardPage'
import { AllItemsPage } from './pages/AllItemsPage'
import { InsightsPage } from './pages/InsightsPage'
import { BriefingPage } from './pages/BriefingPage'
import { ConnectionsPage } from './pages/ConnectionsPage'
import { SettingsPage } from './pages/SettingsPage'
import { useUserName } from './hooks/useUserName'
import { useAssistantName } from './hooks/useAssistantName'
import { useGlobalShortcut } from './hooks/useGlobalShortcut'
import { useSpeechRecognition, isSpeechRecognitionSupported } from './hooks/useSpeechRecognition'
import { deriveObservations } from './utils/observations'
import type { Observation } from './utils/observations'

function App() {
  const [healthy, setHealthy] = useState(true)
  const [notifyOpen, setNotifyOpen] = useState(false)
  const [voiceOpen, setVoiceOpen] = useState(false)
  const [askOpen, setAskOpen] = useState(false)
  const [eveningOpen, setEveningOpen] = useState(false)
  const [askInitialQuestion, setAskInitialQuestion] = useState('')
  const [userName, setUserName] = useUserName()
  const [assistantName, setAssistantName, hasChosenAssistant] = useAssistantName()
  const [observations, setObservations] = useState<Observation[]>([])

  const openAskPanel = useCallback(() => {
    handleAsk('')
  }, [])

  useGlobalShortcut('k', openAskPanel)

  const speechSupported = isSpeechRecognitionSupported()

  const speech = useSpeechRecognition({
    onFinalTranscript: (text) => {
      handleAsk(text)
      setVoiceOpen(false)
    },
  })

  function handleMicClick() {
    if (!speechSupported) return
    setVoiceOpen(true)
    speech.start()
  }

  function handleVoiceClose() {
    speech.cancel()
    setVoiceOpen(false)
  }

  function handleAsk(question: string) {
    setAskInitialQuestion(question)
    setAskOpen(true)
  }

  useEffect(() => {
    getHealth().then(setHealthy).catch(() => setHealthy(false))
  }, [])

  useEffect(() => {
    getTriage()
      .then(records => setObservations(deriveObservations(records)))
      .catch(() => setObservations([]))
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
        <div className="nav-right">
          <HealthBell hasNotifications={observations.length > 0} onClick={() => setNotifyOpen(o => !o)} />
          <AssistantPill assistantName={assistantName} />
          <NavLink to="/connections" className="nav-gear" aria-label="Connections">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1.08 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1.08z"/></svg>
          </NavLink>
        </div>
      </header>

      <NotifyPanel open={notifyOpen} notifications={observations} assistantName={assistantName} onClose={() => setNotifyOpen(false)} />

      {!healthy && (
        <div className="api-banner">
          <span>API unavailable. OpsPilot could not reach the backend.</span>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}

      <main className="content-shell">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage userName={userName} assistantName={assistantName} onAsk={handleAsk} onEveningClick={() => setEveningOpen(true)} />} />
            <Route path="/items" element={<AllItemsPage />} />
            <Route path="/insights" element={<InsightsPage assistantName={assistantName} onAsk={handleAsk} />} />
            <Route path="/briefing" element={<BriefingPage />} />
            <Route path="/connections" element={<ConnectionsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </ErrorBoundary>
      </main>

      <MobileDock assistantName={assistantName} onMicClick={handleMicClick} onAsk={handleAsk} voiceSupported={speechSupported} />
      <VoiceOverlay
        open={voiceOpen}
        listening={speech.listening}
        transcript={speech.transcript}
        interimTranscript={speech.interimTranscript}
        error={speech.error}
        onClose={handleVoiceClose}
      />
      {askOpen && (
        <AskPanel open={askOpen} assistantName={assistantName} initialQuestion={askInitialQuestion} onClose={() => setAskOpen(false)} />
      )}
      {eveningOpen && (
        <EveningPanel open={eveningOpen} assistantName={assistantName} onClose={() => setEveningOpen(false)} />
      )}
    </div>
  )
}

export default App
