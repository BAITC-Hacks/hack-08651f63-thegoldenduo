const state = { data: null, selectedSku: null, salesChart: null };

const urgencyLabels = { critical: 'Критичная', high: 'Высокая', medium: 'Средняя', low: 'Низкая' };

function setActiveTab(tabId) {
  document.querySelectorAll('.tab').forEach((button) => button.classList.toggle('is-active', button.dataset.tab === tabId));
  document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.toggle('is-active', panel.id === tabId));
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
}

function uniqueValues(key) {
  return [...new Set(state.data.orders.map((order) => order[key]))].sort();
}

function fillFilter(id, key) {
  const select = document.getElementById(id);
  uniqueValues(key).forEach((value) => select.insertAdjacentHTML('beforeend', `<option value="${value}">${value}</option>`));
}

function renderOrders() {
  const filters = { warehouse: warehouseFilter.value, category: categoryFilter.value, supplier: supplierFilter.value, urgency: urgencyFilter.value };
  const orders = state.data.orders.filter((order) => Object.entries(filters).every(([key, value]) => !value || order[key] === value));
  ordersBody.innerHTML = orders.map((order) => `
    <tr>
      <td><button type="button" class="sku-link" data-sku="${order.sku}">${order.sku}</button></td><td>${order.name}</td><td>${order.category}</td><td>${order.supplier}</td><td>${order.warehouse}</td>
      <td class="qty">${order.recommended_qty} шт.</td><td><span class="badge badge-${order.urgency}">${urgencyLabels[order.urgency]}</span></td>
      <td class="reason">${order.reasoning.explanation_text}</td>
    </tr>`).join('');
  ordersEmpty.classList.toggle('hidden', orders.length > 0);
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

async function loadMockData() {
  const status = document.getElementById('data-status');
  try {
    const response = await fetch('mock-data.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    fillFilter('warehouse-filter', 'warehouse'); fillFilter('category-filter', 'category'); fillFilter('supplier-filter', 'supplier');
    renderOrders(); renderAnomalies();
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

document.querySelectorAll('.tab').forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.tab)));
document.querySelectorAll('[data-go-tab]').forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.goTab)));
[warehouseFilter, categoryFilter, supplierFilter, urgencyFilter].forEach((filter) => filter.addEventListener('change', renderOrders));
ordersBody.addEventListener('click', (event) => {
  const skuButton = event.target.closest('[data-sku]');
  if (!skuButton || !state.data) return;
  renderDetail(state.data.orders.find((order) => order.sku === skuButton.dataset.sku));
  setActiveTab('detail');
});
themeToggle.addEventListener('click', () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
applyTheme(document.documentElement.dataset.theme);
loadMockData();
