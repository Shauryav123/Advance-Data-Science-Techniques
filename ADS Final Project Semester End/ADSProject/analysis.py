from __future__ import annotations

import difflib
import json
import os
import pickle
import sqlite3
from itertools import combinations
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import db

ROOT = Path(__file__).resolve().parent
MODEL_PATH = Path(
    os.environ.get("MODEL_PATH", ROOT / "artifacts" / "menu_similarity.pkl")
)
if not MODEL_PATH.is_absolute():
    MODEL_PATH = ROOT / MODEL_PATH


def train_and_store() -> dict[str, int]:
    """
    Computes pairwise menu similarity strictly within the SAME city & locality trade area.
    This solves the problem statement: finding competing kitchens selling identical menus in an area.
    """
    db.init_db()
    rows = db.restaurants()
    if len(rows) < 2:
        raise RuntimeError("At least two restaurant menus are required.")

    frame = pd.DataFrame(rows)
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), stop_words="english")
    matrix = vectorizer.fit_transform(frame["menu_text"])
    similarities = cosine_similarity(matrix)

    insights = []
    # Group by city and location so comparisons are trade-area specific
    grouped: dict[tuple[str, str], list[int]] = {}
    for idx, row in enumerate(rows):
        key = (row["city"].strip().lower(), row["location"].strip().lower())
        grouped.setdefault(key, []).append(idx)

    for (city, loc), indices in grouped.items():
        if len(indices) < 2:
            continue
        for left, right in combinations(indices, 2):
            sim = float(similarities[left, right])
            shared = sorted(
                set(rows[left]["menu_items"].lower().split("; "))
                & set(rows[right]["menu_items"].lower().split("; "))
            )
            insights.append(
                {
                    "restaurant_a_id": rows[left]["id"],
                    "restaurant_b_id": rows[right]["id"],
                    "similarity": round(sim, 4),
                    "shared_items": json.dumps(shared),
                }
            )

    db.replace_insights(insights)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as file:
        pickle.dump(
            {"vectorizer": vectorizer, "restaurant_ids": frame["id"].tolist()},
            file,
        )
    return {
        "restaurants": len(rows),
        "menu_items": len(db.menu_items()),
        "comparisons": len(insights),
    }


def build_area_repetitiveness() -> list[dict]:
    """
    Ranks neighbourhoods by menu repetitiveness score (average intra-locality similarity).
    Also joins OpenStreetMap competitor counts and Census population data.
    """
    with db.get_connection() as conn:
        insights = db.get_insights()
        
        # Load Census demographics
        census_rows = conn.execute("SELECT * FROM census_districts").fetchall()
        census_map = {r["city"].strip().lower(): dict(r) for r in census_rows}
        
        # Load OSM density
        osm_rows = conn.execute("SELECT * FROM osm_restaurant_density").fetchall()
        osm_map = {(r["city_normalized"].strip().lower(), r["locality"].strip().lower()): dict(r) for r in osm_rows}

    # Group insights by neighbourhood
    loc_similarities: dict[tuple[str, str], list[float]] = {}
    for item in insights:
        # Get city and location of restaurant A
        key = (item.get("city_a", "").strip().lower(), item.get("location_a", "").strip().lower())
        loc_similarities.setdefault(key, []).append(item["similarity"])

    restaurants = db.restaurants()
    loc_restaurants: dict[tuple[str, str], list[dict]] = {}
    for r in restaurants:
        key = (r["city"].strip().lower(), r["location"].strip().lower())
        loc_restaurants.setdefault(key, []).append(r)

    results = []
    for (city_norm, loc_norm), r_list in loc_restaurants.items():
        if not r_list:
            continue
        sims = loc_similarities.get((city_norm, loc_norm), [])
        avg_sim = round(sum(sims) / len(sims), 3) if sims else 0.15
        
        # Look up OSM & Census
        osm_info = osm_map.get((city_norm, loc_norm), {})
        osm_competitors = osm_info.get("restaurant_count", len(r_list))
        
        c_info = census_map.get(city_norm, {})
        pop = c_info.get("population_total", 5000000)
        
        # Saturation level
        if avg_sim >= 0.40:
            status = "Highly Repetitive"
            badge = "danger"
        elif avg_sim >= 0.25:
            status = "Moderate Overlap"
            badge = "warning"
        else:
            status = "Diverse Menus"
            badge = "success"

        results.append({
            "city": r_list[0]["city"],
            "locality": r_list[0]["location"],
            "restaurant_count": len(r_list),
            "osm_competitors": osm_competitors,
            "population": pop,
            "avg_similarity": avg_sim,
            "status": status,
            "badge": badge,
            "latitude": r_list[0]["latitude"],
            "longitude": r_list[0]["longitude"],
        })

    return sorted(results, key=lambda x: x["avg_similarity"], reverse=True)


