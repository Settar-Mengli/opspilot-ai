import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCapabilities } from '../api/client'
import type { Capability } from '../api/types'
import { Mail, MessageSquare, Calendar, FileText, Building2, CreditCard, Circle, Zap, ArrowLeft } from 'lucide-react'

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
  { id: 'email', name: 'Email', category: 'email', apps: ['Gmail', 'Outlook', 'Mailgun'], status: 'coming_soon', featured: false, description: '' },
  { id: 'chat', name: 'Chat', category: 'chat', apps: ['Slack', 'Discord', 'Teams'], status: 'coming_soon', featured: false, description: '' },
  { id: 'calendar', name: 'Calendar', category: 'calendar', apps: ['Google', 'Outlook'], status: 'coming_soon', featured: false, description: '' },
  { id: 'documents', name: 'Documents', category: 'documents', apps: ['Docs', 'Notion', 'Dropbox'], status: 'coming_soon', featured: false, description: '' },
  { id: 'crm', name: 'CRM', category: 'crm', apps: ['Salesforce', 'HubSpot'], status: 'coming_soon', featured: false, description: '' },
  { id: 'payments', name: 'Payments', category: 'payments', apps: ['Stripe', 'banking'], status: 'coming_soon', featured: false, description: '' },
]

export function ConnectionsPage() {
  const navigate = useNavigate()
  const [capabilities, setCapabilities] = useState<Capability[]>(FALLBACK_CAPS)
  const [modalCap, setModalCap] = useState<Capability | null>(null)

  useEffect(() => {
    let cancelled = false
    getCapabilities()
      .then(caps => { if (!cancelled) setCapabilities(caps) })
      .catch(() => { /* keep fallback */ })
    return () => { cancelled = true }
  }, [])

  // Modal scroll-lock + Escape-to-close
  useEffect(() => {
    if (!modalCap) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setModalCap(null)
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [modalCap])

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

      {featured && (
        <div className="cn-feature">
          <div className="cn-feat-top">
            <span className="cn-feat-ic"><Zap size={24} /></span>
            <span className="cn-badge">Recommended</span>
          </div>
          <p className="cn-feat-head">One connection. 250+ apps.</p>
          <p className="cn-feat-sub">{featured.description}</p>
          <button className="cn-feat-btn" onClick={() => setModalCap(featured)}>Coming soon</button>
        </div>
      )}

      <p className="cn-sec">Or connect by category</p>

      {categories.map(cap => {
        const Icon = CATEGORY_ICONS[cap.category] || Circle
        return (
          <div key={cap.id} className="cn-cat" onClick={() => setModalCap(cap)}>
            <span className="cn-cat-ic"><Icon size={18} /></span>
            <span className="cn-cat-info">
              <p className="cn-cat-name">{cap.name}</p>
              <p className="cn-cat-apps">{cap.apps.join(' · ')}</p>
            </span>
            <span className="cn-cat-status"><Circle size={10} />Soon</span>
          </div>
        )
      })}

      {modalCap && (
        <div className="cn-modal-overlay" onClick={() => setModalCap(null)}>
          <div className="cn-modal" onClick={e => e.stopPropagation()}>
            <p className="cn-modal-txt">
              Connections are coming soon. <strong>{modalCap.name}</strong> will be available shortly — I'll let you know the moment it's ready.
            </p>
            <button className="cn-modal-close" onClick={() => setModalCap(null)}>Got it</button>
          </div>
        </div>
      )}
    </div>
  )
}
