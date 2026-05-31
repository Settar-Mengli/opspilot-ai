import { useEffect, useState } from 'react'
import { getTriage } from '../api/client'
import type { TriageRecord } from '../api/types'
import { OpenLoop } from '../components/OpenLoop'

export function AllItemsPage() {
  const [records, setRecords] = useState<TriageRecord[]>([])

  useEffect(() => {
    getTriage().then(setRecords).catch(console.error)
  }, [])

  return (
    <>
      <div className="section-label">All items <span className="section-count">{records.length} TOTAL</span></div>
      <div className="loops">
        {records.map((r, i) => <OpenLoop key={r.id} number={i + 1} record={r} />)}
      </div>
    </>
  )
}
