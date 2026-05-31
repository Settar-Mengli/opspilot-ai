import { useEffect, useRef, useState, useCallback } from 'react'
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
import { DashboardPage } from './pages/DashboardPage'
import { AllItemsPage } from './pages/AllItemsPage'
import { InsightsPage } from './pages/InsightsPage'
import { BriefingPage } from './pages/BriefingPage'
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
  const askPilotRef = useRef<HTMLInputElement>(null)

  const focusAskPilot = useCallback(() => {
    askPilotRef.current?.focus()
  }, [])

  useGlobalShortcut('k', focusAskPilot)

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
    speech.stop()
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
        <nav className="nav-tabs" aria-label="Primary">
          <NavLink to="/dashboard" className={({isActive}) => `nav-tab ${isActive ? 'active' : ''}`}>Dashboard</NavLink>
          <NavLink to="/items" className={({isActive}) => `nav-tab ${isActive ? 'active' : ''}`}>All items</NavLink>
          <NavLink to="/insights" className={({isActive}) => `nav-tab ${isActive ? 'active' : ''}`}>Insights</NavLink>
          <NavLink to="/briefing" className={({isActive}) => `nav-tab ${isActive ? 'active' : ''}`}>Briefing</NavLink>
        </nav>
        <div className="nav-right">
          <HealthBell hasNotifications={observations.length > 0} onClick={() => setNotifyOpen(o => !o)} />
          <AssistantPill assistantName={assistantName} />
        </div>
      </header>

      <NotifyPanel open={notifyOpen} notifications={observations} assistantName={assistantName} />

      {!healthy && (
        <div className="api-banner">
          <span>API unavailable. OpsPilot could not reach the backend.</span>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}

      <main className="content-shell">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage userName={userName} assistantName={assistantName} askPilotRef={askPilotRef} onMicClick={handleMicClick} onAsk={handleAsk} onEveningClick={() => setEveningOpen(true)} voiceSupported={speechSupported} />} />
          <Route path="/items" element={<AllItemsPage />} />
          <Route path="/insights" element={<InsightsPage assistantName={assistantName} />} />
          <Route path="/briefing" element={<BriefingPage />} />
        </Routes>
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
