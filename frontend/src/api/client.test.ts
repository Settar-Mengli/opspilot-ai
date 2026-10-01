import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_PREFIX, approveMailDraft, editMailDraft } from './client'

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses the /api/v1 prefix', () => {
    expect(API_PREFIX).toBe('/api/v1')
  })

  it('editMailDraft posts subject and body only', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 'md_1',
        subject: 'Re: Hi',
        body: 'Thanks',
        to_addrs: 'demo@example.com',
        payload_sha256: 'a'.repeat(64),
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await editMailDraft('md_1', 'Re: Hi', 'Thanks')
    expect(result.id).toBe('md_1')
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/mail/drafts/md_1/edit')
    expect(JSON.parse(String(init.body))).toEqual({ subject: 'Re: Hi', body: 'Thanks' })
  })

  it('approveMailDraft posts payload hash', async () => {
    const hash = 'b'.repeat(64)
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'sent' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await approveMailDraft('md_1', hash)
    expect(result.status).toBe('sent')
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/mail/drafts/md_1/approve')
    expect(JSON.parse(String(init.body))).toEqual({
      payload_sha256: hash,
      idempotency_key: undefined,
    })
  })
})
