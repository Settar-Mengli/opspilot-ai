import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useCallback, useState } from 'react'
import type { AskDraftCard, AskMessage } from './api/types'
import { AskDock } from './components/AskDock'
import { AskPanel } from './components/AskPanel'
import { formatMailHitlError } from './api/client'
import { useMinWidth } from './hooks/useMinWidth'

/**
 * Mirrors App.tsx Ask surface + approve state (isDesktop dock vs panel, askDraft, onApproveDraft).
 * Renders real AskDock and AskPanel — not AskThreadBody alone (D2).
 */
function AppAskApproveShell({
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
  ) => Promise<{ status: string }>
  initialDraft: AskDraftCard
}) {
  const isDesktop = useMinWidth(1280)
  const [askOpen, setAskOpen] = useState(true)
  const [askDraft, setAskDraft] = useState<AskDraftCard | null>(initialDraft)
  const [askInput, setAskInput] = useState('')

  const onApproveDraft = useCallback(() => {
    void (async () => {
      const hold: {
        key: string
        draft: Pick<AskDraftCard, 'draftId' | 'subject' | 'body'> | null
      } = { key: '', draft: null }
      setAskDraft((d) => {
        if (!d || d.sentAt || d.approving) return d
        hold.key = d.idempotencyKey || crypto.randomUUID()
        hold.draft = { draftId: d.draftId, subject: d.subject, body: d.body }
        return {
          ...d,
          approveError: null,
          approving: true,
          idempotencyKey: hold.key,
        }
      })
      if (!hold.draft || !hold.key) return
      try {
        const edited = await editMailDraft(hold.draft.draftId, hold.draft.subject, hold.draft.body)
        await approveMailDraft(edited.id, edited.payload_sha256, hold.key)
        setAskDraft((d) =>
          d
            ? {
                ...d,
                sentAt: Date.now(),
                approveError: null,
                approving: false,
                sendOutcomeUnknown: false,
              }
            : d,
        )
      } catch (e) {
        const message = formatMailHitlError(e)
        const code =
          typeof e === 'object' && e && 'code' in e && typeof (e as { code?: string }).code === 'string'
            ? (e as { code: string }).code
            : undefined
        const unknown = code === 'send_outcome_unknown'
        setAskDraft((d) =>
          d
            ? {
                ...d,
                approveError: message,
                approving: false,
                idempotencyKey: crypto.randomUUID(),
                sendOutcomeUnknown: unknown,
              }
            : d,
        )
      }
    })()
  }, [approveMailDraft, editMailDraft])

  const thread = {
    assistantName: 'Bulbul',
    messages: [] as AskMessage[],
    draft: askDraft,
    onDraftSubjectChange: (value: string) => setAskDraft((d) => (d ? { ...d, subject: value } : d)),
    onDraftBodyChange: (value: string) => setAskDraft((d) => (d ? { ...d, body: value } : d)),
    onApproveDraft,
    input: askInput,
    loading: false,
    error: null as string | null,
    onInputChange: setAskInput,
    onSubmit: () => undefined,
  }

  return (
    <div>
      <button type="button" data-testid="open-ask-panel" onClick={() => setAskOpen(true)}>
        open panel
      </button>
      {isDesktop && <AskDock {...thread} />}
      {!isDesktop && (
        <AskPanel open={askOpen} onClose={() => setAskOpen(false)} {...thread} />
      )}
    </div>
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

describe('approve state remount survival (C5/D2) — real AskDock ↔ AskPanel', () => {
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

  it('test_approve_pending_survives_dock_to_panel_remount_sent', async () => {
    let resolveApprove: (v: { status: string }) => void = () => undefined
    const approvePending = new Promise<{ status: string }>((resolve) => {
      resolveApprove = resolve
    })
    approveMailDraft.mockImplementation(async () => approvePending)

    render(
      <AppAskApproveShell
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
      <AppAskApproveShell
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
      <AppAskApproveShell
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
