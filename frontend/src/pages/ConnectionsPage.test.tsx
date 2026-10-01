import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConnectionsPage } from './ConnectionsPage'

vi.mock('../api/client', () => ({
  getCapabilities: vi.fn(async () => []),
  getApiSettings: vi.fn(),
  postSync: vi.fn(),
  disconnectGoogle: vi.fn(),
}))

import { getApiSettings } from '../api/client'

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
})
