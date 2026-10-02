import { render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { AskThreadBody } from './AskDock'

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

describe('AskThreadBody a11y', () => {
  it('marks error with role=alert and draft meta aria-live=polite', () => {
    render(
      <AskThreadBody
        assistantName="OpsPilot"
        messages={[]}
        draft={{
          draftId: 'md_1',
          subject: 'S',
          body: 'B',
          toAddrs: 'demo@example.com',
        }}
        onDraftSubjectChange={vi.fn()}
        onDraftBodyChange={vi.fn()}
        input=""
        loading={false}
        error="Something failed"
        onInputChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Something failed')
    expect(screen.getByText(/To: demo@example.com/)).toHaveAttribute('aria-live', 'polite')
  })
})
