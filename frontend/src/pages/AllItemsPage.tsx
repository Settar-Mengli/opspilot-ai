import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTriage } from '../api/client'
import type { TriageRecord, Category, Urgency } from '../api/types'
import { LoopSkeleton } from '../components/skeletons/LoopSkeleton'
import { BulBulAvatar } from '../components/BulBulAvatar'
import { AlertTriangle, FileText, Users, Calendar, MessageCircle, ChevronRight, ArrowLeft } from 'lucide-react'
import { useMinWidth } from '../hooks/useMinWidth'

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

const dotClass: Record<Urgency, string> = {
  critical: 'fp-dot fp-dot--crit',
  high: 'fp-dot fp-dot--high',
  medium: 'fp-dot fp-dot--med',
  low: 'fp-dot fp-dot--low',
}

interface Props {
  onAsk?: (question: string) => void
}

export function AllItemsPage({ onAsk }: Props) {
  const navigate = useNavigate()
  const isDesktop = useMinWidth(1280)
  const [records, setRecords] = useState<TriageRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getTriage()
      .then((r) => {
        if (cancelled) return
        setRecords(r)
        const first = urgencyOrder
          .flatMap((u) => r.filter((x) => x.urgency === u))
          .at(0)
        setSelectedId(first?.id ?? null)
      })
      .catch(console.error)
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const grouped = urgencyOrder
    .map((u) => ({ urgency: u, items: records.filter((r) => r.urgency === u) }))
    .filter((g) => g.items.length > 0)

  const selected = records.find((r) => r.id === selectedId) ?? null

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
              return (
                <div
                  key={r.id}
                  className={`fp-row${selectedClass}`}
                  role={isDesktop ? 'button' : undefined}
                  tabIndex={isDesktop ? 0 : undefined}
                  onClick={() => {
                    if (isDesktop) setSelectedId(r.id)
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
                    <p className="fp-row-cat">{categoryLabel(r.category)}</p>
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
    </>
  )
}
