import { describe, expect, it } from 'vitest'
import { _parseSseChunkForTest, ASK_APPROVE_ENABLED } from './askStream'

describe('askStream', () => {
  it('parses SSE data lines', () => {
    const { events, rest } = _parseSseChunkForTest(
      'data: {"type":"token","text":"Hi"}\n\ndata: {"type":"final","answer":"Hi"}\n\npartial',
    )
    expect(events).toHaveLength(2)
    expect(events[0]?.type).toBe('token')
    expect(events[1]?.type).toBe('final')
    expect(rest).toBe('partial')
  })

  it('keeps Approve disabled until C6', () => {
    expect(ASK_APPROVE_ENABLED).toBe(false)
  })
})
