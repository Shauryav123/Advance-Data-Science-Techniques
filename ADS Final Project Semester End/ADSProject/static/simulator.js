const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[char]));

const citySelect = $('#city');
const locationSelect = $('#location');
const resultContainer = $('#result');
const simulatorForm = $('#simulator-form');
const interestForm = $('#interest-form');
const interestDish = $('#interest-dish');
const interestResult = $('#interest-result');
const notInterestedBtn = $('#not-interested');

let restaurants = [];

async function setup() {
  try {
    const res = await fetch('/api/restaurants');
    if (!res.ok) throw new Error('Could not load restaurant database.');
    restaurants = await res.json();

    const cities = [...new Set(restaurants.map((row) => row.city).filter(Boolean))].sort();
    citySelect.innerHTML = cities.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join('');
    
    citySelect.addEventListener('change', () => {
      updateLocations();
      loadCommunityPolls();
    });
    locationSelect.addEventListener('change', loadCommunityPolls);

    // Check for prefilled city, location, and dish from URL params or sessionStorage
    const urlParams = new URLSearchParams(window.location.search);
    const prefillCity = urlParams.get('city');
    const prefillLoc = urlParams.get('location');
    if (prefillCity && cities.includes(prefillCity)) {
      citySelect.value = prefillCity;
    }
    updateLocations();
    if (prefillLoc) {
      locationSelect.value = prefillLoc;
    }
    loadCommunityPolls();

    const prefillDish = urlParams.get('dish') || sessionStorage.getItem('prefill_dish');
    if (prefillDish) {
      const menuInput = $('#menu-items');
      if (menuInput) menuInput.value = prefillDish;
      if (interestDish) interestDish.value = prefillDish;
      sessionStorage.removeItem('prefill_dish');
    }
  } catch (err) {
    console.error(err);
    if (resultContainer) {
      resultContainer.innerHTML = `<p class="error">Failed to load cities: ${esc(err.message)}</p>`;
    }
  }
}

function updateLocations() {
  const currentCity = citySelect.value;
  const locations = [...new Set(
    restaurants
      .filter((row) => row.city && row.city.toLowerCase() === currentCity.toLowerCase())
      .map((row) => row.location)
      .filter(Boolean)
  )].sort();

  locationSelect.innerHTML = locations.map((loc) => `<option value="${esc(loc)}">${esc(loc)}</option>`).join('');
}

