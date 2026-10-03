import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AllItemsPage } from './AllItemsPage'

vi.mock('../api/client', () => ({
  getApiSettings: vi.fn(),
  getTriage: vi.fn(),
  upsertCorrection: vi.fn(),
  deleteCorrection: vi.fn(),
}))

vi.mock('../hooks/useMinWidth', () => ({
  useMinWidth: (min: number) => min <= 1280,
}))

import { getApiSettings, getTriage, upsertCorrection } from '../api/client'

const baseRow = {
  id: 'WI-013',
  subject_or_title: 'Checkout errors on payment confirm',
  urgency: 'high' as const,
  urgency_reason: 'Customer-facing checkout failures.',
  category: 'incident' as const,
  category_reason: 'Production error reports.',
  sentiment: 'negative' as const,
  sentiment_reason: 'Frustrated customers.',
  corrected: false,
}

describe('AllItemsPage corrections refetch', () => {
  beforeEach(() => {
    vi.mocked(getApiSettings).mockReset()
    vi.mocked(getTriage).mockReset()
    vi.mocked(upsertCorrection).mockReset()
    vi.mocked(getApiSettings).mockResolvedValue({
      provider: 'gemini',
      model: 'gemini-3.5-flash-lite',
      api_key_set: true,
      demo_mode: false,
      google_connected: true,
    })
    vi.mocked(getTriage).mockResolvedValue([baseRow])
    vi.mocked(upsertCorrection).mockResolvedValue({ status: 'saved' })
  })

  it('refetches triage after save and updates grouping, header, and Corrected badge', async () => {
    render(
      <MemoryRouter>
        <AllItemsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/high\s*·\s*1/i)).toBeInTheDocument()
    })

    fireEvent.click(screen.getAllByText('Checkout errors on payment confirm')[0]!)

    const controls = await screen.findByTestId('correction-controls')
    const urgencySelect = within(controls).getByDisplayValue('high')
    fireEvent.change(urgencySelect, { target: { value: 'medium' } })

    vi.mocked(getTriage).mockResolvedValue([
      {
        ...baseRow,
        urgency: 'medium',
        corrected: true,
      },
    ])

    fireEvent.click(within(controls).getByRole('button', { name: /save correction/i }))

    await waitFor(() => {
      expect(upsertCorrection).toHaveBeenCalled()
      expect(getTriage.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    await waitFor(() => {
      expect(screen.getByText(/medium\s*·\s*1/i)).toBeInTheDocument()
      expect(screen.queryByText(/high\s*·\s*1/i)).toBeNull()
    })
    expect(screen.getByTestId('correction-badge')).toBeInTheDocument()
    expect(screen.getByText(/●\s*medium/i)).toBeInTheDocument()
  })
})
