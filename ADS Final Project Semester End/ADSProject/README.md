# Bitewise

Bitewise is a Flask and SQLite decision-support application for comparing restaurant menus and identifying underserved food opportunities in local markets.

## What the project is made to do

Bitewise answers one practical question:

> **Where do restaurant menus look too similar, and which dishes are less represented in that local market?**

It is designed for a restaurant owner, food-market analyst, or customer who wants
to explore menu supply before doing deeper research. The application:

1. compares restaurant menu text and highlights pairs with similar menus;
2. shows the similarity relationships on a neighbourhood-level map;
3. counts dishes by city and neighbourhood to surface less-common menu items;
4. lets an owner test a proposed menu in a selected market;
5. records simple yes/no interest responses for individual dishes; and
6. gives analysts a separate, clearly labelled benchmark for estimated orders and
   revenue.

The project does **not** identify fraud, prove that two kitchens have the same
owner, guarantee customer demand, or predict future sales with certainty. Menu
similarity is evidence that menu text overlaps; a menu opportunity is a research
lead. The performance model is separate from the similarity and opportunity
systems because the available restaurant-level data is limited and estimated.

### How to use the website

- **Overview:** start here to see the market map, similarity threshold, repeated
  menus, and less-common dishes.
- **How it works:** read the plain-language explanation of every score and
  limitation.
- **Concept test:** choose a city and neighbourhood, enter one proposed dish per
  line, and review the local menu coverage.
- **Owner:** select a city to review possible menu gaps worth researching.
- **Analyst:** inspect city supply and the separate estimated-performance
  benchmark.
- **Customer:** browse less-repeated dishes in a selected city.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

The application opens on the sign-in page. After signing in or creating an
account, visitors are taken to the market overview dashboard.

The application uses the processed restaurant menu file generated from the approved source data. Do not scrape a delivery platform without checking its terms and obtaining permission.

## Project structure

```text
ADSProject/
├── app.py                         # Flask application and routes
├── db.py                          # SQLite schema and data access
├── analysis.py                    # Similarity and opportunity analysis
├── wsgi.py                        # Production WSGI entry point
├── scripts/                       # Data preparation and model commands
│   ├── prepare_zomato_data.py     # Raw menu -> processed menu files
│   ├── prepare_orders_data.py     # Orders ZIP -> performance file
│   ├── train_model.py             # Rebuild TF-IDF artifact and insights
│   └── download_datasets.py       # Optional dataset downloader
├── data/
│   ├── raw/                       # Original, downloaded source files
│   └── processed/                 # Files consumed by the application
├── artifacts/                     # Pickle model artifacts
├── instance/                      # Local SQLite database
├── notebooks/                     # Jupyter exploration
├── templates/                     # Flask HTML templates
├── static/                        # CSS and browser JavaScript
└── tests/                         # Application tests
```

## Project demonstration deployment

The project includes a production WSGI entry point, health check, deployment
start command, prepared data files, and route smoke tests. Install the
requirements and start it with:

```powershell
waitress-serve --listen=0.0.0.0:8000 wsgi:app
```

Then open `http://127.0.0.1:8000`. Set `SECRET_KEY` to a long random value and
keep `FLASK_DEBUG=0` when presenting the project as a production-style build.
The `/health` endpoint returns a small readiness response for a hosting
platform or local demonstration.

Run the smoke tests with:

```powershell
python -m unittest discover -s tests -v
```

Build and benchmark the leakage-safe estimated-orders model:

```powershell
python -m scripts.validate_joins
python -m scripts.benchmark_models
```

This creates `data/processed/model_features.csv`,
`data/processed/join_audit.json`, and
`data/processed/model_validation_report.json`. The benchmark is visible to
analyst and owner accounts at `/api/model-benchmark`. A model is not served as
a demand forecast unless it beats the mean baseline and its limitations remain
visible.

The benchmark also writes separate pickle pipelines to
`artifacts/restaurant_orders_model.pkl` and
`artifacts/restaurant_revenue_model.pkl` when a non-baseline model wins. These
are estimated-performance artifacts and are not connected to the concept
simulator as guaranteed demand predictions.