// Concept test prediction form submission
simulatorForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  
  const menuLines = $('#menu-items').value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);

  if (!menuLines.length) {
    resultContainer.innerHTML = '<p class="error">Please enter at least one dish name in the menu box.</p>';
    return;
  }

  resultContainer.innerHTML = `
    <p class="eyebrow">PREDICTION RESULTS</p>
    <h2>Evaluating Neighborhood Menu…</h2>
    <p class="panel-copy">Checking proposed dishes against local competitor menus…</p>
  `;

  const payload = {
    city: citySelect.value,
    location: locationSelect.value,
    menu_items: menuLines,
    price: Number($('#price').value) || null,
  };

  try {
    const res = await fetch('/api/predict-concept', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      resultContainer.innerHTML = `<p class="error">${esc(data.error || 'Menu simulation failed.')}</p>`;
      return;
    }

    const rareList = Array.isArray(data.rare_items) && data.rare_items.length
      ? data.rare_items.map(esc).join(', ')
      : 'None (all submitted items are already common)';

    const commonList = Array.isArray(data.common_items) && data.common_items.length
      ? data.common_items.map(esc).join(', ')
      : 'None (your menu is entirely unique)';

    // Typo corrections & novel dish notices
    let resolutionHtml = '';
    if (Array.isArray(data.typo_corrections) && data.typo_corrections.length) {
      resolutionHtml += `
        <div style="margin-bottom: 8px; font-size: 12px; color: #92400e; background: #fffbeb; border: 1px solid #fde68a; padding: 8px 12px; border-radius: 4px;">
          <strong>Spelling Auto-Corrected:</strong> ${data.typo_corrections.map((c) => `<em>"${esc(c.original)}"</em> &rarr; <b>${esc(c.dish)}</b> (${Math.round((c.confidence || 0) * 100)}% match)`).join(' · ')}
        </div>
      `;
    }
    if (Array.isArray(data.novel_dishes) && data.novel_dishes.length) {
      resolutionHtml += `
        <div style="margin-bottom: 8px; font-size: 12px; color: #166534; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 8px 12px; border-radius: 4px;">
          <strong>Unique Dish:</strong> ${data.novel_dishes.map((n) => `<b>${esc(n.dish)}</b> (No local competitors currently serve this &mdash; Great Opportunity)`).join(' · ')}
        </div>
      `;
    }

    // Price positioning & benchmark
    let priceHtml = '';
    if (data.price_analysis) {
      const pa = data.price_analysis;
      const diffSign = pa.difference_pct > 0 ? `+${pa.difference_pct}%` : `${pa.difference_pct}%`;
      priceHtml = `
        <div style="margin-top: 12px; padding: 12px 14px; background: var(--surface-subtle); border: 1px solid var(--border); border-radius: 4px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 12px; font-weight: 600; color: var(--text-primary);">Price Level: ${esc(pa.price_tier)}</span>
            <span class="badge ${pa.difference_pct < -15 ? 'success' : pa.difference_pct > 15 ? 'warning' : 'success'}">${esc(diffSign)} vs Neighborhood Average</span>
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4;">
            Your planned price of ₹${pa.proposed_price} vs <b>₹${pa.locality_avg_price}</b> neighborhood average. <em>${esc(pa.positioning)}</em>
          </div>
        </div>
      `;
    }

    // Performance Prediction
    let mlHtml = '';
    if (data.ml_performance_prediction) {
      const ml = data.ml_performance_prediction;
      const sensRows = (ml.sensitivity_analysis || [])
        .map(
          (s) => `
            <tr>
              <td style="padding: 5px 8px; border-bottom: 1px solid var(--border); font-size: 11px;">${esc(s.scenario)} (₹${s.price})</td>
              <td style="padding: 5px 8px; border-bottom: 1px solid var(--border); font-size: 11px; text-align: right; font-family: var(--font-mono); font-weight: 600;">${Number(s.estimated_orders).toLocaleString()}</td>
              <td style="padding: 5px 8px; border-bottom: 1px solid var(--border); font-size: 11px; text-align: right; font-family: var(--font-mono); font-weight: 600; color: var(--success);">₹${Number(s.estimated_revenue).toLocaleString()}</td>
            </tr>
          `
        )
        .join('');

      mlHtml = `
        <div style="margin-top: 14px; padding: 12px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 4px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <h4 style="margin: 0; font-size: 13px; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.04em;">Sales & Revenue Estimate</h4>
            <span class="badge success">Estimated benchmark</span>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
            <div style="background: var(--surface-subtle); padding: 8px 10px; border-radius: 4px; text-align: center;">
              <div style="font-family: var(--font-mono); font-size: 18px; font-weight: 700; color: var(--primary);">${Number(ml.estimated_monthly_orders).toLocaleString()}</div>
              <div style="font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Estimated monthly orders</div>
            </div>
            <div style="background: var(--surface-subtle); padding: 8px 10px; border-radius: 4px; text-align: center;">
              <div style="font-family: var(--font-mono); font-size: 18px; font-weight: 700; color: var(--success);">₹${Number(ml.estimated_monthly_revenue_inr).toLocaleString()}</div>
              <div style="font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Estimated monthly revenue</div>
            </div>
          </div>

          <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Price comparison examples:</div>
          <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
              <tr style="color: var(--text-muted); text-align: left;">
                <th style="padding: 4px 8px;">Pricing Scenario</th>
                <th style="padding: 4px 8px; text-align: right;">Estimated Orders</th>
                <th style="padding: 4px 8px; text-align: right;">Estimated Revenue</th>
              </tr>
            </thead>
            <tbody>
              ${sensRows}
            </tbody>
          </table>
        </div>
      `;
    }

    // Community Poll Matches
    let pollMatchesHtml = '';
    if (Array.isArray(data.community_poll_matches) && data.community_poll_matches.length) {
      pollMatchesHtml = `
        <div style="margin-bottom: 10px; padding: 10px 12px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 4px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            <strong style="color: #065f46; font-size: 12px;">Customer Demand Verified</strong>
            <span class="badge success">High Demand</span>
          </div>
          <div style="font-size: 12px; color: #047857; line-height: 1.4;">
            ${data.community_poll_matches.map((m) => `• <b>${esc(m.dish)}</b>: ${esc(m.note)}`).join('<br>')}
          </div>
        </div>
      `;
    }

    const limitationsText = Array.isArray(data.limitations)
      ? data.limitations.map(esc).join(' ')
      : 'This is an estimated neighborhood assessment to guide your menu planning.';

    resultContainer.innerHTML = `
      <p class="eyebrow">SIMULATION RESULTS</p>
      <h2 style="font-size: 18px; margin: 0 0 10px;">${esc(data.outlook)}</h2>

      ${resolutionHtml}
      ${pollMatchesHtml}
      
      <div class="prediction-score">
        <strong>${data.opportunity_score}</strong>
        <span>OPPORTUNITY SCORE / 99</span>
      </div>

      <div class="result-metrics">
        <div>
          <b>${data.competition_score}%</b>
          <span>MENU SIMILARITY</span>
        </div>
        <div>
          <b>${data.menu_whitespace}%</b>
          <span>LESS-COMMON DISHES</span>
        </div>
        <div>
          <b>${data.market_restaurants}</b>
          <span>${esc((data.market_scope || 'area').toUpperCase())} KITCHENS</span>
        </div>
      </div>

      ${priceHtml}

      ${mlHtml}

      <div style="margin-top: 14px; padding: 12px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 4px;">
        <h4 style="margin: 0 0 6px; font-size: 13px; font-weight: 600; color: var(--text-primary);">Item Breakdown for ${esc(data.location)}, ${esc(data.city)}:</h4>
        <p style="margin: 0 0 4px; font-size: 12px; line-height: 1.4; color: var(--success);">
          <strong>Less-common items:</strong> ${rareList}
        </p>
        <p style="margin: 0; font-size: 12px; line-height: 1.4; color: var(--danger);">
          <strong>Common in this area:</strong> ${commonList}
        </p>
      </div>

      <p class="panel-copy" style="font-size: 11px; margin-top: 10px; color: var(--text-muted);">${limitationsText}</p>
    `;
  } catch (err) {
    console.error(err);
    resultContainer.innerHTML = `<p class="error">Network error: ${esc(err.message)}</p>`;
  }
});

