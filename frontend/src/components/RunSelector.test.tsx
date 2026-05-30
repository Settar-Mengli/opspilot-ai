import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { RunSummary } from '../api/types'
import { RunSelector } from './RunSelector'

afterEach(() => {
  cleanup()
})

const RUNS: RunSummary[] = [
  {
    run_id: 'run-20260530-121000-111',
    status: 'success',
    finished_at: '2026-05-30T12:10:00Z',
    item_count: 6,
  },
]

describe('RunSelector', () => {
  it('always includes Latest option', () => {
    const onSelectRun = vi.fn()
    render(
      <RunSelector
        runs={RUNS}
        selectedRunId={null}
        isLoading={false}
        error={null}
        onSelectRun={onSelectRun}
      />,
    )

    const latestOption = screen.getByRole('option', { name: 'Latest' }) as HTMLOptionElement
    expect(latestOption.value).toBe('')
  })

  it('disables selector while loading', () => {
    const onSelectRun = vi.fn()
    render(
      <RunSelector
        runs={RUNS}
        selectedRunId={null}
        isLoading
        error={null}
        onSelectRun={onSelectRun}
      />,
    )

    const selector = screen.getByRole('combobox', { name: 'Select run snapshot' })
    expect(selector.hasAttribute('disabled')).toBe(true)
  })

  it('falls back to latest when user selects Latest option', () => {
    const onSelectRun = vi.fn()
    render(
      <RunSelector
        runs={RUNS}
        selectedRunId={RUNS[0].run_id}
        isLoading={false}
        error={null}
        onSelectRun={onSelectRun}
      />,
    )

    fireEvent.change(screen.getByRole('combobox', { name: 'Select run snapshot' }), {
      target: { value: '' },
    })

    expect(onSelectRun).toHaveBeenCalledWith(null)
  })

  it('keeps missing selected historical run as explicit option', () => {
    const onSelectRun = vi.fn()
    render(
      <RunSelector
        runs={RUNS}
        selectedRunId="run-20260530-999999-999"
        isLoading={false}
        error={null}
        onSelectRun={onSelectRun}
      />,
    )

    expect(screen.getByRole('option', { name: 'run-20260530-999999-999' })).toBeTruthy()
  })
})
