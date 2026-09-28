import { describe, expect, it, vi, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useMinWidth } from './useMinWidth'

describe('useMinWidth', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('returns matchMedia().matches on the first render (no false→true flash)', () => {
    const addEventListener = vi.fn()
    const removeEventListener = vi.fn()
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: query === '(min-width: 1280px)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener,
        removeEventListener,
        dispatchEvent: vi.fn(),
      })),
    )

    const { result } = renderHook(() => useMinWidth(1280))

    expect(window.matchMedia).toHaveBeenCalledWith('(min-width: 1280px)')
    expect(result.current).toBe(true)
  })

  it('returns false on first render when viewport is below the breakpoint', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    )

    const { result } = renderHook(() => useMinWidth(1280))
    expect(result.current).toBe(false)
  })
})
