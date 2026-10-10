from __future__ import annotations

import csv
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "instance" / "menus.sqlite3"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = ROOT / DATABASE_PATH


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                city TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                menu_items TEXT NOT NULL,
                menu_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_a_id INTEGER NOT NULL,
                restaurant_b_id INTEGER NOT NULL,
                similarity REAL NOT NULL,
                shared_items TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(restaurant_a_id, restaurant_b_id)
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('owner', 'analyst', 'customer')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS dish_interest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dish_name TEXT NOT NULL,
                city TEXT NOT NULL,
                location TEXT NOT NULL,
                interested INTEGER NOT NULL CHECK (interested IN (0, 1)),
                user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                city TEXT NOT NULL,
                location TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                dish_name TEXT NOT NULL,
                category TEXT NOT NULL,
                price_inr REAL,
                rating REAL,
                rating_count INTEGER,
                price_band TEXT NOT NULL,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
            );
            CREATE TABLE IF NOT EXISTS restaurant_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_restaurant_id TEXT NOT NULL UNIQUE,
                restaurant_name TEXT NOT NULL,
                city TEXT NOT NULL,
                locality TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                restaurant_type TEXT NOT NULL,
                cuisines TEXT NOT NULL,
                top_selling_dish TEXT NOT NULL,
                average_rating REAL,
                sentiment_score REAL,
                average_cost_inr REAL,
                price_category TEXT NOT NULL,
                swiggy_delivery_minutes REAL,
                zomato_delivery_minutes REAL,
                preparation_minutes REAL,
                monthly_orders REAL NOT NULL,
                monthly_revenue_inr REAL NOT NULL,
                monthly_profit_inr REAL NOT NULL,
                order_growth_pct REAL,
                weekend_uplift_pct REAL,
                repeat_customer_pct REAL,
                online_order_share_pct REAL,
                listing_date TEXT NOT NULL
            );
            """
        )
        performance_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(restaurant_performance)")
        }
        required_performance_columns = {
            "source_restaurant_id",
            "monthly_orders",
            "monthly_revenue_inr",
            "monthly_profit_inr",
        }
        if not required_performance_columns.issubset(performance_columns):
            legacy_table = "restaurant_performance_legacy"
            connection.execute(f"DROP TABLE IF EXISTS {legacy_table}")
            connection.execute(
                f"ALTER TABLE restaurant_performance RENAME TO {legacy_table}"
            )
            connection.execute(
                """
                CREATE TABLE restaurant_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_restaurant_id TEXT NOT NULL UNIQUE,
                    restaurant_name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    locality TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    restaurant_type TEXT NOT NULL,
                    cuisines TEXT NOT NULL,
                    top_selling_dish TEXT NOT NULL,
                    average_rating REAL,
                    sentiment_score REAL,
                    average_cost_inr REAL,
                    price_category TEXT NOT NULL,
                    swiggy_delivery_minutes REAL,
                    zomato_delivery_minutes REAL,
                    preparation_minutes REAL,
                    monthly_orders REAL NOT NULL,
                    monthly_revenue_inr REAL NOT NULL,
                    monthly_profit_inr REAL NOT NULL,
                    order_growth_pct REAL,
                    weekend_uplift_pct REAL,
                    repeat_customer_pct REAL,
                    online_order_share_pct REAL,
                    listing_date TEXT NOT NULL
                )
                """
            )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(restaurants)")
        }
        if "city" not in columns:
            connection.execute("ALTER TABLE restaurants ADD COLUMN city TEXT NOT NULL DEFAULT ''")
        if "location" not in columns:
            connection.execute("ALTER TABLE restaurants ADD COLUMN location TEXT NOT NULL DEFAULT ''")


def create_user(username: str, password: str, role: str) -> dict[str, Any]:
    username = username.strip().lower()
    role = role.strip().lower()
    if not username or len(password) < 6:
        raise ValueError("Username is required and password must be at least 6 characters.")
    if role not in {"owner", "analyst", "customer"}:
        raise ValueError("Choose a valid role.")
    with get_connection() as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), role),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("That username is already registered.") from error
        return {"id": cursor.lastrowid, "username": username, "role": role}


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    return None


def get_user(user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def add_dish_interest(
    dish_name: str,
    city: str,
    location: str,
    interested: bool,
    user_id: int | None = None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO dish_interest
            (dish_name, city, location, interested, user_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (dish_name.strip().lower(), city.strip(), location.strip(), int(interested), user_id),
        )


def dish_interest_summary(dish_name: str, city: str, location: str) -> dict[str, int]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS responses,
                COALESCE(SUM(interested), 0) AS interested,
                COALESCE(SUM(CASE WHEN interested = 0 THEN 1 ELSE 0 END), 0) AS not_interested
            FROM dish_interest
            WHERE dish_name = ? AND city = ? AND location = ?
            """,
            (dish_name.strip().lower(), city.strip(), location.strip()),
        ).fetchone()
    return dict(row)


