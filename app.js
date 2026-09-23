const state = { data: null, selectedSku: null, selectedMarketSku: null, salesChart: null, analyticsChart: null, marketTrendsUpdatedAt: null, adjustments: {}, manualOrders: getStoredManualOrders(), approvedOrders: getStoredApprovals() };

const urgencyLabels = { critical: 'Критичная', high: 'Высокая', medium: 'Средняя', low: 'Низкая' };

function getStoredApprovals() {
  try { return JSON.parse(localStorage.getItem('hackalem-approved-orders')) || []; } catch { return []; }
}

function getStoredManualOrders() {
  try { return JSON.parse(localStorage.getItem('hackalem-manual-orders')) || []; } catch { return []; }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
}

function setActiveTab(tabId) {
  document.querySelectorAll('.tab').forEach((button) => button.classList.toggle('is-active', button.dataset.tab === tabId));
  document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.toggle('is-active', panel.id === tabId));
  if (tabId === 'analytics') renderAnalytics();
}

function applyTheme(theme) {
  const isLight = theme === 'light';
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('hackalem-theme', theme);
  themeToggle.setAttribute('aria-pressed', String(isLight));
  themeToggle.setAttribute('aria-label', isLight ? 'Переключить тёмную тему' : 'Переключить светлую тему');
  themeToggle.title = themeToggle.getAttribute('aria-label');
  themeIcon.textContent = isLight ? '☀' : '☾';
  if (state.selectedSku) renderDetail(state.data.orders.find((order) => order.sku === state.selectedSku));
  if (state.data && document.getElementById('analytics').classList.contains('is-active')) renderAnalytics();
}

function uniqueValues(key) {
  return [...new Set(state.data.orders.map((order) => order[key]))].sort();
}

function fillFilter(id, key) {
  const select = document.getElementById(id);
  uniqueValues(key).forEach((value) => select.insertAdjacentHTML('beforeend', `<option value="${value}">${value}</option>`));
}

function renderOrders() {
  const orders = getVisibleOrders();
  ordersBody.innerHTML = orders.map((order) => `
    <tr>
      <td><button type="button" class="sku-link" data-sku="${order.sku}">${order.sku}</button></td><td>${order.name}</td><td>${order.category}</td><td>${order.supplier}</td><td>${order.warehouse}</td>
      <td class="qty">${order.recommended_qty} шт.</td><td><span class="badge badge-${order.urgency}">${urgencyLabels[order.urgency]}</span></td>
      <td class="reason">${order.reasoning.explanation_text}</td>
      <td><button class="secondary-button market-button" type="button" data-market-sku="${order.sku}">Найти альтернативу</button></td>
    </tr>`).join('');
  ordersEmpty.classList.toggle('hidden', orders.length > 0);
}

function renderSupplierComparison(order) {
  if (!order) return;
  state.selectedMarketSku = order.sku;
  supplierEmpty.classList.add('hidden'); supplierContent.classList.remove('hidden');
  supplierSku.textContent = order.sku; supplierProduct.textContent = order.name;
  supplierCurrent.textContent = `Текущий поставщик: ${order.supplier} · рекомендовано ${order.recommended_qty} шт.`;
  const alternatives = state.data.market_alternatives?.[order.sku] || [];
  const alternativeRows = alternatives.map((item) => `<tr><td class="font-semibold">${escapeHtml(item.supplier)}</td><td><span class="market-status">Альтернатива</span></td><td class="qty">${new Intl.NumberFormat('ru-RU').format(item.price)} ₸</td><td>${item.moq} шт.</td><td>${escapeHtml(item.lead_time)}</td><td><a class="source-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">Открыть ↗</a></td></tr>`).join('');
  supplierComparisonBody.innerHTML = `<tr class="current-supplier"><td class="font-semibold">${escapeHtml(order.supplier)}</td><td><span class="market-status is-current">Текущий</span></td><td>—</td><td>—</td><td>—</td><td>Нет рыночной оценки</td></tr>${alternativeRows || '<tr><td colspan="6" class="py-7 text-center text-slate-400">Для этой позиции пока нет моковых альтернатив.</td></tr>'}`;
}

