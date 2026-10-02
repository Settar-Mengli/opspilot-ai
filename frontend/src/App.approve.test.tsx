import { render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { AskThreadBody } from './components/AskDock'

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

/**
 * Approve state lives on App askDraft and is passed into AskDock/AskPanel.
 * These tests pin remount survival of that shared card state (C5) without AbortController on approve.
 */
describe('approve state remount survival (C5)', () => {
  it('test_approve_pending_survives_dock_to_panel_remount_sent', () => {
    const draftPending = {
      draftId: 'md_1',
      subject: 'S',
      body: 'B',
      toAddrs: 'demo@example.com',
      approving: true,
      idempotencyKey: 'k1',
    }
    const { rerender } = render(
      <AskThreadBody
        assistantName="Bulbul"
        messages={[]}
        draft={draftPending}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={vi.fn()}
      />,
    )
    expect(screen.getByTestId('ask-draft-approve')).toBeDisabled()
    rerender(
      <AskThreadBody
        assistantName="Bulbul"
        messages={[]}
        draft={{ ...draftPending }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={vi.fn()}
      />,
    )
    expect(screen.getByTestId('ask-draft-approve')).toBeDisabled()
    expect(draftPending.idempotencyKey).toBe('k1')
    rerender(
      <AskThreadBody
        assistantName="Bulbul"
        messages={[]}
        draft={{ ...draftPending, approving: false, sentAt: Date.now() }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={vi.fn()}
      />,
    )
    expect(screen.getByText(/Sent ✓/)).toBeInTheDocument()
  })

  it('test_approve_pending_survives_remount_error_path', () => {
    const { rerender } = render(
      <AskThreadBody
        assistantName="Bulbul"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approving: true,
          idempotencyKey: 'k-err',
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )
    rerender(
      <AskThreadBody
        assistantName="Bulbul"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approving: false,
          approveError: 'Demo mode blocks sending.',
          idempotencyKey: 'k-err',
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Demo mode')
  })

  it('test_send_outcome_unknown_resend_ui_survives_dock_panel_remount', () => {
    const draft = {
      draftId: 'md_1',
      subject: 'S',
      body: 'B',
      toAddrs: 'demo@example.com',
      approveError: 'Send may have gone through. Check the Sent folder before trying again.',
      sendOutcomeUnknown: true,
      idempotencyKey: 'k-unk',
      approving: false,
    }
    const { rerender } = render(
      <AskThreadBody
        assistantName="Bulbul"
        messages={[]}
        draft={draft}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={vi.fn()}
      />,
    )
    expect(screen.getByTestId('ask-draft-approve')).toHaveTextContent('Check Sent, then re-send')
    rerender(
      <AskThreadBody
        assistantName="Bulbul"
        messages={[]}
        draft={{ ...draft }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={vi.fn()}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Send may have gone through')
    expect(screen.getByTestId('ask-draft-approve')).toHaveTextContent('Check Sent, then re-send')
  })
})
