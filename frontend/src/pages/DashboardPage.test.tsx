import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DashboardPage } from './DashboardPage'
import { getTriage } from '../api/client'

vi.mock('../api/client', () => ({
  getTriage: vi.fn(),
}))

const getTriageMock = vi.mocked(getTriage)

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('clears error on successful triage load (success-path setError null)', async () => {
    getTriageMock.mockResolvedValueOnce([])

    render(
      <MemoryRouter>
        <DashboardPage
          userName="Alex"
          assistantName="Bulbul"
          onAsk={() => undefined}
          onEveningClick={() => undefined}
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/Where would you like to start/i)).toBeInTheDocument()
    })
    expect(screen.queryByRole('alert')).toBeNull()
    expect(getTriageMock).toHaveBeenCalled()
  })

  it('shows error then clears it after successful retry', async () => {
    getTriageMock
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce([])

    render(
      <MemoryRouter>
        <DashboardPage
          userName="Alex"
          assistantName="Bulbul"
          onAsk={() => undefined}
          onEveningClick={() => undefined}
        />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('boom')
    })

    screen.getByRole('button', { name: /try again/i }).click()

    await waitFor(() => {
      expect(screen.queryByRole('alert')).toBeNull()
    })
  })
})
