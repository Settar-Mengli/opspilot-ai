import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getCapabilities, getApiSettings, postSync } from '../api/client'
import type { ApiSettings, Capability } from '../api/types'
import { Mail, MessageSquare, Calendar, FileText, Building2, CreditCard, Circle, Zap, ArrowLeft } from 'lucide-react'
import { useOverlay } from '../hooks/useOverlay'

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://127.0.0.1:8000'
const GRANT_REQUIRED_MSG = 'Grant Gmail and Calendar access to continue'

const CATEGORY_ICONS: Record<string, typeof Mail> = {
  email: Mail,
  chat: MessageSquare,
  calendar: Calendar,
  documents: FileText,
  crm: Building2,
  payments: CreditCard,
}

const FALLBACK_CAPS: Capability[] = [
  { id: 'composio', name: 'Composio', category: 'aggregator', apps: ['Gmail', 'Slack', 'Salesforce', 'Stripe'], status: 'coming_soon', featured: true, description: 'One connection. 250+ apps. Connect once and unlock Gmail, Slack, Salesforce, Stripe, and more.' },
  { id: 'email', name: 'Email', category: 'email', apps: ['Gmail', 'Outlook', 'Mailgun'], status: 'available', featured: false, description: '' },
  { id: 'chat', name: 'Chat', category: 'chat', apps: ['Slack', 'Discord', 'Teams'], status: 'coming_soon', featured: false, description: '' },
  { id: 'calendar', name: 'Calendar', category: 'calendar', apps: ['Google', 'Outlook'], status: 'available', featured: false, description: '' },
  { id: 'documents', name: 'Documents', category: 'documents', apps: ['Docs', 'Notion', 'Dropbox'], status: 'coming_soon', featured: false, description: '' },
  { id: 'crm', name: 'CRM', category: 'crm', apps: ['Salesforce', 'HubSpot'], status: 'coming_soon', featured: false, description: '' },
  { id: 'payments', name: 'Payments', category: 'payments', apps: ['Stripe', 'banking'], status: 'coming_soon', featured: false, description: '' },
]

function statusLabel(status: Capability['status']): string {
  if (status === 'connected') return 'Connected'
  if (status === 'available') return 'Available'
  return 'Soon'
}

export function ConnectionsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [capabilities, setCapabilities] = useState<Capability[]>(FALLBACK_CAPS)
  const [settings, setSettings] = useState<ApiSettings | null>(null)
  const [modalCap, setModalCap] = useState<Capability | null>(null)
  const [syncMsg, setSyncMsg] = useState<string | null>(() =>
    searchParams.get('oauth_error') === 'grant_required' ? GRANT_REQUIRED_MSG : null,
  )
  const [syncing, setSyncing] = useState(false)
  const modalRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  const { onBackdropClick } = useOverlay({
    open: modalCap !== null,
    onClose: () => setModalCap(null),
    containerRef: modalRef,
  })

  const refresh = () => {
    getCapabilities().then(setCapabilities).catch(() => { /* keep */ })
    getApiSettings().then(setSettings).catch(() => { /* keep */ })
  }

  useEffect(() => {
    refresh()
  }, [])

  useEffect(() => {
    if (searchParams.get('oauth_error') !== 'grant_required') return
    const next = new URLSearchParams(searchParams)
    next.delete('oauth_error')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const demoMode = settings?.demo_mode === true
  const googleConnected = settings?.google_connected === true

  const connectGoogle = () => {
    window.location.href = `${API_ORIGIN}/api/v1/oauth/google/start`
  }

  const runSync = async () => {
    setSyncing(true)
    setSyncMsg(null)
    try {
      const result = await postSync()
      setSyncMsg(
        `Synced ${result.gmail_upserted} mail, ${result.calendar_upserted} meetings — triaged ${result.triaged}.`,
      )
      refresh()
    } catch (err) {
      setSyncMsg(err instanceof Error ? err.message : 'Sync failed.')
    } finally {
      setSyncing(false)
    }
  }

  const featured = capabilities.find(c => c.featured)
  const categories = capabilities.filter(c => !c.featured)

  return (
    <div className="cn-page">
      <div className="page-header">
        <button className="page-back" onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
          <ArrowLeft size={20} strokeWidth={2} />
        </button>
        <h2 className="page-header-title">Connections</h2>
      </div>

      <p className="cn-intro">
        Right now I can think, write, and plan with you. Connect me to your tools and I'll start acting on your behalf — always with your say-so.
      </p>

      {!demoMode && (
        <div className="cn-feature">
          <div className="cn-feat-top">
            <span className="cn-feat-ic"><Mail size={24} /></span>
            <span className="cn-badge">{googleConnected ? 'Connected' : 'Google'}</span>
          </div>
          <p className="cn-feat-head">Gmail + Calendar</p>
          <p className="cn-feat-sub">
            {googleConnected
              ? 'Operator Google account linked (readonly). Sync pulls fictional demo mail and the week ahead.'
              : 'Connect your Testing-mode Google account. Readonly Gmail and Calendar only.'}
          </p>
          {googleConnected ? (
            <button className="cn-feat-btn" type="button" disabled={syncing} onClick={() => { void runSync() }}>
              {syncing ? 'Syncing…' : 'Sync now'}
            </button>
          ) : (
            <button className="cn-feat-btn" type="button" onClick={connectGoogle}>
              Connect Google
            </button>
          )}
          {syncMsg && <p className="cn-feat-sub" role="status">{syncMsg}</p>}
        </div>
      )}

      {demoMode && (
        <p className="cn-intro" role="status">DEMO_MODE is on — Google connect is disabled for visitors.</p>
      )}

      {featured && (
        <div className="cn-feature">
          <div className="cn-feat-top">
            <span className="cn-feat-ic"><Zap size={24} /></span>
            <span className="cn-badge">Recommended</span>
          </div>
          <p className="cn-feat-head">One connection. 250+ apps.</p>
          <p className="cn-feat-sub">{featured.description}</p>
          <button className="cn-feat-btn" type="button" onClick={() => setModalCap(featured)}>Coming soon</button>
        </div>
      )}

      <p className="cn-sec">Or connect by category</p>

      {categories.map(cap => {
        const Icon = CATEGORY_ICONS[cap.category] || Circle
        return (
          <button
            key={cap.id}
            type="button"
            className="cn-cat"
            onClick={() => setModalCap(cap)}
          >
            <span className="cn-cat-ic"><Icon size={18} /></span>
            <span className="cn-cat-info">
              <p className="cn-cat-name">{cap.name}</p>
              <p className="cn-cat-apps">{cap.apps.join(' · ')}</p>
            </span>
            <span className="cn-cat-status"><Circle size={10} />{statusLabel(cap.status)}</span>
          </button>
        )
      })}

      {modalCap && (
        <div className="cn-modal-overlay" onClick={onBackdropClick}>
          <div
            ref={modalRef}
            className="cn-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            onClick={e => e.stopPropagation()}
          >
            <p className="cn-modal-txt" id={titleId}>
              {modalCap.id === 'email' || modalCap.id === 'calendar'
                ? (
                    <>
                      <strong>{modalCap.name}</strong> uses the Google connect button above
                      {demoMode ? ' (disabled in DEMO_MODE).' : '.'}
                    </>
                  )
                : (
                    <>
                      Connections are coming soon. <strong>{modalCap.name}</strong> will be available shortly — I'll let you know the moment it's ready.
                    </>
                  )}
            </p>
            <button className="cn-modal-close" type="button" onClick={() => setModalCap(null)}>Got it</button>
          </div>
        </div>
      )}
    </div>
  )
}
