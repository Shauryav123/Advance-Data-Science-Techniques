from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .prepare_model_features import OUTPUT, build_features


ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "processed" / "model_validation_report.json"
FEATURES = [
    "city", "locality", "restaurant_type", "cuisines", "price_category",
    "average_rating", "average_cost_inr", "avg_delivery_time",
    "preparation_minutes", "num_cuisines", "is_cloud_kitchen",
    "price_category_encoded", "prep_to_delivery_ratio", "menu_item_count",
    "menu_avg_price", "menu_median_price", "menu_min_price", "menu_max_price",
    "menu_category_count", "locality_competitor_density", "population_total",
    "population_urban", "literates_total",
]
TARGETS = {
    "monthly_orders": [
        "swiggy_estimated_monthly_orders",
        "zomato_estimated_monthly_orders",
        "monthly_revenue_inr",
        "monthly_profit_inr",
        "repeat_customer_pct",
        "online_order_share_pct",
        "weekend_uplift_pct",
        "order_growth_pct",
        "sentiment_score",
    ],
    "monthly_revenue_inr": [
        "swiggy_estimated_monthly_orders",
        "zomato_estimated_monthly_orders",
        "monthly_orders",
        "monthly_profit_inr",
        "swiggy_estimated_monthly_revenue_inr",
        "zomato_estimated_monthly_revenue_inr",
        "repeat_customer_pct",
        "online_order_share_pct",
        "weekend_uplift_pct",
        "order_growth_pct",
        "sentiment_score",
    ],
}


def make_pipeline(model: object) -> Pipeline:
    categorical = ["city", "locality", "restaurant_type", "cuisines", "price_category"]
    numeric = [column for column in FEATURES if column not in categorical]
    preprocessor = ColumnTransformer(
        [
            ("categorical", Pipeline([
                ("impute", SimpleImputer(strategy="most_frequent")),
                ("encode", OneHotEncoder(handle_unknown="ignore")),
            ]), categorical),
            ("numeric", SimpleImputer(strategy="median"), numeric),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def benchmark_target(frame: pd.DataFrame, target: str) -> dict:
    if not OUTPUT.exists():
        frame, _ = build_features()
    X, y = frame[FEATURES], frame[target]
    models = {
        "DummyRegressor (Mean)": DummyRegressor(strategy="mean"),
        "DummyRegressor (Median)": DummyRegressor(strategy="median"),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1
        ),
        "ExtraTreesRegressor": ExtraTreesRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1
        ),
        "GradientBoostingRegressor": GradientBoostingRegressor(
            n_estimators=150, max_depth=2, learning_rate=0.03,
            loss="huber", random_state=42
        ),
    }
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    results = {}
    for name, estimator in models.items():
        folds = []
        for train, validation in cv.split(X):
            pipeline = make_pipeline(estimator)
            pipeline.fit(X.iloc[train], y.iloc[train])
            predictions = pipeline.predict(X.iloc[validation])
            folds.append({
                "mae": mean_absolute_error(y.iloc[validation], predictions),
                "rmse": mean_squared_error(y.iloc[validation], predictions) ** 0.5,
                "r2": r2_score(y.iloc[validation], predictions),
            })
        results[name] = {
            metric: float(np.mean([fold[metric] for fold in folds]))
            for metric in ("mae", "rmse", "r2")
        }
        results[name]["folds"] = folds
    baseline = results["DummyRegressor (Mean)"]["mae"]
    winner = min(results, key=lambda name: results[name]["mae"])
    return {
        "status": "estimated_performance_prediction",
        "target": target,
        "rows": int(len(frame)),
        "features": FEATURES,
        "leakage_excluded": TARGETS[target],
        "models": results,
        "winner_by_mae": winner,
        "beats_mean_baseline": bool(results[winner]["mae"] < baseline),
    }


def benchmark() -> dict:
    frame = pd.read_csv(OUTPUT) if OUTPUT.exists() else build_features()[0]
    report = {
        "status": "estimated_performance_prediction",
        "rows": int(len(frame)),
        "targets": {
            target: benchmark_target(frame, target) for target in TARGETS
        },
    }
    ROOT.joinpath("artifacts").mkdir(parents=True, exist_ok=True)
    for target, target_report in report["targets"].items():
        winner_name = target_report["winner_by_mae"]
        if winner_name.startswith("DummyRegressor"):
            continue
        estimator = {
            "RandomForestRegressor": RandomForestRegressor(
                n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1
            ),
            "ExtraTreesRegressor": ExtraTreesRegressor(
                n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1
            ),
            "GradientBoostingRegressor": GradientBoostingRegressor(
                n_estimators=150, max_depth=2, learning_rate=0.03,
                loss="huber", random_state=42
            ),
        }[winner_name]
        pipeline = make_pipeline(estimator)
        pipeline.fit(frame[FEATURES], frame[target])
        artifact = {
            "model": pipeline,
            "target": target,
            "features": FEATURES,
            "training_rows": len(frame),
            "model_name": winner_name,
            "metrics": {
                key: target_report["models"][winner_name][key]
                for key in ("mae", "rmse", "r2")
            },
            "data_status": "estimated",
            "limitations": [
                "Only 200 restaurant-level records are available.",
                "The target is estimated or aggregated rather than verified transaction data.",
                "Cross-validation is shuffled and cross-sectional, not a future time-series forecast.",
            ],
        }
        filename = "restaurant_orders_model.pkl" if target == "monthly_orders" else "restaurant_revenue_model.pkl"
        with (ROOT / "artifacts" / filename).open("wb") as file:
            pickle.dump(artifact, file)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        target: {
            name: {key: round(value, 3) for key, value in values.items() if key in {"mae", "rmse", "r2"}}
            for name, values in target_report["models"].items()
        }
        for target, target_report in report["targets"].items()
    }, indent=2))
    return report


if __name__ == "__main__":
    benchmark()