function getAnalyticsTheme() {
  const isLight = document.documentElement.dataset.theme === 'light';
  return { text: isLight ? '#475569' : '#94a3b8', grid: isLight ? '#e2e8f0' : '#263244' };
}

function formatLocalDate(date) {
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' }).format(date);
}

function formatDaysRemaining(days) {
  if (days < 0) return `Просрочено на ${Math.abs(days)} дн.`;
  if (days === 0) return 'Заказать сегодня';
  if (days === 1) return 'Остался 1 день';
  return `Осталось ${days} дн.`;
}

// Временная клиентская заглушка вместо ai_service.generate_market_trends(category).
function generateMarketTrends(category) {
  const trend = state.data.analytics.market_trends.find((item) => item.category === category);
  return new Promise((resolve) => window.setTimeout(() => resolve(trend), 350));
}

function renderMarketTrends(trends = state.data.analytics.market_trends) {
  marketTrendsSummary.innerHTML = trends.map((trend) => `<article class="market-trend-item"><h3>${escapeHtml(trend.category)}</h3><p>${escapeHtml(trend.summary)}</p></article>`).join('');
  const sources = trends.flatMap((trend) => trend.sources.map((source) => ({ ...source, category: trend.category })))
    .filter((source, index, list) => list.findIndex((item) => item.url === source.url) === index);
  marketTrendsSources.innerHTML = sources.map((source) => `<li><a class="source-link" href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)} ↗</a><span>${escapeHtml(source.category)}</span></li>`).join('');
  marketTrendsStatus.textContent = state.marketTrendsUpdatedAt
    ? `Демо-анализ обновлён: ${new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(state.marketTrendsUpdatedAt)}.`
    : 'Показана исходная демо-сводка по отраслям.';
}

function renderSeasonalCalendar() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const schedule = state.data.orders.filter((order) => order.peak_season_start && Number.isFinite(order.lead_time_days)).map((order) => {
    const peakStart = new Date(`${order.peak_season_start}T00:00:00`);
    const orderBy = new Date(peakStart);
    orderBy.setDate(orderBy.getDate() - order.lead_time_days - 5);
    return { ...order, peakStart, orderBy, daysRemaining: Math.ceil((orderBy - today) / 86400000) };
  }).sort((a, b) => a.orderBy - b.orderBy);
  seasonalCalendar.innerHTML = schedule.map((item) => `<li class="seasonal-item${item.daysRemaining < 7 ? ' is-urgent' : ''}"><div class="seasonal-date"><strong>${formatLocalDate(item.orderBy)}</strong><span>заказать до</span></div><div class="seasonal-info"><p><strong>${escapeHtml(item.sku)}</strong> · ${escapeHtml(item.name)}</p><span>Пик сезона: ${formatLocalDate(item.peakStart)} · срок поставки ${item.lead_time_days} дн.</span></div><span class="seasonal-deadline">${formatDaysRemaining(item.daysRemaining)}</span></li>`).join('') || '<li class="text-slate-400">Нет позиций с заполненным сезоном.</li>';
}

