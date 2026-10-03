import { render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { AskThreadBody } from './AskDock'

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

describe('AskThreadBody draft card', () => {
  it('shows Sent and disables approve after send', () => {
    const sentAt = Date.UTC(2026, 9, 2, 17, 30)
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          sentAt,
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getByText(/Sent ✓/)).toBeInTheDocument()
    expect(screen.getByTestId('ask-draft-approve')).toBeDisabled()
    expect(screen.getByLabelText('Draft subject')).toBeDisabled()
  })

  it('surfaces approve errors on the card', () => {
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approveError: 'This draft was already sent or is no longer approvable.',
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('already sent')
  })

  it('disables approve while approving', () => {
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approving: true,
          idempotencyKey: 'k1',
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={vi.fn()}
      />,
    )
    expect(screen.getByTestId('ask-draft-approve')).toBeDisabled()
  })

  it('double-click while approving does not fire onApproveDraft twice', () => {
    const onApprove = vi.fn()
    const { rerender } = render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approving: false,
          idempotencyKey: 'k1',
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={onApprove}
      />,
    )
    screen.getByTestId('ask-draft-approve').click()
    rerender(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approving: true,
          idempotencyKey: 'k1',
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={onApprove}
      />,
    )
    screen.getByTestId('ask-draft-approve').click()
    expect(onApprove).toHaveBeenCalledTimes(1)
  })

  it('AskDock_unknown_shows_alert_and_resend_label', () => {
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approveError: 'Send may have gone through. Check the Sent folder before trying again.',
          sendOutcomeUnknown: true,
          idempotencyKey: 'k2',
        }}
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
    expect(screen.getByTestId('ask-draft-approve')).toHaveAttribute(
      'title',
      'Check Sent folder, then re-send',
    )
  })

  it('AskDock_gmail_unavailable_shows_alert_and_normal_approve_label', () => {
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approveError: 'Gmail was unavailable. Nothing was sent — try again.',
          sendOutcomeUnknown: false,
          idempotencyKey: 'k3',
        }}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onApproveDraft={vi.fn()}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Gmail was unavailable. Nothing was sent')
    expect(screen.getByTestId('ask-draft-approve')).toHaveTextContent('Approve & send')
    expect(screen.getByTestId('ask-draft-approve')).not.toHaveTextContent('Check Sent, then re-send')
  })

  it('shows Reopen when reopenable and not demo mode', () => {
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approveError: 'Send failed (google_reauth_required)',
          reopenable: true,
        }}
        demoMode={false}
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onReopenDraft={vi.fn()}
      />,
    )
    expect(screen.getByTestId('ask-draft-reopen')).toBeInTheDocument()
  })

  it('hides Reopen when demoMode is true', () => {
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
          approveError: 'Send failed (google_reauth_required)',
          reopenable: true,
        }}
        demoMode
        input=""
        loading={false}
        error={null}
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
        onReopenDraft={vi.fn()}
      />,
    )
    expect(screen.queryByTestId('ask-draft-reopen')).toBeNull()
  })
})
