import { describe, expect, it } from 'vitest'

import { formatDateTime, formatMoney, formatPercent, formatQty } from './formatters'

describe('formatters', () => {
  it('格式化百分比', () => {
    expect(formatPercent('0.8523')).toBe('85.23%')
  })

  it('格式化金额', () => {
    expect(formatMoney('650025')).toBe('650,025.00')
  })

  it('格式化数量', () => {
    expect(formatQty('120.5')).toBe('120.500')
  })

  it('格式化时间', () => {
    expect(formatDateTime('2026-03-06T08:00:00+08:00')).toContain('2026/')
  })
})
