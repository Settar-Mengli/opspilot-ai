import { describe, expect, it } from 'vitest'
import { API_PREFIX } from './client'

describe('api client', () => {
  it('uses the /api/v1 prefix', () => {
    expect(API_PREFIX).toBe('/api/v1')
  })
})
