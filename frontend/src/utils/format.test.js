import { describe, expect, it } from 'vitest'

import { formatDateTime, formatDistance, formatRelative, formatTime } from './format'

describe('formatTime', () => {
  it('returns empty string for falsy input', () => {
    expect(formatTime('')).toBe('')
    expect(formatTime(null)).toBe('')
  })

  it('renders a time for a valid ISO string', () => {
    const out = formatTime('2026-09-23T14:05:00Z')
    expect(out).toMatch(/\d{1,2}:\d{2}/)
  })
})

describe('formatDateTime', () => {
  it('renders a short date-time for valid ISO', () => {
    const out = formatDateTime('2026-09-23T14:05:00Z')
    expect(out).toContain('Sep')
    expect(out).toMatch(/\d{1,2}:\d{2}/)
  })
})

describe('formatRelative', () => {
  const now = Date.now()

  it('returns just now for recent timestamps', () => {
    expect(formatRelative(new Date(now - 10_000).toISOString())).toBe('just now')
  })

  it('returns minutes for < 1 hour', () => {
    expect(formatRelative(new Date(now - 90_000).toISOString())).toBe('2m ago')
  })

  it('returns hours for < 1 day', () => {
    expect(formatRelative(new Date(now - 3600_000 * 3).toISOString())).toBe('3h ago')
  })

  it('returns days otherwise', () => {
    expect(formatRelative(new Date(now - 86400_000 * 4).toISOString())).toBe('4d ago')
  })
})

describe('formatDistance', () => {
  it('renders meters under 1km', () => {
    expect(formatDistance(820)).toBe('820m away')
    expect(formatDistance(0)).toBe('0m away')
  })

  it('renders km at and above 1km', () => {
    expect(formatDistance(1000)).toBe('1.0km away')
    expect(formatDistance(2200)).toBe('2.2km away')
  })

  it('renders empty for nullish', () => {
    expect(formatDistance(null)).toBe('')
    expect(formatDistance(undefined)).toBe('')
  })
})