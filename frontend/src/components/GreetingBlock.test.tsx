import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { GreetingBlock } from '../components/GreetingBlock'

afterEach(() => {
  cleanup()
})

describe('GreetingBlock', () => {
  it('shows Sample badge by default with dayShapeLine', () => {
    render(
      <GreetingBlock
        userName="Alex"
        assistantName="Bulbul"
        salutation="Working late"
        dayShapeLine="Today is light."
      />,
    )
    expect(screen.getByLabelText(/Sample data/i)).toBeInTheDocument()
  })

  it('hides Sample badge when showSampleBadge is false', () => {
    render(
      <GreetingBlock
        userName="Alex"
        assistantName="Bulbul"
        salutation="Working late"
        dayShapeLine="Today is light."
        showSampleBadge={false}
      />,
    )
    expect(screen.queryByLabelText(/Sample data/i)).toBeNull()
    expect(screen.getByText(/Today is light/i)).toBeInTheDocument()
  })
})