function renderAnalytics() {
  if (!state.data?.analytics) return;
  const { category_demand: demand, category_growth: growth, stock_risk: risk } = state.data.analytics;
  const palette = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24'];
  const chartTheme = getAnalyticsTheme();
  if (state.analyticsChart) state.analyticsChart.destroy();
  state.analyticsChart = new Chart(categoryDemandChart, {
    type: 'line',
    data: { labels: demand.labels, datasets: demand.series.map((series, index) => ({ label: series.category, data: series.values, borderColor: palette[index % palette.length], backgroundColor: `${palette[index % palette.length]}22`, tension: .32, borderWidth: 2.5, pointRadius: 3, fill: false })) },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: chartTheme.text, usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: (context) => ` ${context.dataset.label}: ${context.parsed.y} шт.` } } }, scales: { x: { grid: { color: chartTheme.grid }, ticks: { color: chartTheme.text } }, y: { beginAtZero: true, grid: { color: chartTheme.grid }, ticks: { color: chartTheme.text, precision: 0 }, title: { display: true, text: 'Спрос, шт.', color: chartTheme.text } } } }
  });
  const rankings = (items) => items.map((item, index) => `<li><span class="ranking-number">${index + 1}</span><span>${escapeHtml(item.category)}</span><strong class="${item.change_percent >= 0 ? 'trend-up' : 'trend-down'}">${item.change_percent > 0 ? '+' : ''}${item.change_percent}%</strong></li>`).join('');
  growthList.innerHTML = rankings(growth.filter((item) => item.change_percent >= 0).sort((a, b) => b.change_percent - a.change_percent));
  declineList.innerHTML = rankings(growth.filter((item) => item.change_percent < 0).sort((a, b) => a.change_percent - b.change_percent));
  const cells = ['<div class="heatmap-corner"></div>', ...risk.categories.map((category) => `<div class="heatmap-label heatmap-column">${escapeHtml(category)}</div>`)]
    .concat(risk.warehouses.flatMap((warehouse, rowIndex) => [`<div class="heatmap-label">${escapeHtml(warehouse)}</div>`, ...risk.values[rowIndex].map((value, categoryIndex) => `<div class="heatmap-cell" role="cell" style="--risk-hue:${Math.round(120 - value * 1.2)}" title="${escapeHtml(warehouse)} · ${escapeHtml(risk.categories[categoryIndex])}: риск ${value}%"><strong>${value}%</strong><span>${value >= 70 ? 'Высокий' : value >= 40 ? 'Средний' : 'Низкий'}</span></div>`)]));
  riskHeatmap.style.gridTemplateColumns = `minmax(8rem, 1.2fr) repeat(${risk.categories.length}, minmax(8rem, 1fr))`;
  riskHeatmap.innerHTML = cells.join('');
  renderMarketTrends();
  renderSeasonalCalendar();
}

function getVisibleOrders() {
  const filters = { warehouse: warehouseFilter.value, category: categoryFilter.value, supplier: supplierFilter.value, urgency: urgencyFilter.value };
  return state.data.orders.filter((order) => Object.entries(filters).every(([key, value]) => !value || order[key] === value));
}

const stockoutPlugin = {
  id: 'stockoutPeriods',
  beforeDatasetsDraw(chart) {
    const periods = chart.options.plugins.stockoutPeriods || [];
    if (!periods.length) return;
    const { ctx, chartArea } = chart;
    const history = chart.data.datasets[0].data;
    const dates = history.map((item) => new Date(item.date).getTime());
    const minDate = Math.min(...dates); const maxDate = Math.max(...dates);
    if (minDate === maxDate) return;
    const toX = (date) => chartArea.left + ((Math.max(minDate, Math.min(maxDate, new Date(date).getTime())) - minDate) / (maxDate - minDate)) * (chartArea.right - chartArea.left);
    ctx.save();
    periods.forEach((period) => {
      const left = toX(period.start); const right = toX(period.end);
      ctx.fillStyle = 'rgba(251, 146, 60, 0.20)'; ctx.fillRect(left, chartArea.top, Math.max(3, right - left), chartArea.bottom - chartArea.top);
      ctx.strokeStyle = 'rgba(251, 146, 60, 0.85)'; ctx.setLineDash([4, 3]); ctx.strokeRect(left, chartArea.top, Math.max(3, right - left), chartArea.bottom - chartArea.top);
    });
    ctx.restore();
  }
};

