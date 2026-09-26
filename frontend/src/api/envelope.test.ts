import { describe, expect, it } from 'vitest'
import { isErrorEnvelope, messageFromErrorEnvelope } from './client'

describe('error envelope parsing', () => {
  it('parses {error:{code,message,details}}', () => {
    const payload = {
      error: {
        code: 'validation_error',
        message: 'Request validation failed.',
        details: [{ loc: ['body', 'date'], msg: 'Field required' }],
      },
    }
    expect(isErrorEnvelope(payload)).toBe(true)
    expect(messageFromErrorEnvelope(payload)).toBe('Request validation failed.')
  })

  it('returns null for non-envelope payloads', () => {
    expect(isErrorEnvelope({ detail: 'nope' })).toBe(false)
    expect(messageFromErrorEnvelope('plain')).toBeNull()
  })
})