def seed_from_csv(csv_path: Path | None = None) -> int:
    init_db()
    csv_path = csv_path or ROOT / "data" / "processed" / "menu_listings.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed menu data was not found at {csv_path}. "
            "Run prepare_zomato_data.py first."
        )
    with get_connection() as connection:
        if not connection.execute("SELECT 1 FROM restaurants LIMIT 1").fetchone():
            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            connection.executemany(
                """
                INSERT INTO restaurants
                (restaurant_name, platform, cuisine, city, location, latitude, longitude, menu_items, menu_text)
                VALUES (:restaurant_name, :platform, :cuisine, :city, :location, :latitude, :longitude, :menu_items, :menu_items)
                """,
                rows,
            )
        else:
            rows = []
    items_path = ROOT / "data" / "processed" / "menu_items.csv"
    if not items_path.exists():
        raise FileNotFoundError(
            f"Processed menu-item data was not found at {items_path}. "
            "Run prepare_zomato_data.py first."
        )
    with get_connection() as connection:
        if not connection.execute("SELECT 1 FROM menu_items LIMIT 1").fetchone():
            restaurant_ids = {
                row["restaurant_name"]: row["id"]
                for row in connection.execute("SELECT id, restaurant_name FROM restaurants")
            }
            with items_path.open(newline="", encoding="utf-8") as file:
                item_rows = list(csv.DictReader(file))
            connection.executemany(
                """
                INSERT INTO menu_items
                (restaurant_id, restaurant_name, platform, city, location,
                 latitude, longitude, dish_name, category, price_inr,
                 rating, rating_count, price_band)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        restaurant_ids[row["restaurant_name"]],
                        row["restaurant_name"],
                        row["platform"],
                        row["city"],
                        row["location"],
                        row["latitude"],
                        row["longitude"],
                        row["dish_name"],
                        row["category"],
                        row["price_inr"],
                        row["rating"],
                        row["rating_count"],
                        row["price_band"],
                    )
                    for row in item_rows
                ],
            )
        performance_path = ROOT / "data" / "processed" / "restaurant_performance.csv"
        if performance_path.exists() and not connection.execute(
            "SELECT 1 FROM restaurant_performance LIMIT 1"
        ).fetchone():
            with performance_path.open(newline="", encoding="utf-8") as file:
                performance_rows = list(csv.DictReader(file))
            connection.executemany(
                """
                INSERT INTO restaurant_performance
                (source_restaurant_id, restaurant_name, city, locality, latitude,
                 longitude, restaurant_type, cuisines, top_selling_dish,
                 average_rating, sentiment_score, average_cost_inr, price_category,
                 swiggy_delivery_minutes, zomato_delivery_minutes, preparation_minutes,
                 monthly_orders, monthly_revenue_inr, monthly_profit_inr,
                 order_growth_pct, weekend_uplift_pct, repeat_customer_pct,
                 online_order_share_pct, listing_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["restaurant_id"], row["restaurant_name"], row["city"],
                        row["locality"], row["latitude"], row["longitude"],
                        row["restaurant_type"], row["cuisines"],
                        row["top_selling_dish"], row["average_rating_both_platforms"],
                        row["customer_sentiment_score"], row["avg_cost_per_person_inr"],
                        row["price_category"], row["swiggy_avg_delivery_time_minutes"],
                        row["zomato_avg_delivery_time_minutes"], row["avg_prep_time_minutes"],
                        float(row["swiggy_estimated_monthly_orders"])
                        + float(row["zomato_estimated_monthly_orders"]),
                        float(row["swiggy_estimated_monthly_revenue_inr"])
                        + float(row["zomato_estimated_monthly_revenue_inr"]),
                        float(row["swiggy_estimated_net_profit_inr"])
                        + float(row["zomato_estimated_net_profit_inr"]),
                        row["monthly_order_growth_pct"], row["weekend_order_uplift_pct"],
                        row["repeat_customer_pct"], row["online_order_share_pct"],
                        row["listing_date"],
                    )
                    for row in performance_rows
                ],
            )
    return len(rows)


def restaurants() -> list[dict[str, Any]]:
    with get_connection() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM restaurants ORDER BY id")]


def menu_items() -> list[dict[str, Any]]:
    with get_connection() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM menu_items ORDER BY id")]


def restaurant_performance() -> list[dict[str, Any]]:
    with get_connection() as connection:
        return [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM restaurant_performance ORDER BY monthly_orders DESC"
            )
        ]


def replace_insights(insights: list[dict[str, Any]]) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM insights")
        connection.executemany(
            """
            INSERT INTO insights (restaurant_a_id, restaurant_b_id, similarity, shared_items)
            VALUES (:restaurant_a_id, :restaurant_b_id, :similarity, :shared_items)
            """,
            insights,
        )


def get_insights() -> list[dict[str, Any]]:
    with get_connection() as connection:
        query = """
        SELECT i.*, a.restaurant_name AS restaurant_a, b.restaurant_name AS restaurant_b,
               a.cuisine AS cuisine_a, b.cuisine AS cuisine_b,
               a.city AS city_a, a.location AS location_a,
               b.city AS city_b, b.location AS location_b,
               a.latitude AS latitude_a, a.longitude AS longitude_a,
               b.latitude AS latitude_b, b.longitude AS longitude_b
        FROM insights i
        JOIN restaurants a ON a.id = i.restaurant_a_id
        JOIN restaurants b ON b.id = i.restaurant_b_id
        ORDER BY i.similarity DESC
        """
        return [dict(row) for row in connection.execute(query)]
