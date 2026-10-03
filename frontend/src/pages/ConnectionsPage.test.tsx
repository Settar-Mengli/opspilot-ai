import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConnectionsPage } from './ConnectionsPage'

vi.mock('../api/client', () => ({
  getCapabilities: vi.fn(async () => []),
  getApiSettings: vi.fn(),
  postSync: vi.fn(),
  disconnectGoogle: vi.fn(),
  getJobStatus: vi.fn(),
}))

import { getApiSettings, getJobStatus, postSync } from '../api/client'

function renderPage() {
  return render(
    <MemoryRouter>
      <ConnectionsPage />
    </MemoryRouter>,
  )
}

describe('ConnectionsPage copy', () => {
  beforeEach(() => {
    vi.mocked(getApiSettings).mockReset()
    vi.mocked(postSync).mockReset()
    vi.mocked(getJobStatus).mockReset()
  })

  it('describes send-with-approval when disconnected', async () => {
    vi.mocked(getApiSettings).mockResolvedValue({
      demo_mode: false,
      google_connected: false,
    } as never)
    renderPage()
    expect(
      await screen.findByText(/Gmail read \+ send-with-approval, and Calendar read/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Readonly Gmail/i)).toBeNull()
  })

  it('describes linked account without readonly when connected', async () => {
    vi.mocked(getApiSettings).mockResolvedValue({
      demo_mode: false,
      google_connected: true,
    } as never)
    renderPage()
    expect(
      await screen.findByText(/linked\. Sync pulls fictional demo mail/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/linked \(readonly\)/i)).toBeNull()
  })

  it('shows not_needed status string with triaged and pending', async () => {
    vi.mocked(getApiSettings).mockResolvedValue({
      demo_mode: false,
      google_connected: true,
    } as never)
    vi.mocked(postSync).mockResolvedValue({
      drain: 'not_needed',
      job_id: null,
      account_email: 'ops@example.com',
      gmail_upserted: 2,
      gmail_removed: 1,
      calendar_upserted: 3,
      gmail_total: 10,
      meetings_total: 4,
      triaged: 0,
      pending: 0,
      calendar_truncated: false,
      gmail_truncated: false,
    })
    renderPage()
    const syncBtn = await screen.findByRole('button', { name: /sync now/i })
    fireEvent.click(syncBtn)
    await waitFor(() => {
      expect(
        screen.getByText(
          /Synced \+2 mail \(−1\), \+3 meetings this sync — totals 10 mail, 4 meetings — triaged 0 \(0 pending\)/,
        ),
      ).toBeInTheDocument()
    })
  })

  it('shows busy copy with pending count', async () => {
    vi.mocked(getApiSettings).mockResolvedValue({
      demo_mode: false,
      google_connected: true,
    } as never)
    vi.mocked(postSync).mockResolvedValue({
      drain: 'busy',
      job_id: null,
      account_email: 'ops@example.com',
      gmail_upserted: 1,
      gmail_removed: 0,
      calendar_upserted: 0,
      gmail_total: 5,
      meetings_total: 2,
      triaged: 0,
      pending: 3,
      calendar_truncated: false,
      gmail_truncated: false,
    })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /sync now/i }))
    await waitFor(() => {
      expect(screen.getByText(/triage busy, try again shortly \(3 pending\)/)).toBeInTheDocument()
    })
    expect(screen.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'busy')
    expect(screen.getByRole('button', { name: /sync now/i })).toBeInTheDocument()
  })

  it('shows Syncing… while POST is in flight (progress)', async () => {
    vi.mocked(getApiSettings).mockResolvedValue({
      demo_mode: false,
      google_connected: true,
    } as never)
    let resolveSync: (v: unknown) => void = () => undefined
    vi.mocked(postSync).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSync = resolve
        }),
    )
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /sync now/i }))
    expect(await screen.findByRole('button', { name: /syncing/i })).toBeDisabled()
    resolveSync({
      drain: 'busy',
      job_id: null,
      account_email: 'ops@example.com',
      gmail_upserted: 0,
      gmail_removed: 0,
      calendar_upserted: 0,
      gmail_total: 1,
      meetings_total: 0,
      triaged: 0,
      pending: 1,
      calendar_truncated: false,
      gmail_truncated: false,
    })
    await waitFor(() => {
      expect(screen.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'busy')
    })
  })

  it('shows triaging then done after started poll succeeds', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.mocked(getApiSettings).mockResolvedValue({
      demo_mode: false,
      google_connected: true,
    } as never)
    vi.mocked(postSync).mockResolvedValue({
      drain: 'started',
      job_id: 'job-1',
      account_email: 'ops@example.com',
      gmail_upserted: 2,
      gmail_removed: 0,
      calendar_upserted: 1,
      gmail_total: 10,
      meetings_total: 4,
      triaged: 0,
      pending: 5,
      calendar_truncated: false,
      gmail_truncated: false,
    })
    vi.mocked(getJobStatus).mockResolvedValue({
      id: 'job-1',
      job_kind: 'sync_drain',
      status: 'succeeded',
      triaged: 4,
      pending: 1,
      error_code: null,
      created_at: '2026-10-01T00:00:00Z',
    })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /sync now/i }))
    await waitFor(() => {
      expect(screen.getByText(/triaging 5 pending/)).toBeInTheDocument()
    })
    expect(screen.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'triaging')
    await vi.advanceTimersByTimeAsync(2100)
    await waitFor(() => {
      expect(screen.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'done')
    })
    expect(screen.getByText(/triaged 4 \(1 pending\)/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sync now/i })).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('appends calendar and gmail truncated suffixes', async () => {
    vi.mocked(getApiSettings).mockResolvedValue({
      demo_mode: false,
      google_connected: true,
    } as never)
    vi.mocked(postSync).mockResolvedValue({
      drain: 'not_needed',
      job_id: null,
      account_email: 'ops@example.com',
      gmail_upserted: 0,
      gmail_removed: 0,
      calendar_upserted: 0,
      gmail_total: 1,
      meetings_total: 1,
      triaged: 0,
      pending: 0,
      calendar_truncated: true,
      gmail_truncated: true,
    })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /sync now/i }))
    await waitFor(() => {
      expect(screen.getByText(/calendar sync incomplete; next Sync will full-refresh/)).toBeInTheDocument()
    })
    expect(screen.getByText(/Gmail sync incomplete; next Sync will retry/)).toBeInTheDocument()
  })
})