function renderDetail(order) {
  if (!order) return;
  state.selectedSku = order.sku;
  detailEmpty.classList.add('hidden'); detailContent.classList.remove('hidden');
  detailSku.textContent = order.sku; detailName.textContent = order.name;
  detailMeta.textContent = `${order.category} · ${order.supplier} · ${order.warehouse}`;
  detailUrgency.innerHTML = `<span class="badge badge-${order.urgency}">${urgencyLabels[order.urgency]} приоритет</span>`;
  detailExplanation.textContent = order.reasoning.explanation_text;
  if (state.salesChart) state.salesChart.destroy();
  const isLight = document.documentElement.dataset.theme === 'light';
  const textColor = isLight ? '#475569' : '#94a3b8';
  const gridColor = isLight ? '#e2e8f0' : '#263244';
  state.salesChart = new Chart(salesChart, {
    type: 'line',
    data: { labels: order.history.map((item) => new Intl.DateTimeFormat('ru-RU', { month: 'short', year: 'numeric' }).format(new Date(`${item.date}T00:00:00`))), datasets: [{ data: order.history, parsing: { yAxisKey: 'qty' }, borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,.16)', pointBackgroundColor: '#7dd3fc', pointRadius: 4, fill: true, tension: .32, borderWidth: 2.5, label: 'Продажи, шт.' }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: textColor, usePointStyle: true } }, tooltip: { callbacks: { label: (context) => ` ${context.parsed.y} шт.` } }, stockoutPeriods: order.stockout_periods }, scales: { x: { grid: { color: gridColor }, ticks: { color: textColor } }, y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor, precision: 0 }, title: { display: true, text: 'Количество, шт.', color: textColor } } } },
    plugins: [stockoutPlugin]
  });
}

function renderAnomalies() {
  anomaliesBody.innerHTML = state.data.excluded_anomalies.map((item) => `
    <tr><td class="font-semibold text-sky-300">${item.sku}</td><td>${item.date}</td><td class="qty">${item.qty} шт.</td><td>${item.client_id}</td><td class="reason">${item.reason}</td><td><button class="secondary-button">Вернуть в расчёт</button></td></tr>`).join('');
}

function getApprovalOrders() {
  return [...state.data.orders, ...state.manualOrders];
}

function adjustedOrder(order) {
  const adjustment = state.adjustments[order.sku] || {};
  const defaultQuantity = order.is_manual ? order.order_qty : order.recommended_qty;
  return { ...order, order_qty: Number.isFinite(adjustment.quantity) ? adjustment.quantity : defaultQuantity, adjustment_reason: adjustment.reason || order.adjustment_reason || '' };
}

function renderApproval() {
  const ordersBySupplier = getApprovalOrders().reduce((groups, order) => {
    (groups[order.supplier] ||= []).push(order);
    return groups;
  }, {});
  approvalGroups.innerHTML = Object.entries(ordersBySupplier).map(([supplier, orders]) => `
    <section class="supplier-group">
      <header class="supplier-heading"><div><h3>${escapeHtml(supplier)}</h3><p>${orders.length} ${orders.length === 1 ? 'позиция' : 'позиции'} к утверждению</p></div><button class="primary-button approve-supplier" type="button" data-supplier="${escapeHtml(supplier)}">Утвердить заказ</button></header>
      <div class="table-wrap border-0 rounded-none"><table class="approval-table"><thead><tr><th>Артикул</th><th>Наименование</th><th>Склад</th><th>Рекомендовано</th><th>Количество к заказу</th><th>Причина корректировки</th></tr></thead><tbody>
      ${orders.map((order) => { const value = adjustedOrder(order); return `<tr class="${order.is_manual ? 'manual-order-row' : ''}"><td class="font-semibold text-sky-300">${escapeHtml(order.sku)}${order.is_manual ? '<span class="manual-badge">Добавлено вручную</span>' : ''}</td><td>${escapeHtml(order.name)}</td><td>${escapeHtml(order.warehouse)}</td><td class="qty">${order.is_manual ? '—' : `${order.recommended_qty} шт.`}</td><td><input class="form-input" data-adjustment="quantity" data-sku="${escapeHtml(order.sku)}" type="number" min="0" step="1" value="${value.order_qty}" aria-label="Количество к заказу для ${escapeHtml(order.sku)}" /></td><td><input class="reason-input" data-adjustment="reason" data-sku="${escapeHtml(order.sku)}" type="text" value="${escapeHtml(value.adjustment_reason)}" placeholder="Почему изменено?" aria-label="Причина корректировки для ${escapeHtml(order.sku)}" /></td></tr>`; }).join('')}
      </tbody></table></div>
    </section>`).join('');
}

function renderManualFormOptions() {
  const fields = [
    [manualCategories, 'category'], [manualSuppliers, 'supplier'], [manualWarehouses, 'warehouse']
  ];
  fields.forEach(([list, key]) => {
    list.innerHTML = uniqueValues(key).map((value) => `<option value="${escapeHtml(value)}"></option>`).join('');
  });
}

function setManualFormOpen(isOpen) {
  manualPositionForm.classList.toggle('hidden', !isOpen);
  addPositionButton.setAttribute('aria-expanded', String(isOpen));
  if (isOpen) manualPositionForm.elements.sku.focus();
}

function addManualOrder(form) {
  const formData = new FormData(form);
  const value = (key) => String(formData.get(key) || '').trim();
  const quantity = Number(value('quantity'));
  const position = { sku: value('sku'), name: value('name'), category: value('category'), supplier: value('supplier'), warehouse: value('warehouse'), reason: value('reason') };
  if (Object.values(position).some((item) => !item) || !Number.isInteger(quantity) || quantity < 1) {
    manualPositionError.textContent = 'Заполните все поля; количество должно быть целым числом не меньше 1.';
    return;
  }
  if (getApprovalOrders().some((order) => order.sku.toLowerCase() === position.sku.toLowerCase())) {
    manualPositionError.textContent = 'Позиция с таким артикулом уже есть в заказе. Измените артикул или отредактируйте существующую строку.';
    return;
  }
  state.manualOrders.push({ ...position, order_qty: quantity, urgency: 'manual', is_manual: true, adjustment_reason: position.reason, reasoning: { explanation_text: `Добавлено вручную: ${position.reason}` } });
  localStorage.setItem('hackalem-manual-orders', JSON.stringify(state.manualOrders));
  form.reset(); manualPositionError.textContent = '';
  setManualFormOpen(false);
  renderApproval(); renderExportStatus();
  approvalStatus.textContent = `Позиция «${position.sku}» добавлена вручную к заказу для «${position.supplier}».`;
  approvalStatus.classList.remove('hidden');
}

function approveSupplier(supplier) {
  const positions = getApprovalOrders().filter((order) => order.supplier === supplier).map((order) => {
    const adjusted = adjustedOrder(order);
    return { sku: adjusted.sku, name: adjusted.name, category: adjusted.category, warehouse: adjusted.warehouse, recommended_qty: adjusted.order_qty, urgency: adjusted.urgency, explanation_text: adjusted.reasoning.explanation_text, adjustment_reason: adjusted.adjustment_reason, is_manual: Boolean(adjusted.is_manual) };
  });
  const supplierOrder = { supplier, approved_at: new Date().toISOString(), positions };
  state.approvedOrders = [...state.approvedOrders.filter((order) => order.supplier !== supplier), supplierOrder];
  localStorage.setItem('hackalem-approved-orders', JSON.stringify(state.approvedOrders));
  console.info('Approved supplier order (demo):', supplierOrder);
  approvalStatus.textContent = `Заказ для «${supplier}» сохранён в браузере. Отправка поставщику не выполнялась.`;
  approvalStatus.classList.remove('hidden');
  renderExportStatus();
}

const exportColumns = [
  { key: 'sku', label: 'Артикул' }, { key: 'name', label: 'Наименование' }, { key: 'category', label: 'Категория' }, { key: 'supplier', label: 'Поставщик' },
  { key: 'warehouse', label: 'Склад' }, { key: 'recommended_qty', label: 'Рекомендовано' }, { key: 'urgency', label: 'Срочность' }, { key: 'explanation_text', label: 'Обоснование' }
];

function getExportRows() {
  const currentRows = [...getVisibleOrders(), ...state.manualOrders].map((order) => ({ supplier: order.supplier, ...adjustedOrder(order), explanation_text: order.reasoning.explanation_text }));
  const approvedRows = state.approvedOrders.flatMap((supplierOrder) => supplierOrder.positions.map((position) => ({ supplier: supplierOrder.supplier, ...position })));
  const approvedManualSkus = new Set(approvedRows.filter((row) => row.is_manual).map((row) => row.sku));
  const sourceRows = state.approvedOrders.length ? [...approvedRows, ...currentRows.filter((row) => row.is_manual && !approvedManualSkus.has(row.sku))] : currentRows;
  return sourceRows.map((row) => {
    const sourceOrder = state.data.orders.find((order) => order.sku === row.sku) || {};
    return {
      sku: row.sku, name: row.name || sourceOrder.name, category: row.category || sourceOrder.category, supplier: row.supplier || sourceOrder.supplier,
      warehouse: row.warehouse || sourceOrder.warehouse, recommended_qty: row.order_qty ?? row.recommended_qty, urgency: row.is_manual ? 'Ручная позиция' : row.urgency || sourceOrder.urgency,
      explanation_text: row.explanation_text || sourceOrder.reasoning?.explanation_text || ''
    };
  });
}

function getExportTable() {
  const rows = getExportRows();
  return { headers: exportColumns.map((column) => column.label), rows: rows.map((row) => exportColumns.map((column) => row[column.key])) };
}

function positionCountLabel(count, adjective = '') {
  const mod100 = count % 100; const mod10 = count % 10;
  const plural = mod100 >= 11 && mod100 <= 14 ? 'many' : mod10 === 1 ? 'one' : mod10 >= 2 && mod10 <= 4 ? 'few' : 'many';
  const words = adjective === 'approved'
    ? { one: 'утверждённая позиция', few: 'утверждённые позиции', many: 'утверждённых позиций' }
    : adjective === 'manual'
      ? { one: 'ручная позиция', few: 'ручные позиции', many: 'ручных позиций' }
      : { one: 'позиция', few: 'позиции', many: 'позиций' };
  return `${count} ${words[plural]}`;
}

function renderExportStatus() {
  if (!state.data) return;
  const count = getExportRows().length;
  if (state.approvedOrders.length) {
    exportStatus.textContent = `Готово к экспорту: ${positionCountLabel(count, 'approved')}${state.manualOrders.length ? `, включая ${positionCountLabel(state.manualOrders.length, 'manual')}` : ''}.`;
  } else {
    exportStatus.textContent = `Готово к экспорту: ${positionCountLabel(count)} в текущих рекомендациях${state.manualOrders.length ? `, включая ${positionCountLabel(state.manualOrders.length, 'manual')}` : ''}.`;
  }
}

function downloadCsv() {
  const { headers, rows } = getExportTable();
  const escapeCsv = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const csv = [headers, ...rows].map((row) => row.map(escapeCsv).join(';')).join('\r\n');
  const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = `orders-${new Date().toISOString().slice(0, 10)}.csv`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  exportStatus.textContent = `CSV скачан: ${rows.length} позиций.`;
}

function downloadExcel() {
  if (!window.XLSX) { exportStatus.textContent = 'Библиотека Excel ещё не загружена. Попробуйте ещё раз.'; return; }
  const { headers, rows } = getExportTable();
  const worksheet = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  worksheet['!cols'] = [{ wch: 15 }, { wch: 30 }, { wch: 25 }, { wch: 24 }, { wch: 14 }, { wch: 15 }, { wch: 14 }, { wch: 62 }];
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Заказы');
  XLSX.writeFile(workbook, `orders-${new Date().toISOString().slice(0, 10)}.xlsx`);
  exportStatus.textContent = `Excel скачан: ${rows.length} позиций.`;
}

function registerRobotoFont(doc) {
  const fontBase64 = window.HACKALEM_ROBOTO_BASE64;
  if (typeof fontBase64 !== 'string' || !fontBase64.startsWith('AAE')) throw new Error('Не удалось загрузить встраиваемый шрифт Roboto.');
  doc.addFileToVFS('Roboto-Regular.ttf', fontBase64);
  doc.addFont('Roboto-Regular.ttf', 'Roboto', 'normal');
  doc.setFont('Roboto', 'normal');
}

function downloadPdf() {
  const JsPdf = window.jspdf?.jsPDF;
  if (!JsPdf) { exportStatus.textContent = 'Библиотека PDF ещё не загружена. Попробуйте ещё раз.'; return; }
  try {
    const { headers, rows } = getExportTable();
    const doc = new JsPdf({ orientation: 'landscape', unit: 'mm', format: 'a4' });
    registerRobotoFont(doc);
    doc.setFontSize(16); doc.text('Список рекомендованных заказов', 14, 15);
    doc.setFontSize(9); doc.text(`Дата формирования отчёта: ${new Intl.DateTimeFormat('ru-RU', { dateStyle: 'long', timeStyle: 'short' }).format(new Date())}`, 14, 23);
    doc.autoTable({ startY: 29, head: [headers], body: rows, theme: 'grid', styles: { font: 'Roboto', fontStyle: 'normal', fontSize: 6.5, cellPadding: 1.8, overflow: 'linebreak' }, headStyles: { font: 'Roboto', fontStyle: 'normal', fillColor: [2, 132, 199] }, columnStyles: { 1: { cellWidth: 33 }, 3: { cellWidth: 28 }, 7: { cellWidth: 65 } } });
    doc.save(`orders-${new Date().toISOString().slice(0, 10)}.pdf`);
    exportStatus.textContent = `PDF скачан: ${rows.length} позиций.`;
  } catch (error) {
    exportStatus.textContent = 'Не удалось подготовить PDF: шрифт Roboto не загружен.';
    console.error(error);
  }
}

async function loadMockData() {
  const status = document.getElementById('data-status');
  try {
    const response = await fetch('mock-data.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    fillFilter('warehouse-filter', 'warehouse'); fillFilter('category-filter', 'category'); fillFilter('supplier-filter', 'supplier');
    renderOrders(); renderAnomalies(); renderApproval(); renderManualFormOptions(); renderExportStatus();
    document.getElementById('mock-summary').innerHTML = `<p><strong class="text-slate-100">${state.data.orders.length}</strong> рекомендованных позиций в ${uniqueValues('category').length} категориях.</p><p><strong class="text-slate-100">${state.data.excluded_anomalies.length}</strong> аномалии исключены из регулярной потребности.</p>`;
    status.textContent = 'Моковые данные загружены';
  } catch (error) {
    status.textContent = 'Не удалось загрузить mock-data.json';
    document.getElementById('mock-summary').innerHTML = '<p class="text-red-300">Запустите сайт через локальный статический сервер: fetch не работает при открытии HTML как файла.</p>';
    console.error(error);
  }
}

const warehouseFilter = document.getElementById('warehouse-filter');
const categoryFilter = document.getElementById('category-filter');
const supplierFilter = document.getElementById('supplier-filter');
const urgencyFilter = document.getElementById('urgency-filter');
const ordersBody = document.getElementById('orders-body');
const ordersEmpty = document.getElementById('orders-empty');
const anomaliesBody = document.getElementById('anomalies-body');
const detailEmpty = document.getElementById('detail-empty');
const detailContent = document.getElementById('detail-content');
const detailSku = document.getElementById('detail-sku');
const detailName = document.getElementById('detail-name');
const detailMeta = document.getElementById('detail-meta');
const detailUrgency = document.getElementById('detail-urgency');
const detailExplanation = document.getElementById('detail-explanation');
const salesChart = document.getElementById('sales-chart');
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.getElementById('theme-icon');
const approvalGroups = document.getElementById('approval-groups');
const approvalStatus = document.getElementById('approval-status');
const addPositionButton = document.getElementById('add-position-button');
const manualPositionForm = document.getElementById('manual-position-form');
const manualPositionError = document.getElementById('manual-position-error');
const manualCategories = document.getElementById('manual-categories');
const manualSuppliers = document.getElementById('manual-suppliers');
const manualWarehouses = document.getElementById('manual-warehouses');
const csvExport = document.getElementById('csv-export');
const excelExport = document.getElementById('excel-export');
const pdfExport = document.getElementById('pdf-export');
const exportStatus = document.getElementById('export-status');
const supplierEmpty = document.getElementById('supplier-empty');
const supplierContent = document.getElementById('supplier-content');
const supplierSku = document.getElementById('supplier-sku');
const supplierProduct = document.getElementById('supplier-product');
const supplierCurrent = document.getElementById('supplier-current');
const supplierComparisonBody = document.getElementById('supplier-comparison-body');
const categoryDemandChart = document.getElementById('category-demand-chart');
const growthList = document.getElementById('growth-list');
const declineList = document.getElementById('decline-list');
const riskHeatmap = document.getElementById('risk-heatmap');
const marketTrendsButton = document.getElementById('refresh-market-trends');
const marketTrendsStatus = document.getElementById('market-trends-status');
const marketTrendsSummary = document.getElementById('market-trends-summary');
const marketTrendsSources = document.getElementById('market-trends-sources');
const seasonalCalendar = document.getElementById('seasonal-calendar');

document.querySelectorAll('.tab').forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.tab)));
document.querySelectorAll('[data-go-tab]').forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.goTab)));
[warehouseFilter, categoryFilter, supplierFilter, urgencyFilter].forEach((filter) => filter.addEventListener('change', () => { renderOrders(); renderExportStatus(); }));
ordersBody.addEventListener('click', (event) => {
  const marketButton = event.target.closest('[data-market-sku]');
  if (marketButton && state.data) {
    renderSupplierComparison(state.data.orders.find((order) => order.sku === marketButton.dataset.marketSku));
    setActiveTab('suppliers');
    return;
  }
  const skuButton = event.target.closest('[data-sku]');
  if (!skuButton || !state.data) return;
  renderDetail(state.data.orders.find((order) => order.sku === skuButton.dataset.sku));
  setActiveTab('detail');
});
approvalGroups.addEventListener('input', (event) => {
  const input = event.target.closest('[data-adjustment]');
  if (!input) return;
  const previous = state.adjustments[input.dataset.sku] || {};
  state.adjustments[input.dataset.sku] = input.dataset.adjustment === 'quantity' ? { ...previous, quantity: Number(input.value) } : { ...previous, reason: input.value };
  renderExportStatus();
});
approvalGroups.addEventListener('click', (event) => {
  const button = event.target.closest('.approve-supplier');
  if (button) approveSupplier(button.dataset.supplier);
});
addPositionButton.addEventListener('click', () => { manualPositionError.textContent = ''; setManualFormOpen(manualPositionForm.classList.contains('hidden')); });
manualPositionForm.addEventListener('submit', (event) => { event.preventDefault(); addManualOrder(manualPositionForm); });
manualPositionForm.addEventListener('click', (event) => { if (event.target.closest('[data-cancel-manual], #cancel-manual-position')) { manualPositionError.textContent = ''; setManualFormOpen(false); } });
csvExport.addEventListener('click', downloadCsv);
excelExport.addEventListener('click', downloadExcel);
pdfExport.addEventListener('click', downloadPdf);
marketTrendsButton.addEventListener('click', async () => {
  if (!state.data?.analytics?.market_trends) return;
  marketTrendsButton.disabled = true;
  marketTrendsButton.textContent = 'Обновляем…';
  marketTrendsStatus.textContent = 'Генерируем демо-сводку по категориям…';
  try {
    const trends = await Promise.all(state.data.analytics.market_trends.map((trend) => generateMarketTrends(trend.category)));
    state.marketTrendsUpdatedAt = new Date();
    renderMarketTrends(trends.filter(Boolean));
  } finally {
    marketTrendsButton.disabled = false;
    marketTrendsButton.textContent = 'Обновить анализ';
  }
});
themeToggle.addEventListener('click', () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
applyTheme(document.documentElement.dataset.theme);
loadMockData();
