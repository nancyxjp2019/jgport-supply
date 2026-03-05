function padText(value) {
  return `${value}`.padStart(2, '0');
}

function isBlankValue(value) {
  return value === undefined || value === null || (typeof value === 'string' && value.trim() === '');
}

function addThousandsSeparators(text) {
  const normalized = String(text || '');
  const [integerPart, decimalPart] = normalized.split('.');
  const signedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return decimalPart !== undefined ? `${signedInteger}.${decimalPart}` : signedInteger;
}

function normalizeDateInput(value) {
  const text = String(value || '').trim();
  if (!text) {
    return value;
  }
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/.test(text)) {
    return `${text}Z`;
  }
  return value;
}

function formatDate(value) {
  if (!value) {
    return '';
  }
  const date = new Date(normalizeDateInput(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return `${date.getFullYear()}-${padText(date.getMonth() + 1)}-${padText(date.getDate())}`;
}

function formatDateTime(value) {
  if (!value) {
    return '';
  }
  const date = new Date(normalizeDateInput(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return `${formatDate(date)} ${padText(date.getHours())}:${padText(date.getMinutes())}:${padText(date.getSeconds())}`;
}

function formatNumber(value, digits = 2) {
  if (isBlankValue(value)) {
    return '-';
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '-';
  }
  return numeric.toFixed(digits);
}

function formatMoney(value) {
  if (isBlankValue(value)) {
    return '-';
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '-';
  }
  return addThousandsSeparators(numeric.toFixed(2));
}

function todayText() {
  return formatDate(new Date());
}

function buildQueryString(params = {}) {
  const segments = Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`);
  return segments.length ? `?${segments.join('&')}` : '';
}

module.exports = {
  addThousandsSeparators,
  buildQueryString,
  formatDate,
  formatDateTime,
  formatMoney,
  formatNumber,
  normalizeDateInput,
  todayText,
};
