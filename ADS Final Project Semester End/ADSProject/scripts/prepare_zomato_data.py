from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "cleaned_zomato_menus.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
LOCATIONS_PATH = PROCESSED_DIR / "restaurant_locations.csv"
MENUS_PATH = PROCESSED_DIR / "menu_listings.csv"
ITEMS_PATH = PROCESSED_DIR / "menu_items.csv"
USER_AGENT = "MenuMirror/1.0 (local research application)"


def geocode(city: str, location: str) -> dict[str, str]:
    query = f"{location}, {city}, India"
    params = urlencode({"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1})
    request = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
    )
    with urlopen(request, timeout=30) as response:
        results = json.loads(response.read().decode("utf-8"))
    if not results:
        raise LookupError(f"No geocoding result for {query}")
    result = results[0]
    return {
        "latitude": result["lat"],
        "longitude": result["lon"],
        "display_name": result.get("display_name", ""),
    }


def create_location_file(frame: pd.DataFrame) -> pd.DataFrame:
    areas = frame[["City", "Location"]].drop_duplicates().sort_values(["City", "Location"])
    existing: dict[tuple[str, str], dict[str, str]] = {}
    if LOCATIONS_PATH.exists():
        cached = pd.read_csv(LOCATIONS_PATH).fillna("")
        existing = {
            (row["city"], row["location"]): row.to_dict()
            for _, row in cached.iterrows()
        }

    records = []
    for _, area in areas.iterrows():
        city, location = str(area["City"]), str(area["Location"])
        cached = existing.get((city, location))
        if cached and cached.get("latitude") and cached.get("longitude"):
            records.append(cached)
            continue
        result = geocode(city, location)
        records.append(
            {
                "city": city,
                "location": location,
                **result,
                "geocode_source": "OpenStreetMap Nominatim",
                "geocode_confidence": "neighbourhood",
            }
        )
        time.sleep(1.1)

    locations = pd.DataFrame(records)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    locations.to_csv(LOCATIONS_PATH, index=False, quoting=csv.QUOTE_MINIMAL)
    return locations


def create_menu_file(frame: pd.DataFrame, locations: pd.DataFrame) -> None:
    location_columns = locations[["city", "location", "latitude", "longitude"]]
    frame = frame.copy()
    frame["area_key"] = frame["City"].astype(str) + "|" + frame["Location"].astype(str)
    grouped = (
        frame.groupby("Restaurant Name", as_index=False)
        .agg(
            menu_items=("Dish Name", lambda values: "; ".join(dict.fromkeys(map(str, values)))),
            cuisine=("Category", lambda values: " / ".join(sorted(set(map(str, values))))),
            area_key=("area_key", lambda values: values.mode().iat[0]),
        )
    )
    grouped[["city", "location"]] = grouped["area_key"].str.split("|", n=1, expand=True)
    grouped = grouped.drop(columns=["area_key"])
    grouped = grouped.merge(
        location_columns,
        on=["city", "location"],
        how="left",
        validate="many_to_one",
    )
    output = grouped.rename(
        columns={
            "Restaurant Name": "restaurant_name",
        }
    )
    output.insert(1, "platform", "Zomato dataset")
    output[
        [
            "restaurant_name",
            "platform",
            "cuisine",
            "city",
            "location",
            "latitude",
            "longitude",
            "menu_items",
        ]
    ].to_csv(MENUS_PATH, index=False)
    item_output = frame.rename(
        columns={
            "Restaurant Name": "restaurant_name",
            "Dish Name": "dish_name",
            "Category": "category",
            "Price (INR)": "price_inr",
            "Rating": "rating",
            "Rating Count": "rating_count",
            "Price_Band": "price_band",
        }
    ).merge(
        location_columns,
        left_on=["City", "Location"],
        right_on=["city", "location"],
        how="left",
        validate="many_to_one",
    )
    item_output["platform"] = "Zomato dataset"
    item_output[
        [
            "restaurant_name",
            "platform",
            "City",
            "Location",
            "latitude",
            "longitude",
            "dish_name",
            "category",
            "price_inr",
            "rating",
            "rating_count",
            "price_band",
        ]
    ].rename(columns={"City": "city", "Location": "location"}).to_csv(
        ITEMS_PATH, index=False
    )


def main() -> None:
    frame = pd.read_csv(RAW_PATH)
    locations = create_location_file(frame)
    create_menu_file(frame, locations)
    print(f"Created {LOCATIONS_PATH} ({len(locations)} areas)")
    print(f"Created {MENUS_PATH} ({frame['Restaurant Name'].nunique()} restaurants)")
    print(f"Created {ITEMS_PATH} ({len(frame)} menu items)")


if __name__ == "__main__":
    main()
