import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTriage } from '../api/client'
import type { TriageRecord, Category, Urgency } from '../api/types'
import { LoopSkeleton } from '../components/skeletons/LoopSkeleton'
import { BulBulAvatar } from '../components/BulBulAvatar'
import { AlertTriangle, FileText, Users, Calendar, MessageCircle, ChevronRight, ArrowLeft } from 'lucide-react'

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

export function AllItemsPage() {
  const navigate = useNavigate()
  const [records, setRecords] = useState<TriageRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getTriage()
      .then(r => { if (!cancelled) setRecords(r) })
      .catch(console.error)
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const grouped = urgencyOrder
    .map(u => ({ urgency: u, items: records.filter(r => r.urgency === u) }))
    .filter(g => g.items.length > 0)

  return (
    <>
      <div className="fp-header">
        <button className="page-back" onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
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
      ) : (
        <div className="fp-body">
          <div className="fp-intro">
            <BulBulAvatar size={26} />
            <p className="fp-intro-txt">Everything, nothing hidden — grouped by what needs you most.</p>
          </div>

          {grouped.map(g => {
            const label = g.urgency.charAt(0).toUpperCase() + g.urgency.slice(1)
            return (
              <div key={g.urgency}>
                <p className="fp-group-label">
                  <span className={dotClass[g.urgency]} />
                  {label} · {g.items.length}
                </p>
                {g.items.map(r => {
                  const Icon = categoryIcon[r.category] ?? MessageCircle
                  return (
                    <div key={r.id} className="fp-row">
                      <span className="fp-row-ic"><Icon size={16} strokeWidth={2} /></span>
                      <span className="fp-row-text">
                        <p className="fp-row-title">{r.subject_or_title ?? r.id}</p>
                        <p className="fp-row-cat">{categoryLabel(r.category)}</p>
                      </span>
                      <span className="fp-row-arr"><ChevronRight size={16} strokeWidth={2} /></span>
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}
