const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[c]));

let allAreas = [];
let allDishes = [];
let currentCity = "all";
let currentArea = "all";
let currentCategory = "all";
let searchQuery = "";

function initData() {
  const areasEl = document.getElementById("initial-areas");
  const dishesEl = document.getElementById("initial-dishes");

  if (areasEl && dishesEl) {
    try {
      allAreas = JSON.parse(areasEl.textContent || "[]");
      allDishes = JSON.parse(dishesEl.textContent || "[]");
    } catch (e) {
      console.warn("Could not parse embedded JSON, falling back to fetch", e);
    }
  }

  if (!allAreas.length || !allDishes.length) {
    fetchData();
  } else {
    setupUI();
    renderAreas();
    renderDishes();
  }
}

async function fetchData() {
  const areasContainer = document.getElementById("areas-container");
  const dishesContainer = document.getElementById("dishes-container");
  try {
    const [areasRes, dishesRes] = await Promise.all([
      fetch("/api/analysis/areas"),
      fetch("/api/analysis/dishes"),
    ]);
    if (!areasRes.ok || !dishesRes.ok) throw new Error("API request failed");
    allAreas = await areasRes.json();
    allDishes = await dishesRes.json();
    setupUI();
    renderAreas();
    renderDishes();
  } catch (err) {
    console.error("Fetch failed:", err);
    if (areasContainer) {
      areasContainer.innerHTML = `
        <div class="empty-box" style="border-color: #ef765d; text-align: center; padding: 24px;">
          <h4 style="margin: 0 0 6px; color: #d94b36;">Unable to fetch market data</h4>
          <p style="margin: 0 0 12px; font-size: 13px;">${esc(err.message)}</p>
          <button class="filter-pill active" onclick="fetchData()">Retry Loading</button>
        </div>
      `;
    }
  }
}

function setupUI() {
  const cityFilter = document.getElementById("city-filter");
  const dishSearch = document.getElementById("dish-search");
  const categoryPills = document.querySelectorAll("#category-pills .filter-pill");

  if (cityFilter) {
    const cities = [...new Set(allAreas.map((a) => a.city))].sort();
    cityFilter.innerHTML = '<option value="all">All Cities</option>';
    cities.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      cityFilter.appendChild(opt);
    });
    cityFilter.addEventListener("change", (e) => {
      currentCity = e.target.value;
      currentArea = "all";
      renderAreas();
      renderDishes();
    });
  }

  if (dishSearch) {
    dishSearch.addEventListener("input", (e) => {
      searchQuery = e.target.value.trim();
      renderDishes();
    });
  }

  categoryPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      categoryPills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.dataset.cat;
      renderDishes();
    });
  });
}

