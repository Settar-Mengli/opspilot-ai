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

  it('parses minimized tool_end without draft body', () => {
    const { events } = _parseSseChunkForTest(
      'data: {"type":"tool_end","tool":"draft_reply","ok":true}\n\n' +
        'data: {"type":"draft","draft_id":"md_1","subject":"S","body":"SECRET","to_addrs":"a@b.c"}\n\n',
    )
    expect(events[0]).toEqual({ type: 'tool_end', tool: 'draft_reply', ok: true })
    expect(events[1]?.body).toBe('SECRET')
  })

  it('enables Approve after HITL lands', () => {
    expect(ASK_APPROVE_ENABLED).toBe(true)
  })
})
