import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiSettings, getTriage, upsertCorrection, deleteCorrection } from '../api/client'
import type { ApiSettings, TriageRecord, Category, Urgency, Sentiment, CorrectionPayload } from '../api/types'
import { LoopSkeleton } from '../components/skeletons/LoopSkeleton'
import { BulBulAvatar } from '../components/BulBulAvatar'
import { AlertTriangle, FileText, Users, Calendar, MessageCircle, ChevronRight, ArrowLeft } from 'lucide-react'
import { useMinWidth } from '../hooks/useMinWidth'
import { useOverlay } from '../hooks/useOverlay'

const categoryIcon: Record<Category, typeof AlertTriangle> = {
  incident: AlertTriangle,
  request: FileText,
  follow_up: Users,
  admin: Calendar,
  other: MessageCircle,
}

function categoryLabel(cat: Category): string {
  if (cat === 'follow_up') return 'Follow-up'
  return cat.charAt(0).toUpperCase() + cat.slice(1)
}

const urgencyOrder: Urgency[] = ['critical', 'high', 'medium', 'low']
const categoryOptions: Category[] = ['incident', 'request', 'admin', 'follow_up', 'other']
const sentimentOptions: Sentiment[] = ['negative', 'neutral', 'positive']

const dotClass: Record<Urgency, string> = {
  critical: 'fp-dot fp-dot--crit',
  high: 'fp-dot fp-dot--high',
  medium: 'fp-dot fp-dot--med',
  low: 'fp-dot fp-dot--low',
}

interface CorrectionState {
  urgency: Urgency
  category: Category
  sentiment: Sentiment
  saved: boolean
  saving: boolean
}

interface Props {
  onAsk?: (question: string) => void
}

