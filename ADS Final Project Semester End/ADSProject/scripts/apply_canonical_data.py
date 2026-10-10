"""
Apply canonical Indian dishes and restaurant brands across all processed datasets
and update the SQLite database cleanly.
"""

import pandas as pd
import sqlite3
from pathlib import Path
from canonical_names import DISH_MAP, RESTAURANT_MAP

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "instance" / "menus.sqlite3"

def update_datasets():
    print("1. Updating menu_items.csv ...")
    items = pd.read_csv(PROCESSED / "menu_items.csv")
    items['dish_name'] = items['dish_name'].map(DISH_MAP).fillna(items['dish_name'])
    items['restaurant_name'] = items['restaurant_name'].map(RESTAURANT_MAP).fillna(items['restaurant_name'])
    items.to_csv(PROCESSED / "menu_items.csv", index=False)
    print(f"   Updated {len(items)} items. Sample dishes: {items['dish_name'].head(4).tolist()}")

    print("2. Updating menu_listings.csv ...")
    listings = pd.read_csv(PROCESSED / "menu_listings.csv")
    listings['restaurant_name'] = listings['restaurant_name'].map(RESTAURANT_MAP).fillna(listings['restaurant_name'])
    
    # Map dishes inside the semicolon-delimited string
    def map_menu_string(s):
        parts = [p.strip() for p in str(s).split(';') if p.strip()]
        return "; ".join([DISH_MAP.get(p, p) for p in parts])

    listings['menu_items'] = listings['menu_items'].apply(map_menu_string)
    listings.to_csv(PROCESSED / "menu_listings.csv", index=False)
    print(f"   Updated {len(listings)} listings.")

    print("3. Updating restaurant_performance.csv ...")
    perf = pd.read_csv(PROCESSED / "restaurant_performance.csv")
    perf['restaurant_name'] = perf['restaurant_name'].map(RESTAURANT_MAP).fillna(perf['restaurant_name'])
    perf['top_selling_dish'] = perf['top_selling_dish'].map(DISH_MAP).fillna(perf['top_selling_dish'])
    perf.to_csv(PROCESSED / "restaurant_performance.csv", index=False)
    print(f"   Updated {len(perf)} performance rows. Top dishes: {perf['top_selling_dish'].head(3).tolist()}")

    print("4. Re-seeding SQLite database ...")
    import sys
    sys.path.insert(0, str(ROOT))
    import db
    db.init_db()
    
    # Delete old tables and re-populate
    with db.get_connection() as conn:
        conn.execute("DELETE FROM restaurants")
        conn.execute("DELETE FROM menu_items")
        conn.execute("DELETE FROM restaurant_performance")
        conn.execute("DELETE FROM insights")
    
    db.seed_from_csv()
    print("   Database successfully re-seeded with realistic culinary names.")

if __name__ == "__main__":
    update_datasets()