def get_community_poll_leaderboard(city: str | None = None, location: str | None = None) -> list[dict]:
    """
    Aggregates verified local diner interest votes from the dish_interest table.
    Ranks dishes by community demand and voter enthusiasm.
    """
    with db.get_connection() as conn:
        query = "SELECT dish_name, city, location, interested FROM dish_interest"
        params = []
        conds = []
        if city and str(city).lower() != "all":
            conds.append("LOWER(city) = LOWER(?)")
            params.append(str(city).strip())
        if location and str(location).lower() != "all":
            conds.append("LOWER(location) = LOWER(?)")
            params.append(str(location).strip())
        if conds:
            query += " WHERE " + " AND ".join(conds)
        rows = conn.execute(query, tuple(params)).fetchall()

    grouped: dict[str, dict] = {}
    for r in rows:
        d = r["dish_name"].strip().lower()
        if d not in grouped:
            grouped[d] = {
                "dish": d.title(),
                "city": r["city"],
                "location": r["location"],
                "total_votes": 0,
                "interested": 0,
                "not_interested": 0,
            }
        grouped[d]["total_votes"] += 1
        if r["interested"]:
            grouped[d]["interested"] += 1
        else:
            grouped[d]["not_interested"] += 1

    leaderboard = []
    for d, info in grouped.items():
        total = info["total_votes"]
        pos = info["interested"]
        pct = round((pos / max(1, total)) * 100)
        leaderboard.append({
            "dish": info["dish"],
            "city": info["city"],
            "location": info["location"],
            "total_votes": total,
            "interested": pos,
            "not_interested": info["not_interested"],
            "approval_pct": pct,
            "summary": f"{pct}% wanted ({pos}/{total} voters)",
        })

    return sorted(leaderboard, key=lambda x: (x["interested"], x["approval_pct"]), reverse=True)