function renderAreas() {
  const areasContainer = document.getElementById("areas-container");
  const areaCountLabel = document.getElementById("area-count-label");
  if (!areasContainer) return;

  let filtered = allAreas;
  if (currentCity !== "all") {
    filtered = filtered.filter(
      (a) => a.city.toLowerCase() === currentCity.toLowerCase()
    );
  }

  if (areaCountLabel) {
    areaCountLabel.textContent = `${filtered.length} delivery areas`;
  }

  if (!filtered.length) {
    areasContainer.innerHTML = `
      <div style="text-align: center; padding: 30px 10px; color: var(--muted); font-size: 13px;">
        No neighborhood records match your selected city.
      </div>
    `;
    return;
  }

  areasContainer.innerHTML = filtered
    .map((item) => {
      const topDishesHtml = (item.top_dishes || [])
        .slice(0, 3)
        .map(
          (td) =>
            `<span style="font-size: 10px; background: #fdf5ec; border: 1px solid #fae6d3; padding: 2px 6px; border-radius: 6px; color: var(--ink);">${esc(td.dish)} (${td.restaurants})</span>`
        )
        .join("");

      const isSelected = currentArea.toLowerCase() === item.area.toLowerCase();
      const selectedStyle = isSelected ? "border-color: var(--primary); background: var(--primary-light);" : "";

      return `
        <div
          class="area-item"
          style="${selectedStyle}"
          onclick="filterDishesByArea('${esc(item.city)}', '${esc(item.area)}')"
          title="Click to view dishes in ${esc(item.area)}"
        >
          <div class="area-meta">
            <strong>${esc(item.area)}</strong>
            <span class="city-tag">${esc(item.city)}</span>
            <small>${item.restaurants || 8} tracked kitchens &middot; ${item.osm_competitors || 25} local food places &middot; ₹${Math.round(item.avg_price_inr || 220)} avg dish</small>
            <div style="margin-top: 6px; display: flex; gap: 4px; flex-wrap: wrap;">
              ${topDishesHtml || '<span style="font-size:10px; color:var(--muted);">Balanced selection</span>'}
            </div>
          </div>
          <div class="area-badge-wrap">
            <span class="sim-pct">${Math.round((item.avg_similarity || 0) * 100)}%</span>
            <span class="badge ${esc(item.badge || 'warning')}">${esc(item.status || 'Moderate Overlap')}</span>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderDishes() {
  const dishesContainer = document.getElementById("dishes-container");
  const dishCountLabel = document.getElementById("dish-count-label");
  const dishPanelTitle = document.getElementById("dish-panel-title");
  if (!dishesContainer) return;

  if (dishPanelTitle) {
    if (currentArea !== "all") {
      dishPanelTitle.innerHTML = `Common Dishes &amp; Food Opportunities in <span>${esc(currentArea)}</span> <button onclick="resetAreaFilter()" style="font-size: 11px; padding: 2px 8px; border-radius: 6px; border: 1px solid var(--line); background: #fff; cursor: pointer; color: var(--muted); vertical-align: middle; margin-left: 6px;">Reset ✕</button>`;
    } else {
      dishPanelTitle.textContent = "Common Dishes & Food Opportunities";
    }
  }

  let filtered = allDishes;

  if (currentCategory !== "all") {
    if (currentCategory === "community") {
      filtered = filtered.filter((d) => Boolean(d.poll_badge) || Boolean(d.is_community_wanted));
    } else {
      filtered = filtered.filter(
        (d) => (d.category || "").toLowerCase() === currentCategory.toLowerCase()
      );
    }
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter((d) => (d.dish || "").toLowerCase().includes(q));
  }

  if (dishCountLabel) {
    dishCountLabel.textContent = `${filtered.length} dishes`;
  }

  if (!filtered.length) {
    dishesContainer.innerHTML = `
      <div style="text-align: center; padding: 40px 10px; color: var(--muted); font-size: 13px;">
        No dishes match "<strong>${esc(searchQuery)}</strong>" in the selected category.
      </div>
    `;
    return;
  }

  dishesContainer.innerHTML = filtered
    .map((item) => {
      const covPct = item.coverage_pct ?? Math.round((item.coverage || 0) * 100);
      const totalR = item.total_restaurants || 200;
      const countR = item.restaurants || 0;
      const price = Math.round(item.avg_price_inr || 220);

      const targetCity = currentCity !== "all" ? currentCity : "Bangalore";
      const targetLoc = currentArea !== "all" ? currentArea : "Koramangala";
      const simUrl = `/simulator?city=${encodeURIComponent(targetCity)}&location=${encodeURIComponent(targetLoc)}&dish=${encodeURIComponent(item.dish)}`;

      return `
        <div class="gap-card clickable" onclick="location.href='${simUrl}'" title="Click to test in simulator">
          <div class="gap-header">
            <strong>${esc(item.dish)}</strong>
            <div style="display: flex; gap: 4px; align-items: center; flex-wrap: wrap;">
              ${item.poll_badge ? `<span class="badge success" style="font-size: 10px; background: #eaf6ee; color: #2e7d32; border: 1px solid #c8e6c9;">${esc(item.poll_badge)}</span>` : ''}
              <span class="badge ${esc(item.badge || 'warning')}">${esc(item.status || 'Moderate Competition')}</span>
            </div>
          </div>
          <div class="gap-details">
            <span>${esc(item.category || 'Main Course')} &middot; ₹${price} avg</span> &middot;
            <span style="font-weight: 700; color: var(--ink);">${covPct}% presence (${countR}/${totalR} kitchens)</span>
          </div>
          <div class="dish-sat-bar-wrap" style="margin: 8px 0 6px;">
            <div class="sat-bar-bg" style="height: 6px;">
              <div class="sat-bar-fill ${esc(item.badge || 'warning')}" style="width: ${Math.min(100, Math.max(5, covPct))}%"></div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
            <span class="gap-reason" style="margin: 0;">${(item.status === 'Market Whitespace' || item.status === 'High-Demand Gap') ? 'Less-common dish' : 'Common dish'}</span>
            <a href="${simUrl}" class="button-link" style="margin: 0; font-size: 11px;">Test in Simulator &rarr;</a>
          </div>
        </div>
      `;
    })
    .join("");
}

window.filterDishesByArea = async function (city, area) {
  currentCity = city;
  currentArea = area;
  const cityFilter = document.getElementById("city-filter");
  if (cityFilter) cityFilter.value = city;

  renderAreas();

  // Fetch dishes specific to this locality
  const dishesContainer = document.getElementById("dishes-container");
  if (dishesContainer) {
    dishesContainer.innerHTML = `<div style="text-align: center; padding: 30px 10px; color: var(--muted); font-size: 13px;">Loading dishes in ${esc(area)}, ${esc(city)}...</div>`;
  }

  try {
    const res = await fetch(`/api/analysis/dishes?city=${encodeURIComponent(city)}&area=${encodeURIComponent(area)}`);
    if (res.ok) {
      allDishes = await res.json();
    }
  } catch (e) {
    console.error(e);
  }
  renderDishes();
};

window.resetAreaFilter = async function () {
  currentArea = "all";
  renderAreas();
  const dishesContainer = document.getElementById("dishes-container");
  if (dishesContainer) {
    dishesContainer.innerHTML = '<div style="text-align: center; padding: 30px 10px; color: var(--muted); font-size: 13px;">Loading all dishes...</div>';
  }
  try {
    const url = currentCity !== "all" ? `/api/analysis/dishes?city=${encodeURIComponent(currentCity)}` : "/api/analysis/dishes";
    const res = await fetch(url);
    if (res.ok) {
      allDishes = await res.json();
    }
  } catch (e) {
    console.error(e);
  }
  renderDishes();
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initData);
} else {
  initData();
}
