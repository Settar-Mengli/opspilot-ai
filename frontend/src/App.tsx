import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import { getHealth, getTriage, editMailDraft, approveMailDraft, formatMailHitlError } from './api/client'
import { askOpsPilotStream } from './api/askStream'
import type { AskDraftCard, AskMessage, AskToolStep } from './api/types'
import { Brand } from './components/Brand'
import { AssistantPill } from './components/AssistantPill'
import { HealthBell } from './components/HealthBell'
import { NotifyPanel } from './components/NotifyPanel'
import { MobileDock } from './components/MobileDock'
import { VoiceOverlay } from './components/VoiceOverlay'
import { Onboarding } from './components/Onboarding'
import { AskPanel } from './components/AskPanel'
import { AskDock } from './components/AskDock'
import { PrimaryRail } from './components/PrimaryRail'
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
import { useMinWidth } from './hooks/useMinWidth'
import { deriveObservations } from './utils/observations'
import type { Observation } from './utils/observations'

function App() {
  const isDesktop = useMinWidth(1280)
  const [healthy, setHealthy] = useState(true)
  const [notifyOpen, setNotifyOpen] = useState(false)
  const [voiceOpen, setVoiceOpen] = useState(false)
  const [askOpen, setAskOpen] = useState(false)
  const [eveningOpen, setEveningOpen] = useState(false)
  const [userName, setUserName] = useUserName()
  const [assistantName, setAssistantName, hasChosenAssistant] = useAssistantName()
  const [observations, setObservations] = useState<Observation[]>([])

  const [askMessages, setAskMessages] = useState<AskMessage[]>([])
  const [askInput, setAskInput] = useState('')
  const [askLoading, setAskLoading] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)
  const [askFocusToken, setAskFocusToken] = useState(0)
  const [askToolSteps, setAskToolSteps] = useState<AskToolStep[]>([])
  const [askDraft, setAskDraft] = useState<AskDraftCard | null>(null)
  const dockInputRef = useRef<HTMLInputElement>(null)
  const askAbortRef = useRef<AbortController | null>(null)

  const sendAsk = useCallback(
    async (question: string) => {
      const clean = question.trim()
      if (!clean) return
      setAskError(null)
      setAskToolSteps([])
      setAskDraft(null)
      const userMsg: AskMessage = {
        id: `u-${Date.now()}`,
        role: 'user',
        text: clean,
        timestamp: Date.now(),
      }
      const history = askMessages.slice(-10).map((m) => ({
        role: m.role,
        content: m.text,
      }))
      setAskMessages((m) => [...m, userMsg])
      setAskInput('')
      setAskLoading(true)
      askAbortRef.current?.abort()
      const ac = new AbortController()
      askAbortRef.current = ac
      let streamed = ''
      const assistantId = `a-${Date.now()}`
      try {
        await askOpsPilotStream(
          clean,
          assistantName,
          history,
          {
            onToken: (text) => {
              streamed = text
              setAskMessages((msgs) => {
                const without = msgs.filter((x) => x.id !== assistantId)
                return [
                  ...without,
                  {
                    id: assistantId,
                    role: 'assistant',
                    text: streamed,
                    timestamp: Date.now(),
                  },
                ]
              })
            },
            onToolStart: (tool) => {
              setAskToolSteps((steps) => [
                ...steps,
                { id: `t-${Date.now()}-${tool}`, tool, status: 'running' },
              ])
            },
            onToolEnd: (tool, ok) => {
              setAskToolSteps((steps) => {
                const copy = [...steps]
                for (let i = copy.length - 1; i >= 0; i -= 1) {
                  if (copy[i]?.tool === tool && copy[i]?.status === 'running') {
                    copy[i] = { ...copy[i]!, status: ok ? 'done' : 'error' }
                    break
                  }
                }
                return copy
              })
            },
            onDraft: (d) => {
              setAskDraft({
                draftId: d.draft_id,
                subject: d.subject,
                body: d.body,
                toAddrs: d.to_addrs,
                sentAt: null,
                approveError: null,
              })
            },
            onFinal: (answer) => {
              streamed = answer || streamed
              setAskMessages((msgs) => {
                const without = msgs.filter((x) => x.id !== assistantId)
                return [
                  ...without,
                  {
                    id: assistantId,
                    role: 'assistant',
                    text: streamed || 'I did not get a response. Please try again.',
                    timestamp: Date.now(),
                  },
                ]
              })
            },
            onError: (message) => {
              setAskError(message)
            },
          },
          ac.signal,
        )
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        setAskError(e instanceof Error ? e.message : 'Something went wrong.')
      } finally {
        setAskLoading(false)
      }
    },
    [assistantName, askMessages],
  )

  const handleAskSubmit = useCallback(() => {
    if (askLoading) return
    void sendAsk(askInput)
  }, [askLoading, askInput, sendAsk])

  const handleAsk = useCallback(
    (question: string) => {
      if (isDesktop) {
        if (question.trim()) void sendAsk(question)
        setAskFocusToken((t) => t + 1)
        return
      }
      if (question.trim()) {
        void sendAsk(question)
      }
      setAskOpen(true)
    },
    [isDesktop, sendAsk],
  )

  const openAskPanel = useCallback(() => {
    handleAsk('')
  }, [handleAsk])

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

  useEffect(() => {
    getHealth().then(setHealthy).catch(() => setHealthy(false))
  }, [])

  useEffect(() => {
    getTriage()
      .then((records) => setObservations(deriveObservations(records)))
      .catch(() => setObservations([]))
  }, [])

  // When the viewport crosses into desktop, close modal Ask and focus the dock (same thread).
  const [desktopForAsk, setDesktopForAsk] = useState(isDesktop)
  if (isDesktop !== desktopForAsk) {
    setDesktopForAsk(isDesktop)
    if (isDesktop && askOpen) {
      setAskOpen(false)
      setAskFocusToken((t) => t + 1)
    }
  }

  if (userName === null || !hasChosenAssistant) {
    return (
      <Onboarding
        onComplete={(user, assistant) => {
          setUserName(user)
          setAssistantName(assistant)
        }}
      />
    )
  }

  const askThread = {
    assistantName,
    messages: askMessages,
    toolSteps: askToolSteps,
    draft: askDraft,
    onDraftSubjectChange: (value: string) =>
      setAskDraft((d) => (d ? { ...d, subject: value } : d)),
    onDraftBodyChange: (value: string) => setAskDraft((d) => (d ? { ...d, body: value } : d)),
    onApproveDraft: () => {
      void (async () => {
        if (!askDraft || askDraft.sentAt) return
        setAskDraft((d) => (d ? { ...d, approveError: null } : d))
        try {
          const edited = await editMailDraft(askDraft.draftId, askDraft.subject, askDraft.body)
          await approveMailDraft(edited.id, edited.payload_sha256)
          setAskDraft((d) => (d ? { ...d, sentAt: Date.now(), approveError: null } : d))
        } catch (e) {
          const message = formatMailHitlError(e)
          setAskDraft((d) => (d ? { ...d, approveError: message } : d))
        }
      })()
    },
    input: askInput,
    loading: askLoading,
    error: askError,
    onInputChange: setAskInput,
    onSubmit: handleAskSubmit,
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {isDesktop && <PrimaryRail />}

      <div className="app-center">
        <header className="top-nav">
          <Brand />
          <div className="nav-right">
            <HealthBell
              hasNotifications={observations.length > 0}
              onClick={() => setNotifyOpen((o) => !o)}
            />
            <AssistantPill assistantName={assistantName} />
            <NavLink to="/connections" className="nav-gear" aria-label="Connections">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1.08 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1.08z" />
              </svg>
            </NavLink>
          </div>
        </header>

        <NotifyPanel
          open={notifyOpen}
          notifications={observations}
          assistantName={assistantName}
          onClose={() => setNotifyOpen(false)}
        />

        {!healthy && (
          <div className="api-banner">
            <span>API unavailable. OpsPilot could not reach the backend.</span>
            <button type="button" onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        )}

        <main id="main-content" className="content-shell">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route
                path="/dashboard"
                element={
                  <DashboardPage
                    userName={userName}
                    assistantName={assistantName}
                    onAsk={handleAsk}
                    onEveningClick={() => setEveningOpen(true)}
                  />
                }
              />
              <Route path="/items" element={<AllItemsPage onAsk={handleAsk} />} />
              <Route
                path="/insights"
                element={<InsightsPage assistantName={assistantName} onAsk={handleAsk} />}
              />
              <Route path="/briefing" element={<BriefingPage />} />
              <Route path="/connections" element={<ConnectionsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>

      {isDesktop && (
        <AskDock
          {...askThread}
          inputRef={dockInputRef}
          focusToken={askFocusToken}
        />
      )}

      <MobileDock
        assistantName={assistantName}
        onMicClick={handleMicClick}
        onAsk={handleAsk}
        voiceSupported={speechSupported}
      />
      <VoiceOverlay
        open={voiceOpen}
        listening={speech.listening}
        transcript={speech.transcript}
        interimTranscript={speech.interimTranscript}
        error={speech.error}
        onClose={handleVoiceClose}
      />
      {!isDesktop && (
        <AskPanel
          open={askOpen}
          onClose={() => setAskOpen(false)}
          {...askThread}
        />
      )}
      {eveningOpen && (
        <EveningPanel open={eveningOpen} assistantName={assistantName} onClose={() => setEveningOpen(false)} />
      )}
    </div>
  )
}

export default App
