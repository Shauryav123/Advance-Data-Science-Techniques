const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[char]));

let allRestaurants = [];
let allInsights = [];
let repetitiveAreas = [];
let currentCity = 'all';
let selectedLocation = null;
let selectedCategory = 'all';
let searchQuery = '';
let cachedOpportunities = [];
let loadTimer = null;

async function initDashboard() {
  const mapStatus = $('#map-status');
  try {
    $('#map').classList.add('is-loading');
    if (mapStatus) mapStatus.textContent = 'Loading market data…';

    const [restRes, insRes, repRes, sumRes] = await Promise.all([
      fetch('/api/restaurants'),
      fetch('/api/insights?min_similarity=0.18'),
      fetch('/api/repetitive-areas'),
      fetch('/api/summary')
    ]);

    allRestaurants = await restRes.json();
    allInsights = await insRes.json();
    repetitiveAreas = await repRes.json();

    // Populate City Filter dropdown & interactive listeners
    populateCityFilter();
    setupCategoryPills();
    setupDishSearch();
    setupResetButton();
    setupThresholdListener();

    // Initial load
    renderDashboard();

    if (mapStatus) {
      mapStatus.textContent = `Analyzed ${allRestaurants.length} kitchens across ${repetitiveAreas.length} delivery areas.`;
    }
  } catch (err) {
    console.error(err);
    if (mapStatus) mapStatus.textContent = 'Failed to load market data. Check server connection.';
  } finally {
    $('#map').classList.remove('is-loading');
  }
}

function populateCityFilter() {
  const citySelect = $('#city-filter');
  if (!citySelect) return;
  const cities = [...new Set(allRestaurants.map(r => r.city).filter(Boolean))].sort();
  citySelect.innerHTML = `<option value="all">All Cities</option>` +
    cities.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('');

  citySelect.addEventListener('change', (e) => {
    currentCity = e.target.value;
    selectedLocation = null;
    toggleResetButton(false);
    renderDashboard();
  });
}

function setupCategoryPills() {
  const container = $('#category-pills');
  if (!container) return;

  container.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-pill');
    if (!btn) return;

    container.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedCategory = btn.getAttribute('data-cat') || 'all';
    filterAndDisplayOpportunities();
  });
}

function setupDishSearch() {
  const searchInput = $('#dish-search');
  if (!searchInput) return;

  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    filterAndDisplayOpportunities();
  });
}

function setupResetButton() {
  const resetBtn = $('#reset-loc-btn');
  if (!resetBtn) return;

  resetBtn.addEventListener('click', () => {
    selectedLocation = null;
    toggleResetButton(false);
    renderDashboard();
  });
}

function toggleResetButton(show) {
  const resetBtn = $('#reset-loc-btn');
  if (resetBtn) {
    resetBtn.style.display = show ? 'inline-block' : 'none';
  }
}

function renderDashboard() {
  const threshold = Number($('#threshold').value || 0.30);

  // Filter restaurants by city
  const filteredRest = currentCity === 'all'
    ? allRestaurants
    : allRestaurants.filter(r => r.city.toLowerCase() === currentCity.toLowerCase());

  // Filter repetitive areas
  const filteredAreas = currentCity === 'all'
    ? repetitiveAreas
    : repetitiveAreas.filter(a => a.city.toLowerCase() === currentCity.toLowerCase());

  // Filter pairwise insights
  const filteredInsights = allInsights.filter(item => {
    const meetThreshold = item.similarity >= threshold;
    if (!meetThreshold) return false;
    if (currentCity === 'all') return true;
    return (item.city_a && item.city_a.toLowerCase() === currentCity.toLowerCase());
  });

  // Update Stats Cards
  $('#restaurants').textContent = filteredRest.length;
  $('#pairs').textContent = filteredInsights.length;
  
  const avgSim = filteredInsights.length
    ? (filteredInsights.reduce((sum, item) => sum + item.similarity, 0) / filteredInsights.length).toFixed(3)
    : '0.000';
  $('#average').textContent = avgSim;

  // Render components
  renderInteractiveMap(filteredRest, filteredInsights, filteredAreas);
  renderRepetitiveAreas(filteredAreas);
  fetchOpportunities(currentCity, selectedLocation);
  renderComparisonTable(filteredInsights);
}

