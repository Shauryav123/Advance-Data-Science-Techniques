from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUTPUT = PROCESSED / "model_features.csv"
AUDIT_OUTPUT = PROCESSED / "join_audit.json"

CITY_ALIASES = {
    "bengaluru": "bangalore",
    "bangalore": "bangalore",
    "delhi": "new delhi",
    "new delhi": "new delhi",
    "mumbai": "mumbai",
    "bombay": "mumbai",
    "chennai": "chennai",
    "madras": "chennai",
    "pune": "pune",
    "poona": "pune",
}


def normalize(value: object) -> str:
    text = "" if pd.isna(value) else str(value).lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text)).strip()


def normalize_city(value: object) -> str:
    return CITY_ALIASES.get(normalize(value), normalize(value))


def require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    performance = pd.read_csv(PROCESSED / "restaurant_performance.csv")
    menu = pd.read_csv(PROCESSED / "menu_items.csv")
    density = pd.read_csv(PROCESSED / "osm_restaurant_density.csv")
    census = pd.read_csv(PROCESSED / "census_city_population.csv")
    require_columns(
        performance,
        [
            "restaurant_id", "restaurant_name", "city", "locality",
            "restaurant_type", "cuisines", "average_rating_both_platforms",
            "avg_cost_per_person_inr", "price_category",
            "swiggy_avg_delivery_time_minutes",
            "zomato_avg_delivery_time_minutes", "avg_prep_time_minutes",
            "swiggy_estimated_monthly_orders",
            "zomato_estimated_monthly_orders",
            "swiggy_estimated_monthly_revenue_inr",
            "zomato_estimated_monthly_revenue_inr",
        ],
        "restaurant_performance.csv",
    )
    require_columns(
        menu,
        ["restaurant_name", "city", "location", "dish_name", "category", "price_inr"],
        "menu_items.csv",
    )
    require_columns(density, ["city_normalized", "locality", "restaurant_count"], "osm_restaurant_density.csv")
    require_columns(census, ["city", "population_total", "population_urban", "literates_total"], "census_city_population.csv")
    return performance, menu, density, census


def build_features() -> tuple[pd.DataFrame, dict]:
    performance, menu, density, census = load_inputs()
    for frame, city_column in (
        (performance, "city"), (menu, "city"), (density, "city_normalized"), (census, "city")
    ):
        frame["city_norm"] = frame[city_column].map(normalize_city)
    performance["locality_norm"] = performance["locality"].map(normalize)
    performance["name_norm"] = performance["restaurant_name"].map(normalize)
    menu["locality_norm"] = menu["location"].map(normalize)
    menu["name_norm"] = menu["restaurant_name"].map(normalize)
    density["locality_norm"] = density["locality"].map(normalize)

    menu_agg = (
        menu.groupby(["name_norm", "city_norm", "locality_norm"], as_index=False)
        .agg(
            menu_item_count=("dish_name", "count"),
            menu_avg_price=("price_inr", "mean"),
            menu_median_price=("price_inr", "median"),
            menu_min_price=("price_inr", "min"),
            menu_max_price=("price_inr", "max"),
            menu_category_count=("category", "nunique"),
        )
    )
    density_join = density[["city_norm", "locality_norm", "restaurant_count"]].rename(
        columns={"restaurant_count": "locality_competitor_density"}
    )
    census_join = census[["city_norm", "population_total", "population_urban", "literates_total"]].drop_duplicates("city_norm")

    base = performance.copy()
    base["name_norm"] = base["restaurant_name"].map(normalize)
    base["locality_norm"] = base["locality"].map(normalize)
    base["monthly_orders"] = (
        pd.to_numeric(base["swiggy_estimated_monthly_orders"], errors="coerce")
        + pd.to_numeric(base["zomato_estimated_monthly_orders"], errors="coerce")
    )
    base["monthly_revenue_inr"] = (
        pd.to_numeric(base["swiggy_estimated_monthly_revenue_inr"], errors="coerce")
        + pd.to_numeric(base["zomato_estimated_monthly_revenue_inr"], errors="coerce")
    )
    result = base.merge(menu_agg, on=["name_norm", "city_norm", "locality_norm"], how="left", validate="one_to_one")
    result = result.merge(density_join, on=["city_norm", "locality_norm"], how="left", validate="many_to_one")
    result = result.merge(census_join, on="city_norm", how="left", validate="many_to_one")
    result["average_rating"] = pd.to_numeric(result["average_rating_both_platforms"], errors="coerce")
    result["average_cost_inr"] = pd.to_numeric(result["avg_cost_per_person_inr"], errors="coerce")
    result["avg_delivery_time"] = result[["swiggy_avg_delivery_time_minutes", "zomato_avg_delivery_time_minutes"]].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    result["preparation_minutes"] = pd.to_numeric(result["avg_prep_time_minutes"], errors="coerce")
    result["num_cuisines"] = result["cuisines"].fillna("").map(lambda value: len([x for x in re.split(r"[,/]", str(value)) if x.strip()]))
    result["is_cloud_kitchen"] = result["restaurant_type"].fillna("").str.contains("cloud", case=False).astype(int)
    result["price_category_encoded"] = result["price_category"].map({"Budget": 1, "Mid-Range": 2, "Premium": 3}).fillna(2)
    result["prep_to_delivery_ratio"] = result["preparation_minutes"] / result["avg_delivery_time"].replace(0, pd.NA)
    result["prep_to_delivery_ratio"] = result["prep_to_delivery_ratio"].astype("float64")

    output_columns = [
        "restaurant_id", "restaurant_name", "city", "locality", "restaurant_type",
        "cuisines", "price_category", "average_rating", "average_cost_inr",
        "avg_delivery_time", "preparation_minutes", "num_cuisines", "is_cloud_kitchen",
        "price_category_encoded", "prep_to_delivery_ratio", "menu_item_count",
        "menu_avg_price", "menu_median_price", "menu_min_price", "menu_max_price",
        "menu_category_count", "locality_competitor_density", "population_total",
        "population_urban", "literates_total", "monthly_orders", "monthly_revenue_inr",
    ]
    result[output_columns].to_csv(OUTPUT, index=False)
    audit = {
        "performance_rows": int(len(performance)),
        "menu_groups": int(len(menu_agg)),
        "menu_matched_rows": int(result["menu_item_count"].notna().sum()),
        "menu_unmatched_rows": int(result["menu_item_count"].isna().sum()),
        "density_matched_rows": int(result["locality_competitor_density"].notna().sum()),
        "density_unmatched_rows": int(result["locality_competitor_density"].isna().sum()),
        "census_matched_rows": int(result["population_total"].notna().sum()),
        "census_unmatched_rows": int(result["population_total"].isna().sum()),
        "duplicate_model_restaurant_ids": int(result["restaurant_id"].duplicated().sum()),
        "missing_feature_cells": int(result[output_columns].isna().sum().sum()),
    }
    AUDIT_OUTPUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return result, audit


if __name__ == "__main__":
    frame, audit = build_features()
    print(f"Created {OUTPUT} with {len(frame)} rows.")
    print(json.dumps(audit, indent=2))
