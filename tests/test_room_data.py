import csv
import json

import pytest

from build_schedule_data import refresh_schedule

from room_data import (
    build_schedule_dataset,
    find_room_availability,
    parse_clock,
    parse_days,
    parse_time_range,
    save_schedule_dataset,
    ScheduleDataError,
)


FIELDNAMES = [
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
]


def write_schedule(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def row(**overrides):
    values = {
        "Term": "202690",
        "Course": "CS 100",
        "Title": "Roadmap to Computing",
        "Section": "001",
        "CRN": "10001",
        "Days": "M",
        "Times": "9:00 AM - 10:00 AM",
        "Location": "CKB 101",
        "Status": "Open",
        "Instructor": "Staff",
    }
    values.update(overrides)
    return values


@pytest.fixture
def dataset(tmp_path):
    rows = [
        row(),
        row(CRN="10002", Location="CKB 102", Times="10:00 AM - 11:00 AM"),
        row(CRN="10003", Location="GITC 1100", Times="1:00 PM - 2:00 PM"),
    ]
    write_schedule(tmp_path / "courses.csv", rows)
    return build_schedule_dataset(tmp_path)


def test_time_and_day_parsing():
    assert parse_clock("13:45") == 825
    assert parse_time_range("12:00 PM - 1:20 PM") == (720, 800)
    assert parse_time_range("TBA") is None
    assert parse_days("MWR") == ["Monday", "Wednesday", "Thursday"]
    with pytest.raises(ValueError):
        parse_clock("25:00")


def test_builder_selects_latest_term_and_filters_non_rooms(tmp_path):
    rows = [
        row(Term="202590", CRN="90001"),
        row(),
        row(CRN="10004", Location="ONLINE"),
        row(CRN="10005", Location="CKB 105", Status="Cancelled"),
        row(CRN="10006", Location="CKB 106", Times="TBA"),
    ]
    write_schedule(tmp_path / "courses.csv", rows)
    built = build_schedule_dataset(tmp_path)

    assert built["metadata"]["term"] == "202690"
    assert built["metadata"]["term_name"] == "Fall 2026"
    assert built["room_list"] == ["CKB 101"]
    assert built["metadata"]["skipped_rows"] == {
        "no_physical_room": 1,
        "cancelled": 1,
        "no_fixed_meeting": 1,
        "other_term": 1,
    }


def test_builder_is_reproducible(tmp_path):
    write_schedule(tmp_path / "courses.csv", [row()])
    (tmp_path / "_update_metadata.txt").write_text(
        "Last Updated: 2026-08-27T18:41:05\n", encoding="utf-8"
    )

    first = build_schedule_dataset(tmp_path)
    second = build_schedule_dataset(tmp_path)

    assert first == second
    assert first["metadata"]["generated_at"] == "2026-08-27T18:41:05Z"


def test_duration_marks_future_conflict_as_unavailable(dataset):
    result = find_room_availability(
        dataset,
        day="Monday",
        start_min=parse_clock("09:30"),
        duration_minutes=60,
    )

    assert [room["room"] for room in result["available_rooms"]] == ["GITC 1100"]
    reasons = {room["room"]: room["reason"] for room in result["unavailable_rooms"]}
    assert reasons == {"CKB 101": "occupied", "CKB 102": "starts_soon"}
    assert result["summary"] == {
        "total_rooms": 3,
        "available": 1,
        "occupied": 1,
        "starts_soon": 1,
    }


def test_end_boundary_is_available_and_filters_work(dataset):
    result = find_room_availability(
        dataset,
        day="Monday",
        start_min=parse_clock("10:00"),
        duration_minutes=30,
        building="ckb",
        query="101",
    )

    assert [room["room"] for room in result["available_rooms"]] == ["CKB 101"]
    assert result["unavailable_rooms"] == []


def test_request_cannot_extend_past_midnight(dataset):
    with pytest.raises(ValueError, match="past midnight"):
        find_room_availability(
            dataset,
            day="Monday",
            start_min=parse_clock("23:30"),
            duration_minutes=60,
        )


@pytest.fixture
def refresh_files(tmp_path, dataset):
    source = tmp_path / "upstream"
    source.mkdir()
    output = tmp_path / "schedule.json"
    save_schedule_dataset(dataset, output)
    config = tmp_path / "refresh.json"
    config.write_text(json.dumps({
        "active_term": "202690", "minimum_rooms": 1, "minimum_buildings": 1,
    }))
    return source, output, config


def test_refresh_keeps_active_semester_when_newer_term_exists(refresh_files):
    source, output, config = refresh_files
    write_schedule(source / "courses.csv", [
        row(), row(Location="CKB 102"), row(Location="GITC 1100"),
        row(Term="202695", Location="CKB 999"),
    ])
    result = refresh_schedule(source, output, config)
    assert result["metadata"]["term"] == "202690"
    assert "CKB 999" not in result["rooms"]
    assert json.loads(output.read_text()) == result


def test_refresh_preserves_dataset_when_active_semester_is_missing(refresh_files):
    source, output, config = refresh_files
    original = output.read_bytes()
    write_schedule(source / "courses.csv", [row(Term="202695")])
    with pytest.raises(ScheduleDataError, match="202690 was not found"):
        refresh_schedule(source, output, config)
    assert output.read_bytes() == original


@pytest.mark.parametrize("locations", [
    ["CKB 101", "GITC 1100"],  # Too many rooms disappeared.
    ["CKB 101", "CKB 102", "CKB 103"],  # Building coverage collapsed.
])
def test_refresh_rejects_coverage_loss(refresh_files, locations):
    source, output, config = refresh_files
    original = output.read_bytes()
    write_schedule(source / "courses.csv", [row(Location=value) for value in locations])
    with pytest.raises(ScheduleDataError, match="Refusing incomplete"):
        refresh_schedule(source, output, config)
    assert output.read_bytes() == original


def test_refresh_checks_minimums_even_without_previous_dataset(refresh_files):
    source, output, config = refresh_files
    output.unlink()
    config.write_text(json.dumps({
        "active_term": "202690", "minimum_rooms": 150, "minimum_buildings": 14,
    }))
    write_schedule(source / "courses.csv", [row()])
    with pytest.raises(ScheduleDataError, match="Refusing incomplete"):
        refresh_schedule(source, output, config)
    assert not output.exists()
