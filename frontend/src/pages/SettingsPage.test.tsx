import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SettingsPage } from '../pages/SettingsPage'

vi.mock('../api/client', () => ({
  getApiSettings: vi.fn(async () => ({
    provider: 'anthropic',
    model: 'claude-haiku-4-5-20251001',
    api_key_set: false,
  })),
}))

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders read-only settings without API-key input or openai option', async () => {
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
})
