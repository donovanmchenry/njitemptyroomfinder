"""Flask application for finding empty NJIT rooms."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from room_data import (
    DAYS,
    ScheduleDataError,
    find_room_availability,
    load_schedule_dataset,
    parse_clock,
    room_schedule_by_day,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = ROOT / "data" / "schedule_data.json"
VALID_SORTS = {"longest", "soonest", "room"}


def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def create_app(data_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    resolved_data_path = Path(
        data_path or os.getenv("SCHEDULE_DATA_FILE", str(DEFAULT_DATA_PATH))
    )
    dataset = load_schedule_dataset(resolved_data_path)
    app.config["SCHEDULE_DATA"] = dataset

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "healthy",
                "term": dataset["metadata"]["term"],
                "rooms": len(dataset["room_list"]),
            }
        )

    @app.get("/api/meta")
    def get_meta():
        response = jsonify(
            {
                "metadata": dataset["metadata"],
                "room_count": len(dataset["room_list"]),
                "building_count": len(dataset["buildings"]),
            }
        )
        response.headers["Cache-Control"] = "public, max-age=300"
        return response

    @app.get("/api/rooms")
    def get_rooms():
        response = jsonify({"rooms": dataset["room_list"], "total": len(dataset["room_list"])})
        response.headers["Cache-Control"] = "public, max-age=300"
        return response

    @app.get("/api/buildings")
    def get_buildings():
        response = jsonify(
            {"buildings": dataset["buildings"], "total": len(dataset["buildings"])}
        )
        response.headers["Cache-Control"] = "public, max-age=300"
        return response

    @app.post("/api/available-rooms")
    def get_available_rooms():
        payload: dict[str, Any] | None = request.get_json(silent=True)
        if not isinstance(payload, dict) or not payload:
            return _error("Send a JSON body with day and time")

        day = payload.get("day")
        if day not in DAYS:
            return _error("Choose a valid day of the week")
        try:
            start_min = parse_clock(payload.get("time", ""))
            duration = int(payload.get("duration_minutes", 60))
        except (TypeError, ValueError) as exc:
            return _error(str(exc) if str(exc) else "Choose a valid duration")
        if duration < 15 or duration > 480:
            return _error("Duration must be between 15 minutes and 8 hours")

        building = str(payload.get("building", ""))
        valid_buildings = {item["code"] for item in dataset["buildings"]}
        if building and building.upper() not in valid_buildings:
            return _error("Choose a valid building")
        sort = str(payload.get("sort", "longest"))
        if sort not in VALID_SORTS:
            return _error("Choose a valid sort order")

        try:
            result = find_room_availability(
                dataset,
                day=day,
                start_min=start_min,
                duration_minutes=duration,
                building=building,
                query=str(payload.get("query", "")),
                sort=sort,
            )
        except ValueError as exc:
            return _error(str(exc))
        response = jsonify(result)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/room/<path:room_name>")
    def get_room_schedule(room_name: str):
        normalized_name = " ".join(room_name.upper().split())
        room = dataset["rooms"].get(normalized_name)
        if not room:
            return _error("Room not found", 404)
        return jsonify(
            {
                "room": normalized_name,
                "building": room["building"],
                "schedule": room_schedule_by_day(room),
            }
        )

    return app


try:
    app = create_app()
except ScheduleDataError as exc:
    raise RuntimeError(str(exc)) from exc


if __name__ == "__main__":
    metadata = app.config["SCHEDULE_DATA"]["metadata"]
    print(f"NJIT Empty Room Finder: {metadata['term_name']}")
    app.run(
        debug=os.getenv("FLASK_DEBUG", "").lower() in {"1", "true"},
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5001")),
    )