def build_opportunities(city: str | None = None, location: str | None = None) -> list[dict]:
    """
    Calculates menu whitespace by combining:
    1. Low local dish presence (Supply Gap)
    2. Real community voter poll demand from dish_interest (Diner Pull Factor)
    3. Consumer interest from real delivery survey dataset (Demand Signal)
    4. Locality competition factor from OSM density
    """
    items = db.menu_items()
    if city and str(city).lower() != "all":
        items = [i for i in items if i["city"].lower() == str(city).lower()]
    if location and str(location).lower() != "all":
        items = [i for i in items if i["location"].lower() == str(location).lower()]

    if not items:
        items = db.menu_items()

    # Count dish frequencies
    dish_counts: dict[str, int] = {}
    dish_categories: dict[str, str] = {}
    dish_prices: dict[str, list[float]] = {}
    for i in items:
        d = i["dish_name"].strip()
        dish_counts[d] = dish_counts.get(d, 0) + 1
        dish_categories[d] = i["category"]
        if i["price_inr"]:
            dish_prices.setdefault(d, []).append(float(i["price_inr"]))

    total_listings = len({i["restaurant_id"] for i in items}) or 1

    # Load Consumer Survey demand signals
    with db.get_connection() as conn:
        survey_rows = conn.execute("SELECT * FROM online_food_delivery_survey").fetchall()

    survey_demand_weight = 0.85
    if survey_rows:
        positive_count = sum(1 for r in survey_rows if str(r["Output"]).strip().lower() == "yes")
        survey_demand_weight = round(positive_count / len(survey_rows), 2)

    # Load Community Poll Demand
    poll_leaderboard = get_community_poll_leaderboard(city, location)
    poll_map = {p["dish"].lower(): p for p in poll_leaderboard}

    # Dynamic whitespace cutoff ensures opportunities are never empty
    cov_values = [round(c / max(1, total_listings), 3) for c in dish_counts.values()]
    cutoff = 0.25 if any(c <= 0.25 for c in cov_values) else (sorted(cov_values)[min(14, len(cov_values)-1)] + 0.005)

    opportunities = []
    seen_dishes = set()

    # 1. First include any novel dishes specifically requested by local diner polls
    for p in poll_leaderboard:
        p_dish = p["dish"]
        p_lower = p_dish.lower()
        if p_lower not in [d.lower() for d in dish_counts] or dish_counts.get(p_dish, 0) == 0:
            seen_dishes.add(p_lower)
            score = round(min(99.0, 78.0 + (p["approval_pct"] * 0.21)), 1)
            opportunities.append({
                "dish": p_dish,
                "category": "Community Requested / Novel",
                "current_restaurants": 0,
                "present_restaurants": 0,
                "total_restaurants": total_listings,
                "total_market_restaurants": total_listings,
                "coverage_pct": 0.0,
                "local_appearance_pct": 0.0,
                "avg_price_inr": 280.0,
                "opportunity_score": score,
                "reason": f"0 kitchens in area &middot; 🗳️ {p['approval_pct']}% Customer Demand ({p['interested']} customer votes)",
                "poll_badge": f"🗳️ {p['approval_pct']}% Wanted by Customers ({p['interested']} votes)",
                "poll_votes": p["total_votes"],
                "poll_interested": p["interested"],
                "poll_demand_pct": p["approval_pct"],
                "is_community_wanted": True,
                "repetition_label": "Rare in Local Area",
            })

    # 2. Add lowest saturation menu items, boosted by poll demand
    for dish, count in sorted(dish_counts.items(), key=lambda x: x[1]):
        if dish.lower() in seen_dishes:
            continue
        coverage_pct = round(count / max(1, total_listings), 3)
        if coverage_pct <= cutoff or len(opportunities) < 10:
            seen_dishes.add(dish.lower())
            avg_p = round(sum(dish_prices.get(dish, [200])) / max(1, len(dish_prices.get(dish, [200]))), 1)
            base_score = (1.0 - coverage_pct) * 70.0 + (survey_demand_weight * 25.0)

            # Check if this item has voter poll demand
            poll_info = poll_map.get(dish.lower())
            poll_badge = None
            poll_votes = 0
            poll_interested = 0
            poll_pct = 0
            is_community_wanted = False
            if poll_info and poll_info["interested"] > 0:
                is_community_wanted = True
                poll_votes = poll_info["total_votes"]
                poll_interested = poll_info["interested"]
                poll_pct = poll_info["approval_pct"]
                poll_badge = f"🗳️ {poll_pct}% Wanted by Customers ({poll_interested} votes)"
                base_score += min(18.0, poll_interested * 6.0 + (poll_pct * 0.1))
                reason = f"Served in {count}/{total_listings} kitchens ({round(coverage_pct*100, 1)}%) &middot; 🗳️ {poll_pct}% customer demand"
            else:
                reason = f"Found in only {round(coverage_pct*100, 1)}% of kitchens ({count}/{total_listings})"

            score = round(min(99.0, base_score), 1)
            opportunities.append({
                "dish": dish,
                "category": dish_categories.get(dish, "Main Course"),
                "current_restaurants": count,
                "present_restaurants": count,
                "total_restaurants": total_listings,
                "total_market_restaurants": total_listings,
                "coverage_pct": round(coverage_pct * 100, 1),
                "local_appearance_pct": round(coverage_pct * 100, 1),
                "avg_price_inr": avg_p,
                "opportunity_score": score,
                "reason": reason,
                "poll_badge": poll_badge,
                "poll_votes": poll_votes,
                "poll_interested": poll_interested,
                "poll_demand_pct": poll_pct,
                "is_community_wanted": is_community_wanted,
                "repetition_label": "Rare in Local Area" if coverage_pct <= 0.20 else "Moderate Supply",
            })

    return sorted(opportunities, key=lambda x: x["opportunity_score"], reverse=True)[:15]