// "Would you rather try this dish?" customer sentiment survey
async function submitInterest(interested) {
  const dish = interestDish.value.trim();
  const city = citySelect.value;
  const location = locationSelect.value;

  if (!dish) {
    interestResult.className = 'error';
    interestResult.textContent = 'Please type a dish name first (e.g. Tandoori Momos, Avocado Toast).';
    return;
  }

  interestResult.className = 'panel-copy';
  interestResult.textContent = 'Recording response in database…';

  try {
    const res = await fetch('/api/dish-interest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dish: dish,
        city: city,
        location: location,
        interested: Boolean(interested),
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      interestResult.className = 'error';
      interestResult.textContent = data.error || 'Failed to record response.';
      return;
    }

    interestResult.className = 'panel-copy';
    const total = data.responses || 1;
    const pos = data.interested || 0;
    const neg = data.not_interested || 0;
    const approvalRate = Math.round((pos / total) * 100);

    interestResult.innerHTML = `
      <div style="margin-top: 10px; padding: 12px 16px; background: #f0fbf3; border: 1px solid #c2ebd0; border-radius: 12px;">
        <strong style="color: #1e4620;">Feedback recorded for "${esc(data.dish)}" in ${esc(data.location)}, ${esc(data.city)}:</strong>
        <div style="margin-top: 4px; font-size: 13px; color: var(--ink);">
          <span style="color: #2e7d32; font-weight: 700;">${pos} would try it</span> • 
          <span style="color: #c62828; font-weight: 700;">${neg} not for them</span> • 
          <span>${approvalRate}% local approval (${total} total votes)</span>
        </div>
      </div>
    `;

    // Immediately refresh community poll list to show updated demand
    loadCommunityPolls();
  } catch (err) {
    console.error(err);
    interestResult.className = 'error';
    interestResult.textContent = `Error: ${err.message}`;
  }
}

async function loadCommunityPolls() {
  const pollList = $('#community-poll-list');
  const pollAreaName = $('#poll-area-name');
  if (!pollList) return;

  const city = citySelect.value;
  const location = locationSelect.value;
  if (pollAreaName) {
    pollAreaName.textContent = location ? `${location}, ${city}` : city;
  }

  try {
    const url = `/api/dish-interest?city=${encodeURIComponent(city)}&location=${encodeURIComponent(location)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Could not load poll demand.');
    const polls = await res.json();

    if (!Array.isArray(polls) || !polls.length) {
      pollList.innerHTML = `
        <div style="font-size: 12px; color: var(--muted); padding: 10px 14px; background: #fffaf7; border: 1px dashed var(--line); border-radius: 10px; text-align: center;">
          No customer poll votes recorded yet in ${esc(location)}. Vote above to share what dishes you want!
        </div>
      `;
      return;
    }

    pollList.innerHTML = polls.slice(0, 5).map((p) => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 9px 12px; background: #fff; border: 1px solid var(--line); border-radius: 10px; gap: 8px;">
        <div style="display: flex; flex-direction: column; cursor: pointer; flex-grow: 1;" onclick="addDishToMenu('${esc(p.dish)}')">
          <strong style="font-size: 13px; color: var(--ink);">${esc(p.dish)}</strong>
          <span style="font-size: 11px; color: var(--muted);">${p.interested} would try &middot; ${p.not_interested} not for them</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="badge ${p.approval_pct >= 75 ? 'success' : 'warning'}" style="font-size: 11px;">${p.approval_pct}% approval</span>
          <button type="button" class="button-link" style="font-size: 11px; margin: 0; padding: 3px 8px; font-weight: 600;" onclick="addDishToMenu('${esc(p.dish)}')">+ Add to Menu</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
    pollList.innerHTML = '<p style="font-size: 12px; color: var(--muted); margin: 0;">Could not load customer polls.</p>';
  }
}

window.addDishToMenu = function(dishName) {
  const menuInput = $('#menu-items');
  if (menuInput) {
    const currentLines = menuInput.value.split('\n').map((s) => s.trim()).filter(Boolean);
    if (!currentLines.includes(dishName)) {
      currentLines.push(dishName);
      menuInput.value = currentLines.join('\n');
    }
  }
  if (interestDish) {
    interestDish.value = dishName;
  }
};

interestForm.addEventListener('submit', (e) => {
  e.preventDefault();
  submitInterest(true);
});

if (notInterestedBtn) {
  notInterestedBtn.addEventListener('click', (e) => {
    e.preventDefault();
    submitInterest(false);
  });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', setup);
