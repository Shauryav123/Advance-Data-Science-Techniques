async function analystLoad() {
  const [summary, restaurants, performance, benchmark] = await Promise.all([
    fetch('/api/summary').then((r) => r.json()),
    fetch('/api/restaurants').then((r) => r.json()),
    fetch('/api/performance').then((r) => r.json()),
    fetch('/api/model-benchmark').then((r) => r.ok ? r.json() : null),
  ]);
  document.querySelector('#restaurants').textContent = summary.restaurants;
  document.querySelector('#pairs').textContent = summary.high_similarity_pairs;
  document.querySelector('#average').textContent = summary.average_similarity;
  document.querySelector('#performance-records').textContent = performance.restaurants || '—';
  document.querySelector('#monthly-orders').textContent = performance.restaurants
    ? performance.monthly_orders.toLocaleString('en-IN') : 'Not loaded';
  document.querySelector('#monthly-revenue').textContent = performance.restaurants
    ? `₹${performance.monthly_revenue_inr.toLocaleString('en-IN')}` : 'Not loaded';
  document.querySelector('#growth').textContent = performance.restaurants
    ? `${performance.average_growth_pct}%` : 'Not loaded';
  const cities = Object.entries(restaurants.reduce((counts, row) => { counts[row.city] = (counts[row.city] || 0) + 1; return counts; }, {})).sort((a, b) => b[1] - a[1]);
  const max = cities[0]?.[1] || 1;
  document.querySelector('#city-bars').innerHTML = cities.map(([city, count]) => `<div class="bar-row"><span>${city}</span><i style="width:${count / max * 100}%"></i><b>${count}</b></div>`).join('');
  renderBenchmark(benchmark);
}
function renderBenchmark(report) {
  const status = document.querySelector('#model-status');
  const target = document.querySelector('#model-benchmark');
  if (!report) {
    status.textContent = 'Please run the benchmark test script first';
    if (target) target.innerHTML = '<div class="empty-state">No accuracy report is available yet.</div>';
    return;
  }
  const targets = report.targets || {};
  const orders = targets.monthly_orders;
  const revenue = targets.monthly_revenue_inr;
  status.textContent = orders && revenue ? 'Orders and revenue tested separately' : 'Incomplete accuracy report';
  renderTargetBenchmark(document.querySelector('#model-benchmark-orders'), 'Estimated monthly orders', orders);
  renderTargetBenchmark(document.querySelector('#model-benchmark-revenue'), 'Estimated monthly revenue (INR)', revenue);
}
function renderTargetBenchmark(target, label, report) {
  if (!target) return;
  if (!report) {
    target.innerHTML = `<h3>${label}</h3><div class="empty-state">No accuracy report available.</div>`;
    return;
  }
  const rows = Object.entries(report.models).map(([name, metrics]) => `<tr><td><strong>${name}</strong></td><td>${metrics.mae.toLocaleString('en-IN', {maximumFractionDigits: 0})}</td><td>${metrics.rmse.toLocaleString('en-IN', {maximumFractionDigits: 0})}</td><td>${metrics.r2.toFixed(3)}</td></tr>`).join('');
  target.innerHTML = `<h3>${label}</h3><table><thead><tr><th>MODEL</th><th>AVG ERROR (MAE)</th><th>RMSE</th><th>ACCURACY (R²)</th></tr></thead><tbody>${rows}</tbody></table>`;
}
analystLoad();
