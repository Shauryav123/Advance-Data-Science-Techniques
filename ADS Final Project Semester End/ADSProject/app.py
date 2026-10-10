from __future__ import annotations

import json
import os
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

import analysis
import db

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found."}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error."}), 500
    return render_template("500.html"), 500

def role_required(*roles: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = session.get("user")
            if not user:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required."}), 401
                return redirect(url_for("login", next=request.path))
            if roles and user["role"] not in roles:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "You do not have access to this resource."}), 403
                return "Forbidden", 403
            return view(*args, **kwargs)
        return wrapped
    return decorator

def ensure_data() -> None:
    db.init_db()
    db.seed_from_csv()
    if not db.get_insights():
        analysis.train_and_store()

@app.route("/login", methods=["GET", "POST"])
def login():
    db.init_db()
    if request.method == "POST":
        user = db.authenticate_user(request.form.get("username", ""), request.form.get("password", ""))
        if user:
            session.clear()
            session["user"] = user
            target = request.args.get("next") or url_for("dashboard")
            return redirect(target if target.startswith("/") else url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("auth.html", title="Sign in", signup=False)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    db.init_db()
    if request.method == "POST":
        try:
            user = db.create_user(
                request.form.get("username", ""),
                request.form.get("password", ""),
                request.form.get("role", "customer"),
            )
        except ValueError as error:
            flash(str(error))
        else:
            session["user"] = user
            return redirect(url_for("dashboard"))
    return render_template("auth.html", title="Create account", signup=True)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
def dashboard():
    if not session.get("user") and request.args.get("preview") != "1":
        return redirect(url_for("login", next=url_for("dashboard")))
    ensure_data()
    return render_template("dashboard.html", summary=analysis.build_summary())


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "bitewise"})


@app.get("/owner")
@role_required("owner")
def owner_page():
    ensure_data()
    return render_template("owner.html")


@app.get("/analyst")
@role_required("analyst", "owner")
def analyst_page():
    ensure_data()
    return render_template("analyst.html")


@app.get("/customer")
@role_required("customer", "owner")
def customer_page():
    ensure_data()
    return render_template("customer.html")


@app.get("/simulator")
def simulator_page():
    ensure_data()
    return render_template("simulator.html")


@app.get("/analysis")
def analysis_page():
    ensure_data()
    areas = analysis.build_area_analysis()
    dishes = analysis.build_dish_analysis()
    return render_template(
        "analysis.html",
        areas=areas,
        dishes=dishes,
        areas_json=json.dumps(areas),
        dishes_json=json.dumps(dishes),
    )


@app.get("/guide")
@role_required("owner", "analyst", "customer")
def guide_page():
    return render_template("guide.html")


@app.get("/api/summary")
def api_summary():
    ensure_data()
    return jsonify(analysis.build_summary())


@app.get("/api/restaurants")
def api_restaurants():
    ensure_data()
    return jsonify(db.restaurants())


@app.get("/api/insights")
def api_insights():
    ensure_data()
    try:
        minimum = float(request.args.get("min_similarity", 0.35))
    except (TypeError, ValueError):
        return jsonify({"error": "min_similarity must be a number."}), 400
    if not 0 <= minimum <= 1:
        return jsonify({"error": "min_similarity must be between 0 and 1."}), 400
    insights = [
        {
            **item,
            "shared_items": json.loads(item["shared_items"]),
        }
        for item in db.get_insights()
        if item["similarity"] >= minimum
    ]
    return jsonify(insights)


@app.post("/api/retrain")
@role_required("analyst", "owner")
def api_retrain():
    db.init_db()
    result = analysis.train_and_store()
    return jsonify({"status": "ok", **result})


@app.get("/api/repetitive-areas")
def api_repetitive_areas():
    ensure_data()
    return jsonify(analysis.build_area_repetitiveness())


@app.get("/api/opportunities")
def api_opportunities():
    ensure_data()
    city = request.args.get("city")
    location = request.args.get("location")
    return jsonify(analysis.build_opportunities(city, location))


@app.get("/api/predictions")
def api_predictions():
    ensure_data()
    city = request.args.get("city")
    location = request.args.get("location")
    opportunities = analysis.build_opportunities(city, location)
    repetitive_areas = analysis.build_area_repetitiveness()
    return jsonify({
        "status": "ok",
        "city": city,
        "location": location,
        "opportunities": opportunities,
        "repetitive_areas": repetitive_areas[:8],
        "classification": "ESTIMATED PERFORMANCE PREDICTION",
    })


@app.get("/api/performance")
def api_performance():
    ensure_data()
    return jsonify(analysis.build_performance_summary(request.args.get("city")))


@app.get("/api/model-benchmark")
@role_required("analyst", "owner")
def api_model_benchmark():
    report_path = Path(__file__).resolve().parent / "data" / "processed" / "model_validation_report.json"
    if not report_path.exists():
        return jsonify({"error": "Model benchmark has not been run yet."}), 404
    return jsonify(json.loads(report_path.read_text(encoding="utf-8")))


@app.post("/api/predict-concept")
def api_predict_concept():
    ensure_data()
    payload = request.get_json(silent=True) or {}
    try:
        result = analysis.predict_restaurant_concept(
            city=str(payload.get("city", "")),
            location=str(payload.get("location", "")),
            menu_items=payload.get("menu_items", []),
            price=float(payload["price"]) if payload.get("price") else None,
        )
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    if payload.get("menu_items"):
        result["interest_checks"] = [
            {
                "dish": item,
                **db.dish_interest_summary(item, result["city"], result["location"]),
            }
            for item in result["menu_items"]
        ]
    return jsonify(result)


@app.route("/api/dish-interest", methods=["GET", "POST"])
def api_dish_interest():
    ensure_data()
    if request.method == "GET":
        city = request.args.get("city")
        location = request.args.get("location")
        dish = request.args.get("dish")
        if dish and city and location:
            return jsonify({
                "dish": dish,
                "city": city,
                "location": location,
                **db.dish_interest_summary(dish, city, location),
            })
        return jsonify(analysis.get_community_poll_leaderboard(city, location))

    payload = request.get_json(silent=True) or {}
    dish = " ".join(str(payload.get("dish", "")).split())
    city = " ".join(str(payload.get("city", "")).split())
    location = " ".join(str(payload.get("location", "")).split())
    interested = payload.get("interested")
    if not dish or not city or not location or not isinstance(interested, bool):
        return jsonify(
            {"error": "Dish, city, location, and an interest response are required."}
        ), 400
    user = session.get("user") or {}
    db.add_dish_interest(dish, city, location, interested, user.get("id"))
    summary = db.dish_interest_summary(dish, city, location)
    leaderboard = analysis.get_community_poll_leaderboard(city, location)
    return jsonify(
        {
            "dish": dish,
            "city": city,
            "location": location,
            **summary,
            "leaderboard": leaderboard[:5],
        }
    )


@app.get("/api/analysis/areas")
def api_area_analysis():
    ensure_data()
    return jsonify(analysis.build_area_analysis())


@app.get("/api/analysis/dishes")
def api_dish_analysis():
    ensure_data()
    return jsonify(analysis.build_dish_analysis(
        city=request.args.get("city"), area=request.args.get("area")
    ))


# Descriptive aliases kept for clients that use the feature names directly.
app.add_url_rule("/api/area-wise-analysis", view_func=api_area_analysis)
app.add_url_rule("/api/dish-wise-analysis", view_func=api_dish_analysis)


if __name__ == "__main__":
    ensure_data()
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)), debug=debug)
