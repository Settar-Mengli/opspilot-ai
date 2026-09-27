import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PrioritiesPanel } from '../components/PrioritiesPanel'
import type { TriageRecord } from '../api/types'

function record(partial: Partial<TriageRecord> & Pick<TriageRecord, 'id' | 'urgency'>): TriageRecord {
  return {
    urgency_reason: 'reason',
    category: 'incident',
    category_reason: 'cat',
    sentiment: 'neutral',
    sentiment_reason: 's',
    ...partial,
  }
}

describe('subject_or_title display', () => {
  it('renders subject_or_title when present', () => {
    render(
      <PrioritiesPanel
        open
        onClose={() => undefined}
        records={[
          record({
            id: 'WI-013',
            subject_or_title: 'Checkout errors on payment confirm',
            urgency: 'high',
          }),
        ]}
      />,
    )
    expect(screen.getByText('Checkout errors on payment confirm')).toBeInTheDocument()
    expect(screen.queryByText('WI-013')).toBeNull()
  })

  it('falls back to id when subject_or_title is missing', () => {
    render(
      <PrioritiesPanel
        open
        onClose={() => undefined}
        records={[record({ id: 'WI-013', urgency: 'critical' })]}
      />,
    )
    expect(screen.getByText('WI-013')).toBeInTheDocument()
  })
})
