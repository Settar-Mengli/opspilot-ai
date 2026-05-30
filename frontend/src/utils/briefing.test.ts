import { describe, expect, it } from 'vitest'

import { parseBriefing } from './briefing'

describe('parseBriefing', () => {
  it('extracts required sections and metrics', () => {
    const raw = [
      'OpsPilot AI Daily Executive Briefing - 2026-05-30',
      '',
      'Total Work Items: 6',
      'Urgency Mix: critical=1, high=2, medium=1, low=2',
      'Sentiment Mix: negative=2, neutral=3, positive=1',
      '',
      'Top Priorities:',
      '- WI-001: Production outage',
      '- WI-004: Escalated ticket',
      '',
      'Due-Soon Action Items:',
      '- WI-004: Escalated ticket (owner=unassigned, deadline=EOD)',
    ].join('\n')

    const parsed = parseBriefing(raw)

    expect(parsed.title).toContain('Daily Executive Briefing')
    expect(parsed.metrics.totalWorkItems).toBe('6')
    expect(parsed.metrics.urgencyMix).toContain('critical=1')
    expect(parsed.metrics.sentimentMix).toContain('negative=2')
    expect(parsed.topPriorities).toEqual(['WI-001: Production outage', 'WI-004: Escalated ticket'])
    expect(parsed.dueSoon).toEqual(['WI-004: Escalated ticket (owner=unassigned, deadline=EOD)'])
  })

  it('gracefully handles missing sections', () => {
    const raw = ['OpsPilot Notes', '', 'Total Work Items: 2'].join('\n')

    const parsed = parseBriefing(raw)

    expect(parsed.title).toBe('OpsPilot Daily Briefing')
    expect(parsed.metrics.totalWorkItems).toBe('2')
    expect(parsed.metrics.urgencyMix).toBe('n/a')
    expect(parsed.metrics.sentimentMix).toBe('n/a')
    expect(parsed.topPriorities).toEqual([])
    expect(parsed.dueSoon).toEqual([])
  })
})
