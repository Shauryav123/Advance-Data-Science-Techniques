const ownerCity = document.querySelector('#city');
async function ownerLoad() {
  const profile = await (await fetch('/api/predictions')).json();
  ownerCity.innerHTML = profile.cities.map((city) => `<option>${city}</option>`).join('');
  const update = async () => {
    const data = await (await fetch(`/api/predictions?city=${encodeURIComponent(ownerCity.value)}`)).json();
    const opportunities = data.opportunities;
    document.querySelector('#market-size').textContent = data.market_size;
    document.querySelector('#top-item').textContent = opportunities[0]?.item || 'No opportunity';
    document.querySelector('#top-score').textContent = opportunities[0] ? `Research score ${opportunities[0].opportunity_score}/99` : 'No less-common dish found';
    document.querySelector('#opportunities').innerHTML = opportunities.map((item) => `<article class="opportunity-card"><span class="score">${item.opportunity_score}</span><h3>${item.item}</h3><p>${item.restaurant_count} local menu${item.restaurant_count === 1 ? '' : 's'} · ${item.reason}</p></article>`).join('');
  };
  ownerCity.addEventListener('change', update); update();
}
ownerLoad();
