import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useLayoutEffect, useRef, useState } from 'react'
import type { AskDraftCard, AskMessage } from './api/types'
import { AskDock } from './components/AskDock'
import { AskPanel } from './components/AskPanel'
import { runApproveAskDraft } from './ask/runApproveAskDraft'
import { useMinWidth } from './hooks/useMinWidth'

/**
 * Thin UI harness: same runApproveAskDraft path as App.tsx (no duplicated hold logic).
 * Seeds an initial draft so remount / Approve UI can be exercised without SSE.
 */
function AskApproveUiHarness({
  editMailDraft,
  approveMailDraft,
  initialDraft,
}: {
  editMailDraft: (id: string, subject: string, body: string) => Promise<{
    id: string
    payload_sha256: string
  }>
  approveMailDraft: (
    id: string,
    hash: string,
    key?: string,
  ) => Promise<{ status: string; send_failed?: boolean; error_code?: string | null }>
  initialDraft: AskDraftCard
}) {
  const isDesktop = useMinWidth(1280)
  const [askOpen, setAskOpen] = useState(true)
  const [askDraft, setAskDraft] = useState<AskDraftCard | null>(initialDraft)
  const askDraftRef = useRef<AskDraftCard | null>(initialDraft)
  useLayoutEffect(() => {
    askDraftRef.current = askDraft
  }, [askDraft])
  const [askInput, setAskInput] = useState('')

  const thread = {
    assistantName: 'Bulbul',
    messages: [] as AskMessage[],
    draft: askDraft,
    onDraftSubjectChange: (value: string) => setAskDraft((d) => (d ? { ...d, subject: value } : d)),
    onDraftBodyChange: (value: string) => setAskDraft((d) => (d ? { ...d, body: value } : d)),
    onApproveDraft: () => {
      void runApproveAskDraft({
        getDraft: () => askDraftRef.current,
        setDraft: setAskDraft,
        editMailDraft,
        approveMailDraft,
      })
    },
    demoMode: false,
    input: askInput,
    loading: false,
    error: null as string | null,
    onInputChange: setAskInput,
    onSubmit: () => undefined,
  }

  return (
    <>
      {isDesktop ? (
        <AskDock {...thread} />
      ) : (
        <AskPanel open={askOpen} onClose={() => setAskOpen(false)} {...thread} />
      )}
    </>
  )
}

type MqListener = EventListenerOrEventListenerObject

function installMatchMediaController() {
  let desktop = true
  const listeners = new Set<MqListener>()
  const mq = {
    get matches() {
      return desktop
    },
    media: '(min-width: 1280px)',
    onchange: null as ((this: MediaQueryList, ev: MediaQueryListEvent) => void) | null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn((_type: string, cb: MqListener) => {
      listeners.add(cb)
    }),
    removeEventListener: vi.fn((_type: string, cb: MqListener) => {
      listeners.delete(cb)
    }),
    dispatchEvent: vi.fn(),
  }
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => {
      if (query.includes('1280')) return mq
      return {
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }
    }),
  )
  return {
    setDesktop(next: boolean) {
      desktop = next
      for (const cb of listeners) {
        if (typeof cb === 'function') cb({ matches: desktop } as MediaQueryListEvent)
        else cb.handleEvent({ matches: desktop } as MediaQueryListEvent)
      }
    },
  }
}

const baseDraft = (): AskDraftCard => ({
  draftId: 'md_remount',
  subject: 'Re: FIXTURE_SUBJECT',
  body: 'FIXTURE_BODY',
  toAddrs: 'demo@example.com',
  sentAt: null,
  approveError: null,
  idempotencyKey: 'key-pending-1',
  approving: false,
  sendOutcomeUnknown: false,
})

