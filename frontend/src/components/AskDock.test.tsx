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
})
