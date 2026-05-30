import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiUnavailableBanner } from './ApiUnavailableBanner'

afterEach(() => {
  cleanup()
})

describe('ApiUnavailableBanner', () => {
  it('renders alert content when visible', () => {
    const onRetry = vi.fn()
    render(<ApiUnavailableBanner visible onRetry={onRetry} />)

    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText('API unavailable.')).toBeTruthy()
  })

  it('does not render when hidden', () => {
    const onRetry = vi.fn()
    render(<ApiUnavailableBanner visible={false} onRetry={onRetry} />)

    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('calls onRetry when retry button is clicked', () => {
    const onRetry = vi.fn()
    render(<ApiUnavailableBanner visible onRetry={onRetry} />)

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
