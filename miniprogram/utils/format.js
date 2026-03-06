function isBlankValue(value) {
  return value === undefined || value === null || (typeof value === 'string' && value.trim() === '');
}

function addThousandsSeparators(text) {
  const normalized = String(text || '');
  const segments = normalized.split('.');
  const integerText = segments[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return segments.length > 1 ? `${integerText}.${segments[1]}` : integerText;
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

function formatQty(value) {
  if (isBlankValue(value)) {
    return '-';
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '-';
  }
  return addThousandsSeparators(numeric.toFixed(3));
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

function padText(value) {
  return `${value}`.padStart(2, '0');
}

function formatDateTime(value) {
  if (!value) {
    return '暂无时间';
  }
  const date = new Date(normalizeDateInput(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return `${date.getFullYear()}-${padText(date.getMonth() + 1)}-${padText(date.getDate())} ${padText(date.getHours())}:${padText(date.getMinutes())}`;
}

module.exports = {
  formatDateTime,
  formatMoney,
  formatQty,
};