export function AllItemsPage({ onAsk }: Props) {
  const navigate = useNavigate()
  const isDesktop = useMinWidth(1280)
  const isMedium = useMinWidth(768)
  const [records, setRecords] = useState<TriageRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [settings, setSettings] = useState<ApiSettings | null>(null)
  const [corrections, setCorrections] = useState<Record<string, CorrectionState>>({})
  const [sheetItemId, setSheetItemId] = useState<string | null>(null)
  const sheetRef = useRef<HTMLDivElement>(null)
  const sheetTitleId = useId()

  const showCorrections = settings?.google_connected === true && settings?.demo_mode !== true

  const { onBackdropClick } = useOverlay({
    open: sheetItemId !== null,
    onClose: () => setSheetItemId(null),
    containerRef: sheetRef,
  })

  useEffect(() => {
    let cancelled = false
    getTriage()
      .then((r) => {
        if (cancelled) return
        setRecords(r)
        setError(null)
        const first = urgencyOrder
          .flatMap((u) => r.filter((x) => x.urgency === u))
          .at(0)
        setSelectedId(first?.id ?? null)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load items.')
        setRecords([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    getApiSettings()
      .then((s) => {
        if (!cancelled) setSettings(s)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  function getCorrectionState(record: TriageRecord): CorrectionState {
    return (
      corrections[record.id] ?? {
        urgency: record.urgency,
        category: record.category,
        sentiment: record.sentiment,
        saved: false,
        saving: false,
      }
    )
  }

  function updateCorrection(id: string, patch: Partial<CorrectionState>) {
    setCorrections((prev) => ({
      ...prev,
      [id]: { ...getCorrectionStateById(id), ...patch },
    }))
  }

  function getCorrectionStateById(id: string): CorrectionState {
    const r = records.find((x) => x.id === id)
    if (!r) return { urgency: 'low', category: 'other', sentiment: 'neutral', saved: false, saving: false }
    return getCorrectionState(r)
  }

  async function saveCorrection(id: string) {
    const state = getCorrectionStateById(id)
    updateCorrection(id, { saving: true })
    const payload: CorrectionPayload = {
      urgency: state.urgency,
      category: state.category,
      sentiment: state.sentiment,
    }
    try {
      await upsertCorrection(id, payload)
      updateCorrection(id, { saved: true, saving: false })
    } catch {
      updateCorrection(id, { saving: false })
    }
  }

  async function removeCorrection(id: string) {
    updateCorrection(id, { saving: true })
    try {
      await deleteCorrection(id)
      setCorrections((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
    } catch {
      updateCorrection(id, { saving: false })
    }
  }

  const grouped = urgencyOrder
    .map((u) => ({ urgency: u, items: records.filter((r) => r.urgency === u) }))
    .filter((g) => g.items.length > 0)

  const selected = records.find((r) => r.id === selectedId) ?? null
  const sheetItem = records.find((r) => r.id === sheetItemId) ?? null

  function renderCorrectionControls(record: TriageRecord, context: 'pane' | 'sheet') {
    if (!showCorrections) return null
    const state = getCorrectionState(record)
    const prefix = context === 'pane' ? 'corr-pane' : 'corr-sheet'
    return (
      <div className={`${prefix}-controls`} data-testid="correction-controls">
        {state.saved && (
          <span className="corr-badge" data-testid="correction-badge">Corrected</span>
        )}
        <label className="corr-label">
          Urgency
          <select
            className="corr-select"
            value={state.urgency}
            onChange={(e) => updateCorrection(record.id, { urgency: e.target.value as Urgency, saved: false })}
          >
            {urgencyOrder.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
        </label>
        <label className="corr-label">
          Category
          <select
            className="corr-select"
            value={state.category}
            onChange={(e) => updateCorrection(record.id, { category: e.target.value as Category, saved: false })}
          >
            {categoryOptions.map((c) => (
              <option key={c} value={c}>{categoryLabel(c)}</option>
            ))}
          </select>
        </label>
        <label className="corr-label">
          Sentiment
          <select
            className="corr-select"
            value={state.sentiment}
            onChange={(e) => updateCorrection(record.id, { sentiment: e.target.value as Sentiment, saved: false })}
          >
            {sentimentOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <p className="corr-reason">
          <strong>Original reasons:</strong>{' '}
          {record.urgency_reason} · {record.category_reason} · {record.sentiment_reason}
        </p>
        <div className="corr-actions">
          <button
            type="button"
            className="corr-save"
            disabled={state.saving}
            onClick={() => void saveCorrection(record.id)}
          >
            {state.saving ? 'Saving…' : 'Save correction'}
          </button>
          {state.saved && (
            <button
              type="button"
              className="corr-reset"
              disabled={state.saving}
              onClick={() => void removeCorrection(record.id)}
            >
              Reset
            </button>
          )}
        </div>
      </div>
    )
  }

  function renderDemoNote() {
    if (settings?.demo_mode !== true) return null
    return <p className="corr-demo-note" role="status">Corrections disabled in demo mode.</p>
  }

  const list = (
    <>
      {grouped.map((g) => {
        const label = g.urgency.charAt(0).toUpperCase() + g.urgency.slice(1)
        return (
          <div key={g.urgency}>
            <p className="fp-group-label">
              <span className={dotClass[g.urgency]} />
              {label} · {g.items.length}
            </p>
            {g.items.map((r) => {
              const Icon = categoryIcon[r.category] ?? MessageCircle
              const selectedClass = r.id === selectedId ? ' is-selected' : ''
              const corrState = getCorrectionState(r)
              return (
                <div
                  key={r.id}
                  className={`fp-row${selectedClass}`}
                  role={isDesktop ? 'button' : undefined}
                  tabIndex={isDesktop ? 0 : undefined}
                  onClick={() => {
                    if (isDesktop) {
                      setSelectedId(r.id)
                    } else if (isMedium || !isDesktop) {
                      setSheetItemId(r.id)
                    }
                  }}
                  onKeyDown={(e) => {
                    if (!isDesktop) return
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setSelectedId(r.id)
                    }
                  }}
                >
                  <span className="fp-row-ic">
                    <Icon size={16} strokeWidth={2} />
                  </span>
                  <span className="fp-row-text">
                    <p className="fp-row-title">{r.subject_or_title ?? r.id}</p>
                    <p className="fp-row-cat">
                      {categoryLabel(r.category)}
                      {corrState.saved && <span className="corr-badge-inline"> Corrected</span>}
                    </p>
                  </span>
                  <span className="fp-row-arr">
                    <ChevronRight size={16} strokeWidth={2} />
                  </span>
                </div>
              )
            })}
          </div>
        )
      })}
    </>
  )

  return (
    <>
      <div className="fp-header">
        <button
          type="button"
          className="page-back"
          onClick={() => navigate('/dashboard')}
          aria-label="Back to dashboard"
        >
          <ArrowLeft size={20} strokeWidth={2} />
        </button>
        <h2 className="fp-title">The full picture</h2>
        <span className="fp-count">{loading ? '…' : `${records.length} items`}</span>
      </div>

      {loading ? (
        <div className="loops">
          <LoopSkeleton />
          <LoopSkeleton />
          <LoopSkeleton />
          <LoopSkeleton />
        </div>
      ) : error ? (
        <div className="fp-intro" role="alert">
          <BulBulAvatar size={26} />
          <p className="fp-intro-txt">{error}</p>
        </div>
      ) : isDesktop ? (
        <div className="items-split">
          <div className="items-list-pane">
            <div className="fp-intro">
              <BulBulAvatar size={26} />
              <p className="fp-intro-txt">Everything, nothing hidden — grouped by what needs you most.</p>
            </div>
            {list}
          </div>
          <div className="items-detail-pane">
            {selected ? (
              <>
                <span className={`items-detail-urgency items-detail-urgency--${selected.urgency}`}>
                  ● {selected.urgency}
                </span>
                <h3 className="items-detail-subject">{selected.subject_or_title ?? selected.id}</h3>
                <p className="items-detail-reasons">
                  <strong>Why urgent:</strong>{' '}
                  {selected.urgency_reason || 'No urgency reason recorded.'}
                </p>
                <p className="items-detail-reasons">
                  <strong>Category:</strong> {categoryLabel(selected.category)}
                  {selected.category_reason ? ` — ${selected.category_reason}` : ''}
                </p>
                {renderCorrectionControls(selected, 'pane')}
                {renderDemoNote()}
                <div className="items-detail-actions">
                  <button
                    type="button"
                    onClick={() =>
                      onAsk?.(
                        `Tell me about ${selected.subject_or_title ?? selected.id}`,
                      )
                    }
                  >
                    Ask about this
                  </button>
                </div>
              </>
            ) : (
              <p className="items-detail-reasons">Select an item to see detail.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="fp-body">
          <div className="fp-intro">
            <BulBulAvatar size={26} />
            <p className="fp-intro-txt">Everything, nothing hidden — grouped by what needs you most.</p>
          </div>
          {list}
        </div>
      )}

      {sheetItem && !isDesktop && (
        <div className="corr-sheet-overlay" onClick={onBackdropClick}>
          <div
            ref={sheetRef}
            className="corr-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby={sheetTitleId}
            tabIndex={-1}
            onClick={(e) => e.stopPropagation()}
          >
            <span className={`items-detail-urgency items-detail-urgency--${sheetItem.urgency}`}>
              ● {sheetItem.urgency}
            </span>
            <h3 className="items-detail-subject" id={sheetTitleId}>
              {sheetItem.subject_or_title ?? sheetItem.id}
            </h3>
            <p className="items-detail-reasons">
              <strong>Why urgent:</strong>{' '}
              {sheetItem.urgency_reason || 'No urgency reason recorded.'}
            </p>
            <p className="items-detail-reasons">
              <strong>Category:</strong> {categoryLabel(sheetItem.category)}
              {sheetItem.category_reason ? ` — ${sheetItem.category_reason}` : ''}
            </p>
            {renderCorrectionControls(sheetItem, 'sheet')}
            {renderDemoNote()}
            <div className="items-detail-actions">
              <button
                type="button"
                onClick={() => {
                  setSheetItemId(null)
                  onAsk?.(`Tell me about ${sheetItem.subject_or_title ?? sheetItem.id}`)
                }}
              >
                Ask about this
              </button>
              <button type="button" onClick={() => setSheetItemId(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
