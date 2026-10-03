import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SettingsPage } from '../pages/SettingsPage'

const mockGetApiSettings = vi.fn()

vi.mock('../api/client', () => ({
  getApiSettings: (...args: unknown[]) => mockGetApiSettings(...args),
}))

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders read-only settings without API-key input or openai option', async () => {
    mockGetApiSettings.mockResolvedValue({
      provider: 'anthropic',
      model: 'claude-haiku-4-5-20251001',
      api_key_set: false,
    })

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('AI settings (read-only)')).toBeInTheDocument()
    })

    expect(screen.queryByRole('textbox')).toBeNull()
    expect(screen.queryByRole('combobox')).toBeNull()
    expect(screen.queryByDisplayValue(/openai/i)).toBeNull()
    expect(screen.queryByText(/openai/i)).toBeNull()
    expect(screen.queryByLabelText(/api key/i)).toBeNull()
    expect(screen.getByText('Active provider')).toBeInTheDocument()
    expect(screen.getByText('API key set')).toBeInTheDocument()
    expect(screen.queryByText('API key preview')).toBeNull()
  })

  it('hides job blocks when last_morning and last_sync are null', async () => {
    mockGetApiSettings.mockResolvedValue({
      provider: 'anthropic',
      model: 'claude-haiku-4-5-20251001',
      api_key_set: true,
      last_morning: null,
      last_sync: null,
    })

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Active provider')).toBeInTheDocument()
    })

    expect(screen.queryByTestId('job-block-last-morning-run')).toBeNull()
    expect(screen.queryByTestId('job-block-last-sync')).toBeNull()
  })

  it('shows job blocks when last_morning and last_sync are present', async () => {
    mockGetApiSettings.mockResolvedValue({
      provider: 'gemini',
      model: 'gemini-3.5-flash-lite',
      api_key_set: true,
      last_morning: {
        id: 'j-1',
        status: 'succeeded',
        triaged: 5,
        pending: 0,
        error_code: null,
        finished_at: '2026-10-01T08:00:00Z',
      },
      last_sync: {
        id: 'j-2',
        status: 'failed',
        triaged: 0,
        pending: 3,
        error_code: 'timeout',
        finished_at: '2026-10-01T09:00:00Z',
      },
    })

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('job-block-last-morning-run')).toBeInTheDocument()
    })
    expect(screen.getByTestId('job-block-last-sync')).toBeInTheDocument()

    expect(screen.getByText('Last morning run')).toBeInTheDocument()
    expect(screen.getByText('Last sync')).toBeInTheDocument()
    expect(screen.getByText('succeeded')).toBeInTheDocument()
    expect(screen.getByText('failed')).toBeInTheDocument()
    expect(screen.getByText('timeout')).toBeInTheDocument()
    expect(screen.getAllByText('Status').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Triaged').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Pending').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Finished').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Rules fallback').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Re-auth').length).toBeGreaterThanOrEqual(1)
  })

  it('renders rules_fallback_count and reauth_needed from job summary', async () => {
    mockGetApiSettings.mockResolvedValue({
      provider: 'gemini',
      model: 'gemini-3.5-flash-lite',
      api_key_set: true,
      last_morning: {
        id: 'j-1',
        status: 'partial',
        triaged: 2,
        pending: 1,
        rules_fallback_count: 3,
        reauth_needed: true,
        error_code: null,
        finished_at: '2026-10-01T08:00:00Z',
      },
      last_sync: null,
    })

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('job-block-last-morning-run')).toBeInTheDocument()
    })
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('needed')).toBeInTheDocument()
  })

  it('hides job blocks when fields are undefined', async () => {
    mockGetApiSettings.mockResolvedValue({
      provider: 'anthropic',
      model: 'claude-haiku-4-5-20251001',
      api_key_set: true,
    })

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Active provider')).toBeInTheDocument()
    })

    expect(screen.queryByText('Last morning run')).toBeNull()
    expect(screen.queryByText('Last sync')).toBeNull()
  })
})
