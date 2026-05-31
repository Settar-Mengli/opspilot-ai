import { useEffect, useState } from 'react'
import { getTriage } from '../api/client'
import type { TriageRecord } from '../api/types'
import { OpenLoop } from '../components/OpenLoop'
import { LoopSkeleton } from '../components/skeletons/LoopSkeleton'

export function AllItemsPage() {
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

  return (
    <>
      <div className="section-label">
        All items <span className="section-count">
          {loading ? 'LOADING' : `${records.length} TOTAL`}
        </span>
      </div>
      <div className="loops">
        {loading ? (
          <>
            <LoopSkeleton />
            <LoopSkeleton />
            <LoopSkeleton />
            <LoopSkeleton />
          </>
        ) : (
          records.map((r, i) => <OpenLoop key={r.id} number={i + 1} record={r} />)
        )}
      </div>
    </>
  )
}
