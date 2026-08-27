import csv

import pytest

from app import create_app
from room_data import build_schedule_dataset, save_schedule_dataset


@pytest.fixture
def client(tmp_path):
    csv_path = tmp_path / "courses.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Term",
                "Course",
                "Title",
                "Section",
                "CRN",
                "Days",
                "Times",
                "Location",
                "Status",
                "Instructor",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Term": "202690",
                "Course": "CS 100",
                "Title": "Roadmap to Computing",
                "Section": "001",
                "CRN": "10001",
                "Days": "MW",
                "Times": "9:00 AM - 10:00 AM",
                "Location": "CKB 101",
                "Status": "Open",
                "Instructor": "Staff",
            }
        )
    data_path = tmp_path / "schedule.json"
    save_schedule_dataset(build_schedule_dataset(tmp_path), data_path)
    application = create_app(data_path)
    application.config.update(TESTING=True)
    return application.test_client()


def test_health_and_metadata(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "healthy", "term": "202690", "rooms": 1}

    metadata = client.get("/api/meta")
    assert metadata.get_json()["metadata"]["term_name"] == "Fall 2026"
    assert metadata.headers["Cache-Control"] == "public, max-age=300"


def test_availability_endpoint_checks_full_duration(client):
    response = client.post(
        "/api/available-rooms",
        json={"day": "Monday", "time": "08:30", "duration_minutes": 60},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["available_rooms"] == []
    assert payload["unavailable_rooms"][0]["reason"] == "starts_soon"
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"day": "Funday", "time": "09:00"}, "valid day"),
        ({"day": "Monday", "time": "nine"}, "HH:MM"),
        ({"day": "Monday", "time": "09:00", "duration_minutes": 10}, "between 15"),
        ({"day": "Monday", "time": "09:00", "building": "NOPE"}, "valid building"),
    ],
)
def test_availability_validation(client, payload, message):
    response = client.post("/api/available-rooms", json=payload)
    assert response.status_code == 400
    assert message in response.get_json()["error"]


def test_availability_rejects_non_object_json(client):
    response = client.post("/api/available-rooms", json=["Monday", "09:00"])
    assert response.status_code == 400
    assert response.get_json()["error"] == "Send a JSON body with day and time"


def test_room_schedule_and_security_headers(client):
    response = client.get("/api/room/ckb%20101")
    payload = response.get_json()

    assert payload["room"] == "CKB 101"
    assert len(payload["schedule"]["Monday"]) == 1
    assert len(payload["schedule"]["Wednesday"]) == 1
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_unknown_room_is_404(client):
    response = client.get("/api/room/CKB%20999")
    assert response.status_code == 404
