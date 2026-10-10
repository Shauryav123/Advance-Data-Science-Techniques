from __future__ import annotations

import csv
import os
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = Path(os.environ.get("ORDERS_ZIP_PATH", ROOT / "OrdersDatasetZipFile.zip"))
if not ZIP_PATH.is_absolute():
    ZIP_PATH = ROOT / ZIP_PATH
OUTPUT_PATH = ROOT / "data" / "processed" / "restaurant_performance.csv"
SOURCE_NAME = "swiggy_vs_zomato_enriched.csv"

OUTPUT_COLUMNS = [
    "restaurant_id",
    "restaurant_name",
    "city",
    "locality",
    "latitude",
    "longitude",
    "restaurant_type",
    "cuisines",
    "top_selling_dish",
    "average_rating_both_platforms",
    "customer_sentiment_score",
    "avg_cost_per_person_inr",
    "price_category",
    "swiggy_avg_delivery_time_minutes",
    "zomato_avg_delivery_time_minutes",
    "avg_prep_time_minutes",
    "swiggy_estimated_monthly_orders",
    "zomato_estimated_monthly_orders",
    "monthly_order_growth_pct",
    "weekend_order_uplift_pct",
    "repeat_customer_pct",
    "online_order_share_pct",
    "swiggy_estimated_monthly_revenue_inr",
    "zomato_estimated_monthly_revenue_inr",
    "swiggy_estimated_net_profit_inr",
    "zomato_estimated_net_profit_inr",
    "listing_date",
]


def main() -> None:
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Orders ZIP was not found at {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        with archive.open(SOURCE_NAME) as source:
            rows = csv.DictReader(line.decode("utf-8") for line in source)
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS)
                writer.writeheader()
                writer.writerows(
                    {column: row.get(column, "") for column in OUTPUT_COLUMNS}
                    for row in rows
                )
    print(f"Created {OUTPUT_PATH} ({sum(1 for _ in OUTPUT_PATH.open(encoding='utf-8')) - 1} restaurants)")


if __name__ == "__main__":
    main()