function renderInteractiveMap(places, insights, areas) {
  const pointsContainer = $('#map-points');
  const linesContainer = $('#map-lines');
  const mapStatus = $('#map-status');
  if (!pointsContainer || !linesContainer) return;

  pointsContainer.innerHTML = '';
  linesContainer.innerHTML = '';

  if (!places.length) return;

  const threshold = Number($('#threshold').value || 0.30);
  const threshPct = Math.round(threshold * 100);

  // Update map status banner with precise live feedback
  if (mapStatus) {
    if (insights.length > 0) {
      const activeLocs = new Set(insights.map(i => i.location_a || i.location_b).filter(Boolean));
      mapStatus.innerHTML = `Showing <strong>${insights.length}</strong> similar restaurant pair${insights.length === 1 ? '' : 's'} at or above <strong>${threshPct}%</strong> across <strong>${activeLocs.size}</strong> area${activeLocs.size === 1 ? '' : 's'}.`;
    } else {
      mapStatus.innerHTML = `No similar restaurant pairs found at or above <strong>${threshPct}%</strong>. Lower the slider to see more pairs.`;
    }
  }

  const lats = places.map(p => p.latitude);
  const lons = places.map(p => p.longitude);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons);
  const latRange = maxLat - minLat || 0.05;
  const lonRange = maxLon - minLon || 0.05;

  function toXY(lat, lon) {
    return {
      x: 10 + ((lon - minLon) / lonRange) * 80,
      y: 86 - ((lat - minLat) / latRange) * 72
    };
  }

  // Draw similarity connection lines
  insights.slice(0, 150).forEach(item => {
    const start = toXY(item.latitude_a, item.longitude_a);
    const end = toXY(item.latitude_b, item.longitude_b);
    let length = Math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2);
    if (length < 3.5) length = 3.5;
    const angle = Math.atan2(end.y - start.y, end.x - start.x) * 180 / Math.PI;
    const isCritical = item.similarity >= 0.75;
    const opacity = isCritical ? 0.95 : Math.min(0.85, 0.45 + item.similarity * 0.5);
    const strokeHeight = isCritical ? 3.5 : 2.5;

    linesContainer.innerHTML += `
      <i class="map-line ${isCritical ? 'critical' : ''}" 
         style="left:${start.x}%; top:${start.y}%; width:${length}%; height:${strokeHeight}px; opacity:${opacity}; transform:rotate(${angle}deg)"
         title="${esc(item.restaurant_a)} ⇄ ${esc(item.restaurant_b)}: ${(item.similarity * 100).toFixed(1)}% menu similarity in ${esc(item.location_a)}"></i>
    `;
  });

  // Draw locality cluster nodes
  areas.forEach(area => {
    const pos = toXY(area.latitude, area.longitude);
    const isSelected = selectedLocation && selectedLocation.toLowerCase() === area.locality.toLowerCase();
    
    // Check if this locality contains active overlapping kitchen pairs >= current threshold
    const areaOverlapPairs = insights.filter(it =>
      (it.location_a && it.location_a.toLowerCase() === area.locality.toLowerCase()) ||
      (it.location_b && it.location_b.toLowerCase() === area.locality.toLowerCase())
    );
    const isHot = areaOverlapPairs.length > 0;
    const size = Math.min(42, 18 + area.restaurant_count * 1.5);
    
    const node = document.createElement('div');
    node.className = `map-point ${isHot ? 'hot' : ''} ${isSelected ? 'selected' : ''}`;
    node.style.left = `${pos.x}%`;
    node.style.top = `${pos.y}%`;
    node.style.setProperty('--point-size', `${size}px`);
    node.setAttribute('data-name', `${area.locality}`);
    
    const overlapMsg = isHot 
      ? `• ${areaOverlapPairs.length} similar pair(s) at or above ${threshPct}%`
      : `• No pairs reach ${threshPct}% similarity`;

    node.title = `${area.locality}, ${area.city}\n${overlapMsg}\n• ${area.restaurant_count} Listed Kitchens\n• ${area.osm_competitors} Local Food Places\nClick to inspect opportunities`;
    node.innerHTML = `<span>${area.restaurant_count}</span>`;
    
    // Node click handler
    node.addEventListener('click', () => {
      selectedLocation = area.locality;
      currentCity = area.city;
      $('#city-filter').value = area.city;
      toggleResetButton(true);
      renderDashboard();
    });

    pointsContainer.appendChild(node);
  });
}