## Prepare the Zomato menu file

The project can geocode the unique `City + Location` pairs in
`data/raw/cleaned_zomato_menus.csv` using OpenStreetMap Nominatim. This
produces neighbourhood-level coordinates, not exact restaurant coordinates.
Run:

```powershell
python -m scripts.prepare_zomato_data
```

The script creates `data/processed/restaurant_locations.csv`, `data/processed/menu_listings.csv`, and `data/processed/menu_items.csv`, while preserving the original CSV. The item file keeps every raw menu row, including dish, category, price, rating, and price band. It caches successful lookups and waits between requests to respect the public Nominatim service. Review the generated locations before using them for decisions.

The current database has been loaded from the processed files: 200 restaurant records, all 9,866 menu-item records, 25 geocoded neighbourhoods, and 19,900 menu comparisons. The map points represent neighbourhoods because the source names are anonymized and do not include street addresses.

To prepare the added restaurant-performance ZIP, place
`OrdersDatasetZipFile.zip` in the project root or set `ORDERS_ZIP_PATH` to its
absolute path, then run `python -m scripts.prepare_orders_data`.
It creates `data/processed/restaurant_performance.csv` from
`swiggy_vs_zomato_enriched.csv`. The analyst dashboard then shows estimated
orders, revenue, growth, and performance-record counts separately from the
menu-similarity model.

## Replace with new data

Add an approved export at `data/raw/cleaned_zomato_menus.csv` or update the
processing script. The processed application file is
`data/processed/menu_listings.csv`.

`restaurant_name, platform, cuisine, latitude, longitude, menu_items`

Then remove `instance/menus.sqlite3`, run
`python -m scripts.prepare_zomato_data`, and start `python app.py`. The API
endpoint `POST /api/retrain` performs the same model refresh.
`notebooks/menu_analysis.ipynb` contains the exploratory workflow, and
`python -m scripts.train_model` persists the TF-IDF vectorizer to
`artifacts/menu_similarity.pkl`.

## API

- `GET /api/summary` — headline metrics and low-frequency item opportunities
- `GET /api/restaurants` — normalized restaurant records
- `GET /api/insights?min_similarity=0.35` — menu pairs and shared items
- `POST /api/retrain` — rebuild database insights and the pickle model artifact
- `POST /api/dish-interest` — record an area's yes/no response for a proposed dish
- `GET /api/predictions?city=Bangalore` — opportunity predictions for a selected market

## User pages

- `/login` and `/signup` — account authentication and role selection
- `/owner` — kitchen-owner opportunity recommendations
- `/analyst` — market supply and model limitations
- `/simulator` — enter a proposed city, neighbourhood, menu, and price to get a scenario outcome
- `/customer` — discovery view for less-repeated menu items
- `/analysis` — analyst/owner area-wise and dish-wise visual analysis
- `/guide` — plain-language explanation of the project and its limitations

Accounts are stored in SQLite with Werkzeug password hashing. The signup role selector supports `owner`, `analyst`, and `customer`; protected pages and analysis APIs enforce those roles. Set a long random `SECRET_KEY` in `.env` before deployment and add email verification, password reset, and administrator approval for analyst/owner roles.

The simulator accepts `POST /api/predict-concept` with `city`, `location`, `menu_items`, and optional `price`. It returns local menu coverage, competition score, whitespace percentage, opportunity score, an explainable outlook, and any collected interest checks for those dishes. The simulator also lets people submit a yes/no response for one dish and area; the result is empirical feedback, not a forecast.

The current prediction is an opportunity score based on menu rarity and local coverage. Menu similarity uses TF-IDF with unigram/bigram features and cosine similarity, persisted in `artifacts/menu_similarity.pkl`. Dish interest uses a SQLite aggregate of submitted responses. Neither is a demand or sales forecast because the available dataset has no orders, searches, costs, rent, or time-series customer labels. Those fields must be added before training a true future-outcome model.

This is an opportunity signal, not proof of customer demand or misconduct. Add demand, price, rating, and time-series signals before making a commercial decision.