describe('approve via runApproveAskDraft (same module as App.tsx)', () => {
  let mq: ReturnType<typeof installMatchMediaController>
  const editMailDraft = vi.fn()
  const approveMailDraft = vi.fn()

  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
    mq = installMatchMediaController()
    editMailDraft.mockReset()
    approveMailDraft.mockReset()
    editMailDraft.mockResolvedValue({
      id: 'md_remount',
      payload_sha256: 'a'.repeat(64),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('Approve calls editMailDraft; failure clears approving and shows error + Reopen', async () => {
    approveMailDraft.mockImplementation(async () => {
      throw Object.assign(new Error('google_reauth_required'), {
        status: 400,
        code: 'google_reauth_required',
      })
    })

    render(
      <AskApproveUiHarness
        editMailDraft={editMailDraft}
        approveMailDraft={approveMailDraft}
        initialDraft={baseDraft()}
      />,
    )
    const dock = screen.getByRole('complementary', { name: 'Ask' })
    fireEvent.click(within(dock).getByTestId('ask-draft-approve'))

    await waitFor(() => {
      expect(editMailDraft).toHaveBeenCalledTimes(1)
      expect(editMailDraft).toHaveBeenCalledWith('md_remount', 'Re: FIXTURE_SUBJECT', 'FIXTURE_BODY')
      expect(within(dock).getByRole('alert')).toBeInTheDocument()
      expect(within(dock).getByTestId('ask-draft-reopen')).toBeInTheDocument()
    })
    expect(within(dock).getByTestId('ask-draft-approve')).not.toBeDisabled()
  })

  it('test_approve_pending_survives_dock_to_panel_remount_sent', async () => {
    let resolveApprove: (v: { status: string }) => void = () => undefined
    const approvePending = new Promise<{ status: string }>((resolve) => {
      resolveApprove = resolve
    })
    approveMailDraft.mockImplementation(async () => approvePending)

    render(
      <AskApproveUiHarness
        editMailDraft={editMailDraft}
        approveMailDraft={approveMailDraft}
        initialDraft={baseDraft()}
      />,
    )

    expect(screen.getByRole('complementary', { name: 'Ask' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    const dockApprove = within(screen.getByRole('complementary', { name: 'Ask' })).getByTestId(
      'ask-draft-approve',
    )
    fireEvent.click(dockApprove)
    await waitFor(() => {
      expect(editMailDraft).toHaveBeenCalledTimes(1)
      expect(approveMailDraft).toHaveBeenCalledTimes(1)
      expect(dockApprove).toBeDisabled()
    })
    const keyWhilePending = (approveMailDraft.mock.calls[0] as unknown[])[2]
    expect(keyWhilePending).toBe('key-pending-1')

    act(() => {
      mq.setDesktop(false)
    })

    await waitFor(() => {
      expect(screen.queryByRole('complementary', { name: 'Ask' })).not.toBeInTheDocument()
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
    const panel = screen.getByRole('dialog')
    expect(within(panel).getByTestId('ask-draft-approve')).toBeDisabled()
    expect(approveMailDraft).toHaveBeenCalledTimes(1)
    expect((approveMailDraft.mock.calls[0] as unknown[])[2]).toBe(keyWhilePending)

    await act(async () => {
      resolveApprove({ status: 'sent' })
    })
    await waitFor(() => {
      expect(within(panel).getByText(/Sent ✓/)).toBeInTheDocument()
    })
  })

  it('test_approve_pending_survives_remount_error_path', async () => {
    let rejectApprove: (e: Error) => void = () => undefined
    const approvePending = new Promise<{ status: string }>((_resolve, reject) => {
      rejectApprove = reject
    })
    approveMailDraft.mockImplementation(async () => approvePending)

    render(
      <AskApproveUiHarness
        editMailDraft={editMailDraft}
        approveMailDraft={approveMailDraft}
        initialDraft={baseDraft()}
      />,
    )
    fireEvent.click(
      within(screen.getByRole('complementary', { name: 'Ask' })).getByTestId('ask-draft-approve'),
    )
    await waitFor(() => expect(approveMailDraft).toHaveBeenCalledTimes(1))
    const keyWhilePending = (approveMailDraft.mock.calls[0] as unknown[])[2]

    act(() => {
      mq.setDesktop(false)
    })
    await waitFor(() => {
      expect(screen.queryByRole('complementary', { name: 'Ask' })).not.toBeInTheDocument()
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
    expect((approveMailDraft.mock.calls[0] as unknown[])[2]).toBe(keyWhilePending)

    await act(async () => {
      rejectApprove(Object.assign(new Error('fail'), { status: 400, code: 'gmail_send_failed' }))
    })
    await waitFor(() => {
      expect(within(screen.getByRole('dialog')).getByRole('alert')).toBeInTheDocument()
    })
    const panelApprove = within(screen.getByRole('dialog')).getByTestId('ask-draft-approve')
    expect(panelApprove).not.toBeDisabled()
    expect(panelApprove).toHaveTextContent('Approve & send')
  })

  it('test_send_outcome_unknown_resend_ui_survives_dock_panel_remount', async () => {
    let rejectApprove: (e: Error) => void = () => undefined
    const approvePending = new Promise<{ status: string }>((_resolve, reject) => {
      rejectApprove = reject
    })
    approveMailDraft.mockImplementation(async () => approvePending)

    render(
      <AskApproveUiHarness
        editMailDraft={editMailDraft}
        approveMailDraft={approveMailDraft}
        initialDraft={baseDraft()}
      />,
    )
    fireEvent.click(
      within(screen.getByRole('complementary', { name: 'Ask' })).getByTestId('ask-draft-approve'),
    )
    await waitFor(() => expect(approveMailDraft).toHaveBeenCalledTimes(1))
    const keyWhilePending = (approveMailDraft.mock.calls[0] as unknown[])[2]

    act(() => {
      mq.setDesktop(false)
    })
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument())
    expect((approveMailDraft.mock.calls[0] as unknown[])[2]).toBe(keyWhilePending)

    await act(async () => {
      rejectApprove(
        Object.assign(new Error('unknown'), {
          status: 502,
          code: 'send_outcome_unknown',
        }),
      )
    })
    const panel = screen.getByRole('dialog')
    await waitFor(() => {
      expect(within(panel).getByRole('alert')).toHaveTextContent('Check the Sent folder')
      expect(within(panel).getByTestId('ask-draft-approve')).toHaveTextContent(
        'Check Sent, then re-send',
      )
    })
    expect(approveMailDraft).toHaveBeenCalledTimes(1)
  })
})