function renderRepetitiveAreas(areas) {
  const container = $('#repetitive-areas-list');
  if (!container) return;

  if (!areas.length) {
    container.innerHTML = '<div class="empty-state">No neighborhood competition data found.</div>';
    return;
  }

  container.innerHTML = areas.slice(0, 6).map(a => `
    <div class="area-item" onclick="selectArea('${esc(a.city)}', '${esc(a.locality)}')">
      <div class="area-meta">
        <strong>${esc(a.locality)}</strong>
        <span class="city-tag">${esc(a.city)}</span>
        <small>${a.restaurant_count} Kitchens | ${a.osm_competitors} Local Places</small>
      </div>
      <div class="area-badge-wrap">
        <span class="sim-pct">${(a.avg_similarity * 100).toFixed(1)}%</span>
        <span class="badge ${a.badge}">${esc(a.status)}</span>
      </div>
    </div>
  `).join('');
}

function selectArea(city, locality) {
  currentCity = city;
  selectedLocation = locality;
  $('#city-filter').value = city;
  toggleResetButton(true);
  renderDashboard();
}

async function fetchOpportunities(city = null, location = null) {
  const container = $('#gaps');
  if (!container) return;

  const query = [];
  if (city && city !== 'all') query.push(`city=${encodeURIComponent(city)}`);
  if (location && location !== 'all') query.push(`location=${encodeURIComponent(location)}`);

  const url = query.length ? `/api/opportunities?${query.join('&')}` : '/api/opportunities';
  try {
    const res = await fetch(url);
    cachedOpportunities = await res.json();
    filterAndDisplayOpportunities();
  } catch (err) {
    console.error(err);
    container.innerHTML = '<div class="empty-state error">Could not load opportunities.</div>';
  }
}

function filterAndDisplayOpportunities() {
  const container = $('#gaps');
  if (!container) return;

  const titleEl = $('#opportunity-title');
  if (titleEl) {
    titleEl.textContent = selectedLocation 
      ? `Less-common dishes in ${selectedLocation}` 
      : (currentCity !== 'all' ? `Less-common dishes in ${currentCity}` : 'Less-common dishes across the market');
  }

  let filtered = cachedOpportunities;

  // Filter by category
  if (selectedCategory === 'community') {
    filtered = filtered.filter(o => o.is_community_wanted);
  } else if (selectedCategory !== 'all') {
    filtered = filtered.filter(o => o.category === selectedCategory);
  }

  // Filter by search query
  if (searchQuery) {
    filtered = filtered.filter(o => o.dish.toLowerCase().includes(searchQuery));
  }

  if (!filtered.length) {
    container.innerHTML = '<div class="empty-state">No matching food opportunities found for this filter.</div>';
    return;
  }

  container.innerHTML = filtered.slice(0, 10).map(o => `
    <div class="gap-card clickable" onclick="testDishInSimulator('${esc(o.dish)}')">
      <div class="gap-header">
        <strong>${esc(o.dish)}</strong>
        <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
          ${o.poll_badge ? `<span class="badge success" style="font-size: 10px;">${esc(o.poll_badge)}</span>` : ''}
          <span class="opp-score">${o.opportunity_score} score</span>
        </div>
      </div>
      <div class="gap-details">
        <span>${esc(o.category)}</span> • 
        <span>Avg ₹${o.avg_price_inr}</span>
      </div>
      <div class="gap-reason">${esc(o.reason)}</div>
    </div>
  `).join('');
}

function testDishInSimulator(dishName) {
  sessionStorage.setItem('prefill_dish', dishName);
  window.location.href = `/simulator?dish=${encodeURIComponent(dishName)}`;
}

function renderComparisonTable(insights) {
  const tbody = $('#pairs-table');
  if (!tbody) return;

  if (!insights.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No similar menus found at this level.</td></tr>';
    return;
  }

  tbody.innerHTML = insights.slice(0, 8).map(item => `
    <tr>
      <td>
        <strong>${esc(item.restaurant_a)}</strong>
        <br><span class="shared">${esc(item.location_a || '')} (${esc(item.cuisine_a)})</span>
      </td>
      <td>
        <strong>${esc(item.restaurant_b)}</strong>
        <br><span class="shared">${esc(item.location_b || '')} (${esc(item.cuisine_b)})</span>
      </td>
      <td>
        <span class="pill">${(item.similarity * 100).toFixed(0)}%</span>
      </td>
      <td class="shared">
        ${Array.isArray(item.shared_items) ? item.shared_items.slice(0, 6).map(esc).join(' • ') : 'Identical menu items'}
      </td>
    </tr>
  `).join('');
}

function setupThresholdListener() {
  const thresholdInput = $('#threshold');
  const thresholdVal = $('#threshold-value');
  if (!thresholdInput) return;

  thresholdInput.addEventListener('input', (e) => {
    const val = Number(e.target.value);
    if (thresholdVal) thresholdVal.textContent = `${Math.round(val * 100)}%`;
    renderDashboard();
  });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initDashboard);
