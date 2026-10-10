const customerCity = document.querySelector('#city');
async function customerLoad() {
  const profile = await (await fetch('/api/predictions')).json();
  customerCity.innerHTML = profile.cities.map((city) => `<option>${city}</option>`).join('');
  const update = async () => {
    const data = await (await fetch(`/api/predictions?city=${encodeURIComponent(customerCity.value)}`)).json();
    document.querySelector('#recommendations').innerHTML = data.opportunities.map((item) => `<article class="opportunity-card"><span class="eyebrow">LESS COMMON</span><h3>${item.item}</h3><p>Found on only ${item.restaurant_count} nearby menu${item.restaurant_count === 1 ? '' : 's'}.</p></article>`).join('');
  };
  customerCity.addEventListener('change', update); update();
}
customerLoad();
