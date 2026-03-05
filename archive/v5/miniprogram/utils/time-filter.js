const FIXED_TIME_FILTER_OPTIONS = [
  { value: 'TODAY', label: '今天' },
  { value: 'THIS_WEEK', label: '本周' },
  { value: 'THIS_MONTH', label: '本月' },
  { value: 'THIS_YEAR', label: '今年' },
  { value: 'ALL', label: '全部' },
];

const DEFAULT_TIME_FILTER = 'THIS_WEEK';

function padText(value) {
  return `${value}`.padStart(2, '0');
}

function formatDateText(value) {
  return `${value.getFullYear()}-${padText(value.getMonth() + 1)}-${padText(value.getDate())}`;
}

function toLocalDate(value) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function addDays(value, offset) {
  const next = new Date(value);
  next.setDate(next.getDate() + offset);
  return next;
}

function resolveFixedTimeFilterRange(filterValue) {
  const currentValue = FIXED_TIME_FILTER_OPTIONS.some((item) => item.value === filterValue)
    ? filterValue
    : DEFAULT_TIME_FILTER;
  const today = toLocalDate(new Date());
  if (currentValue === 'ALL') {
    return {
      value: 'ALL',
      fromDate: '',
      toDate: '',
      days: 0,
    };
  }
  if (currentValue === 'TODAY') {
    const todayText = formatDateText(today);
    return {
      value: 'TODAY',
      fromDate: todayText,
      toDate: todayText,
      days: null,
    };
  }
  if (currentValue === 'THIS_WEEK') {
    const weekday = today.getDay();
    const startOffset = weekday === 0 ? -6 : 1 - weekday;
    return {
      value: 'THIS_WEEK',
      fromDate: formatDateText(addDays(today, startOffset)),
      toDate: formatDateText(today),
      days: null,
    };
  }
  if (currentValue === 'THIS_MONTH') {
    return {
      value: 'THIS_MONTH',
      fromDate: formatDateText(new Date(today.getFullYear(), today.getMonth(), 1)),
      toDate: formatDateText(today),
      days: null,
    };
  }
  return {
    value: 'THIS_YEAR',
    fromDate: formatDateText(new Date(today.getFullYear(), 0, 1)),
    toDate: formatDateText(today),
    days: null,
  };
}

function getFixedTimeFilterLabel(filterValue) {
  const matched = FIXED_TIME_FILTER_OPTIONS.find((item) => item.value === filterValue);
  return matched ? matched.label : '本周';
}

module.exports = {
  DEFAULT_TIME_FILTER,
  FIXED_TIME_FILTER_OPTIONS,
  getFixedTimeFilterLabel,
  resolveFixedTimeFilterRange,
};