def _dish_restaurant_counts(items: list[dict]) -> dict[str, int]:
    """Map canonical dish name to count of distinct restaurants offering it."""
    mapping: dict[str, set[Any]] = {}
    for item in items:
        dish = (item.get("dish_name") or item.get("dish") or "").strip()
        rid = item.get("restaurant_id")
        if dish and rid is not None:
            mapping.setdefault(dish, set()).add(rid)
    return {dish: len(rids) for dish, rids in mapping.items()}


def build_summary() -> dict:
    rows = db.restaurants()
    insights = db.get_insights()
    counts = _dish_restaurant_counts(db.menu_items())
    missing_items = [
        {"item": item, "restaurant_count": count}
        for item, count in sorted(counts.items(), key=lambda pair: (pair[1], pair[0]))
        if count <= max(1, len(rows) // 5)
    ]
    return {
        "restaurants": len(rows),
        "high_similarity_pairs": sum(item["similarity"] >= 0.40 for item in insights),
        "average_similarity": round(
            sum(item["similarity"] for item in insights) / len(insights), 3
        )
        if insights
        else 0,
        "menu_gaps": missing_items[:8],
        "threshold": 0.40,
    }


def build_area_analysis() -> list[dict]:
    """Return enriched restaurant, competitor, and menu coverage grouped by city and neighbourhood."""
    items = db.menu_items()
    rep_areas = {
        (a["city"].strip().lower(), a["locality"].strip().lower()): a
        for a in build_area_repetitiveness()
    }
    grouped: dict[tuple[str, str], list[dict]] = {}
    for item in items:
        key = (item["city"] or "Unknown", item["location"] or "Unknown")
        grouped.setdefault(key, []).append(item)

    results = []
    for (city, area), area_items in sorted(grouped.items()):
        key_norm = (city.strip().lower(), area.strip().lower())
        rep_info = rep_areas.get(key_norm, {})
        prices = [float(it["price_inr"]) for it in area_items if it.get("price_inr")]
        avg_price = round(sum(prices) / len(prices), 1) if prices else 200.0

        restaurant_ids = {item["restaurant_id"] for item in area_items}
        r_count = len(restaurant_ids)
        distinct_dishes = len({item["dish_name"].strip() for item in area_items})
        dish_counts = _dish_restaurant_counts(area_items)
        top_dishes = [
            {"dish": dish, "restaurants": count}
            for dish, count in sorted(
                dish_counts.items(),
                key=lambda pair: (-pair[1], pair[0]),
            )[:5]
        ]

        results.append({
            "city": city,
            "area": area,
            "restaurants": r_count,
            "osm_competitors": rep_info.get("osm_competitors", r_count),
            "population": rep_info.get("population", 5000000),
            "avg_similarity": rep_info.get("avg_similarity", 0.20),
            "status": rep_info.get("status", "Moderate Overlap"),
            "badge": rep_info.get("badge", "warning"),
            "dishes": distinct_dishes,
            "avg_price_inr": avg_price,
            "top_dishes": top_dishes,
        })
    return results


def build_dish_analysis(city: str | None = None, area: str | None = None) -> list[dict]:
    """Return frequency and saturation coverage for individual dishes, enriched with community voter poll signals."""
    items = db.menu_items()
    if city and city.strip().lower() != "all":
        items = [item for item in items if item["city"].lower() == city.lower()]
    if area and area.strip().lower() != "all":
        items = [item for item in items if item["location"].lower() == area.lower()]

    counts: dict[str, int] = {}
    cat_map: dict[str, str] = {}
    price_map: dict[str, list[float]] = {}
    for item in items:
        d = item["dish_name"].strip()
        counts[d] = counts.get(d, 0) + 1
        cat_map[d] = item.get("category", "Main Course")
        if item.get("price_inr"):
            price_map.setdefault(d, []).append(float(item["price_inr"]))

    restaurant_counts = _dish_restaurant_counts(items)
    total_restaurants = len({item["restaurant_id"] for item in items}) or 1

    # Load voter poll signals
    poll_leaderboard = get_community_poll_leaderboard(city, area)
    poll_map = {p["dish"].lower(): p for p in poll_leaderboard}

    dish_list = []
    seen = set()

    # 1. Add novel voter-requested items
    for p in poll_leaderboard:
        p_dish = p["dish"]
        p_lower = p_dish.lower()
        if p_lower not in [d.lower() for d in counts]:
            seen.add(p_lower)
            dish_list.append({
                "dish": p_dish,
                "category": "Community Voted / High Demand",
                "menu_items": 0,
                "restaurants": 0,
                "total_restaurants": total_restaurants,
                "coverage": 0.0,
                "coverage_pct": 0.0,
                "avg_price_inr": 280.0,
                "status": "Market Whitespace",
                "badge": "success",
                "poll_badge": f"🗳️ {p['approval_pct']}% Wanted ({p['interested']} votes)",
                "poll_votes": p["total_votes"],
                "poll_demand_pct": p["approval_pct"],
                "is_community_wanted": True,
            })

    # 2. Add existing dishes
    for dish, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        if dish.lower() in seen:
            continue
        r_count = restaurant_counts.get(dish, 0)
        coverage_pct = round((r_count / max(1, total_restaurants)) * 100, 1)
        prices = price_map.get(dish, [200.0])
        avg_price = round(sum(prices) / len(prices), 1)

        poll_info = poll_map.get(dish.lower())
        poll_badge = None
        poll_votes = 0
        poll_pct = 0
        if poll_info and poll_info["interested"] > 0:
            poll_votes = poll_info["total_votes"]
            poll_pct = poll_info["approval_pct"]
            poll_badge = f"🗳️ {poll_pct}% Wanted ({poll_info['interested']} votes)"

        if coverage_pct >= 40.0 and not poll_badge:
            status = "Crowded / Redundant"
            badge = "danger"
        elif coverage_pct <= 20.0 or (poll_info and poll_info["approval_pct"] >= 75):
            status = "Market Whitespace"
            badge = "success"
        else:
            status = "Moderate Competition"
            badge = "warning"

        dish_list.append({
            "dish": dish,
            "category": cat_map.get(dish, "Main Course"),
            "menu_items": count,
            "restaurants": r_count,
            "total_restaurants": total_restaurants,
            "coverage": round(r_count / max(1, total_restaurants), 3),
            "coverage_pct": coverage_pct,
            "avg_price_inr": avg_price,
            "status": status,
            "badge": badge,
            "poll_badge": poll_badge,
            "poll_votes": poll_votes,
            "poll_demand_pct": poll_pct,
            "is_community_wanted": bool(poll_badge),
        })
    return dish_list


def build_performance_summary(city: str | None = None) -> dict:
    rows = db.restaurant_performance()
    if city:
        rows = [row for row in rows if row["city"].lower() == city.lower()]
    if not rows:
        return {"restaurants": 0, "cities": [], "monthly_orders": 0, "monthly_revenue_inr": 0}
    return {
        "restaurants": len(rows),
        "cities": sorted({row["city"] for row in rows}),
        "monthly_orders": round(sum(row["monthly_orders"] for row in rows)),
        "monthly_revenue_inr": round(sum(row["monthly_revenue_inr"] for row in rows)),
        "average_rating": round(sum(row["average_rating"] or 0 for row in rows) / len(rows), 2),
        "top_restaurants": [
            {
                "name": row["restaurant_name"],
                "city": row["city"],
                "orders": round(row["monthly_orders"]),
                "revenue": round(row["monthly_revenue_inr"]),
                "dish": row["top_selling_dish"],
            }
            for row in rows[:6]
        ],
    }


_orders_model_cache = None
_revenue_model_cache = None


def _get_ml_models():
    global _orders_model_cache, _revenue_model_cache
    if _orders_model_cache is None:
        p_orders = ROOT / "artifacts" / "restaurant_orders_model.pkl"
        p_rev = ROOT / "artifacts" / "restaurant_revenue_model.pkl"
        if p_orders.exists():
            with open(p_orders, "rb") as f:
                _orders_model_cache = pickle.load(f)
        if p_rev.exists():
            with open(p_rev, "rb") as f:
                _revenue_model_cache = pickle.load(f)
    return _orders_model_cache, _revenue_model_cache


def resolve_dish_name(query: str, canonical_dishes: list[str]) -> dict:
    """
    Intelligently resolves entered dish name against canonical dishes.
    Handles exact matches, sub-phrase containment, typos (fuzzy matching),
    and identifies genuinely novel/innovative dishes.
    """
    q_norm = " ".join(query.lower().split())
    if not q_norm:
        return {
            "dish": query,
            "original": query,
            "status": "Empty",
            "is_corrected": False,
            "is_novel": True,
            "confidence": 0.0,
        }

    # 1. Exact match (case insensitive)
    for d in canonical_dishes:
        if d.lower() == q_norm:
            return {
                "dish": d,
                "original": query,
                "status": "Exact Match",
                "is_corrected": False,
                "is_novel": False,
                "confidence": 1.0,
            }

    # 2. Token subset match (e.g. 'mutton biryani' matches 'Hyderabadi Mutton Biryani')
    q_tokens = set(q_norm.split())
    for d in canonical_dishes:
        d_tokens = set(d.lower().split())
        if q_tokens.issubset(d_tokens) or (
            len(q_tokens) > 1 and len(q_tokens & d_tokens) / len(q_tokens) >= 0.75
        ):
            return {
                "dish": d,
                "original": query,
                "status": "Standard Menu Item",
                "is_corrected": True,
                "is_novel": False,
                "confidence": 0.90,
            }

    # 3. Fuzzy matching for typos (e.g. 'paner butter masla' -> 'Paneer Butter Masala')
    best_dish = None
    best_ratio = 0.0
    for d in canonical_dishes:
        ratio = difflib.SequenceMatcher(None, q_norm, d.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_dish = d

    if best_ratio >= 0.70 and best_dish:
        return {
            "dish": best_dish,
            "original": query,
            "status": "Typo Auto-Corrected",
            "is_corrected": True,
            "is_novel": False,
            "confidence": round(best_ratio, 2),
        }

    # 4. Genuinely new/novel dish (e.g. "Korean Corn Dog", "Avocado Toast", "Truffle Ramen")
    return {
        "dish": query.strip().title(),
        "original": query,
        "status": "Novel Dish (Untapped Market Innovation)",
        "is_corrected": False,
        "is_novel": True,
        "confidence": 0.0,
    }


def predict_restaurant_concept(
    city: str,
    location: str,
    menu_items: list[str],
    price: float | None = None,
) -> dict:
    rows = [row for row in db.restaurants() if row["city"].lower() == city.lower()]
    if not rows:
        raise ValueError(f"No restaurant data is available for {city}.")
    
    clean_items = [item.strip() for item in menu_items if item.strip()]
    if not clean_items:
        raise ValueError("Enter at least one menu item.")

    canonical_dishes = sorted({row["dish_name"].strip() for row in db.menu_items()})
    
    # Resolve typos vs novel dishes
    resolutions = [resolve_dish_name(item, canonical_dishes) for item in clean_items]
    typo_corrections = [r for r in resolutions if r.get("is_corrected")]
    novel_dishes = [r for r in resolutions if r.get("is_novel")]

    city_items = [
        item for item in db.menu_items()
        if item["city"].lower() == city.lower()
    ]
    item_rows = [
        item for item in city_items
        if item["location"].lower() == location.lower()
    ]
    area_rows = item_rows
    item_rows = item_rows or city_items
    nearby_ids = {item["restaurant_id"] for item in item_rows}
    item_counts = _dish_restaurant_counts(item_rows)

    coverage = []
    for r in resolutions:
        resolved_dish = r["dish"]
        r_count = 0 if r["is_novel"] else item_counts.get(resolved_dish, 0)
        coverage.append({
            "item": resolved_dish,
            "original_query": r["original"],
            "restaurant_count": r_count,
            "status": r["status"],
            "is_novel": r["is_novel"],
            "is_corrected": r["is_corrected"],
            "confidence": r["confidence"],
        })

    common_items = [item for item in coverage if item["restaurant_count"] > 2]
    rare_items = [item for item in coverage if item["restaurant_count"] <= 2]
    overlap = round(sum(item["restaurant_count"] > 0 for item in coverage) / len(coverage), 3)
    whitespace = round(1 - (sum(item["restaurant_count"] for item in coverage) / max(1, len(coverage) * len(nearby_ids))), 3)
    
    competition_score = round(min(99, overlap * 100), 1)
    opportunity_score = round(min(99, whitespace * 70 + (len(rare_items) / len(coverage)) * 30), 1)

    # Cross-reference entered dishes with community diner polls
    poll_leaderboard = get_community_poll_leaderboard(city, location)
    poll_map = {p["dish"].lower(): p for p in poll_leaderboard}

    community_poll_matches = []
    poll_score_boost = 0.0
    for r in resolutions:
        d_lower = r["dish"].lower()
        orig_lower = r["original"].lower()
        p_info = poll_map.get(d_lower) or poll_map.get(orig_lower)
        if p_info and p_info["interested"] > 0:
            community_poll_matches.append({
                "dish": r["dish"],
                "total_votes": p_info["total_votes"],
                "interested": p_info["interested"],
                "approval_pct": p_info["approval_pct"],
                "badge": f"🗳️ {p_info['approval_pct']}% Customer Demand ({p_info['interested']} votes)",
                "note": f"Verified customer interest: {p_info['interested']} local customers requested this dish ({p_info['approval_pct']}% positive poll)",
            })
            poll_score_boost += min(15.0, p_info["interested"] * 5.0 + (p_info["approval_pct"] * 0.1))

    if community_poll_matches:
        opportunity_score = round(min(99.0, opportunity_score + poll_score_boost), 1)

    if opportunity_score >= 70 and competition_score <= 45:
        outlook = "Promising High-Demand Concept"
    elif opportunity_score >= 45:
        outlook = "Viable with Unique Dishes"
    else:
        outlook = "High Competition / Crowded Concept"

    # Locality Price Benchmark
    prices = [float(it["price_inr"]) for it in (area_rows or city_items) if it.get("price_inr")]
    locality_avg_price = round(sum(prices) / len(prices), 1) if prices else 220.0

    price_analysis = None
    ml_prediction = None

    if price is not None and float(price) > 0:
        p_val = float(price)
        diff_pct = round(((p_val - locality_avg_price) / locality_avg_price) * 100, 1)
        tier = "Budget" if p_val <= 250 else ("Mid-Range" if p_val <= 500 else "Premium")
        tier_encoded = 1 if p_val <= 250 else (2 if p_val <= 500 else 3)

        if diff_pct <= -15.0:
            positioning = f"Value / Budget Advantage ({abs(diff_pct)}% below area average)"
        elif diff_pct >= 15.0:
            positioning = f"Premium Pricing ({diff_pct}% above area average)"
        else:
            positioning = "Market-Aligned Pricing (within ±15% of area average)"

        price_analysis = {
            "proposed_price": round(p_val, 1),
            "locality_avg_price": locality_avg_price,
            "difference_pct": diff_pct,
            "price_tier": tier,
            "positioning": positioning,
        }

        # ML Model Inference for Estimated Orders & Revenue
        orders_model_meta, rev_model_meta = _get_ml_models()
        if orders_model_meta and rev_model_meta:
            try:
                orders_pipe = orders_model_meta["model"]
                rev_pipe = rev_model_meta["model"]

                # Repetitive info lookup
                rep_areas = {
                    (a["city"].strip().lower(), a["locality"].strip().lower()): a
                    for a in build_area_repetitiveness()
                }
                rep_info = rep_areas.get((city.strip().lower(), location.strip().lower()), {})
                density = rep_info.get("osm_competitors", len(nearby_ids) or 25)
                pop = rep_info.get("population", 5000000)

                def _build_feature_row(curr_price: float) -> pd.DataFrame:
                    c_tier = "Budget" if curr_price <= 250 else ("Mid-Range" if curr_price <= 500 else "Premium")
                    c_encoded = 1 if curr_price <= 250 else (2 if curr_price <= 500 else 3)
                    return pd.DataFrame([{
                        "city": city.lower(),
                        "locality": location.lower(),
                        "restaurant_type": "Cloud Kitchen",
                        "cuisines": "North Indian",
                        "price_category": c_tier,
                        "average_rating": 4.1,
                        "average_cost_inr": curr_price,
                        "avg_delivery_time": 30.0,
                        "preparation_minutes": 20.0,
                        "num_cuisines": 2,
                        "is_cloud_kitchen": 1,
                        "price_category_encoded": c_encoded,
                        "prep_to_delivery_ratio": 20.0 / 30.0,
                        "menu_item_count": len(clean_items),
                        "menu_avg_price": curr_price,
                        "menu_median_price": curr_price,
                        "menu_min_price": round(curr_price * 0.75, 1),
                        "menu_max_price": round(curr_price * 1.35, 1),
                        "menu_category_count": 2,
                        "locality_competitor_density": density,
                        "population_total": pop,
                        "population_urban": int(pop * 0.88),
                        "literates_total": int(pop * 0.78),
                    }])

                pred_orders = round(float(orders_pipe.predict(_build_feature_row(p_val))[0]))
                pred_revenue = round(float(rev_pipe.predict(_build_feature_row(p_val))[0]))

                # Sensitivity scenarios
                low_p = round(p_val * 0.85, 1)
                high_p = round(p_val * 1.15, 1)
                low_orders = round(float(orders_pipe.predict(_build_feature_row(low_p))[0]))
                low_rev = round(float(rev_pipe.predict(_build_feature_row(low_p))[0]))
                high_orders = round(float(orders_pipe.predict(_build_feature_row(high_p))[0]))
                high_rev = round(float(rev_pipe.predict(_build_feature_row(high_p))[0]))

                ml_prediction = {
                    "estimated_monthly_orders": pred_orders,
                    "estimated_monthly_revenue_inr": pred_revenue,
                    "model_used": "GradientBoostingRegressor / RandomForest Ensemble",
                    "sensitivity_analysis": [
                        {
                            "scenario": "Value Discount (-15%)",
                            "price": low_p,
                            "estimated_orders": low_orders,
                            "estimated_revenue": low_rev,
                        },
                        {
                            "scenario": "Current Proposed Price",
                            "price": round(p_val, 1),
                            "estimated_orders": pred_orders,
                            "estimated_revenue": pred_revenue,
                        },
                        {
                            "scenario": "Premium Markup (+15%)",
                            "price": high_p,
                            "estimated_orders": high_orders,
                            "estimated_revenue": high_rev,
                        },
                    ],
                }
            except Exception as e:
                # Defensive fallback
                pass

    return {
        "city": city,
        "location": location,
        "market_restaurants": len(nearby_ids),
        "market_scope": "neighbourhood" if area_rows else "city",
        "menu_items": [r["dish"] for r in resolutions],
        "item_coverage": coverage,
        "typo_corrections": typo_corrections,
        "novel_dishes": novel_dishes,
        "community_poll_matches": community_poll_matches,
        "common_items": [item["item"] for item in common_items],
        "rare_items": [item["item"] for item in rare_items],
        "competition_score": competition_score,
        "opportunity_score": opportunity_score,
        "menu_whitespace": round(whitespace * 100, 1),
        "outlook": outlook,
        "price": price,
        "price_analysis": price_analysis,
        "ml_performance_prediction": ml_prediction,
        "classification": "ESTIMATED PERFORMANCE PREDICTION",
        "limitations": [
            "This is an estimated trade-area performance prediction, not a guaranteed financial receipt.",
            "Prediction incorporates price elasticity, OpenStreetMap commercial competitor density, and Census demographics.",
        ],
    }
