export function formatPercent(value: string | number, digits = 2): string {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value)
  return `${(numeric * 100).toFixed(digits)}%`
}

export function formatMoney(value: string | number): string {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value)
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric)
}

export function formatQty(value: string | number): string {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value)
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  }).format(numeric)
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return '暂无时间'
  }
  const date = new Date(value)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}
