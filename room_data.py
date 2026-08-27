"""Course-schedule parsing and room availability queries."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
DAY_CODES = dict(zip("MTWRFSU", DAYS))
IGNORED_LOCATIONS = {"", "TBA", "ONLINE", "WEB", "REMOTE", "ARRANGED"}


class ScheduleDataError(ValueError):
    """Raised when schedule source data is missing or inconsistent."""


def parse_clock(value: str) -> int:
    """Convert a 24-hour HH:MM value to minutes after midnight."""
    match = re.fullmatch(r"(\d{2}):(\d{2})", value or "")
    if not match:
        raise ValueError("Time must use HH:MM in 24-hour format")
    hour, minute = map(int, match.groups())
    if hour > 23 or minute > 59:
        raise ValueError("Time must use HH:MM in 24-hour format")
    return hour * 60 + minute


def format_clock(minutes: int) -> str:
    """Format minutes after midnight as HH:MM."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_time_range(value: str) -> tuple[int, int] | None:
    """Parse an NJIT schedule time range such as 8:30 AM - 9:50 AM."""
    if not value or value.strip().upper() in {"TBA", "ARRANGED"}:
        return None
    match = re.fullmatch(
        r"\s*(\d{1,2}):(\d{2})\s*(AM|PM)\s*-\s*"
        r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*",
        value,
        re.IGNORECASE,
    )
    if not match:
        return None

    def to_minutes(hour: str, minute: str, period: str) -> int:
        parsed_hour = int(hour)
        parsed_minute = int(minute)
        if parsed_hour < 1 or parsed_hour > 12 or parsed_minute > 59:
            raise ValueError
        parsed_hour %= 12
        if period.upper() == "PM":
            parsed_hour += 12
        return parsed_hour * 60 + parsed_minute

    try:
        start = to_minutes(match.group(1), match.group(2), match.group(3))
        end = to_minutes(match.group(4), match.group(5), match.group(6))
    except ValueError:
        return None
    return (start, end) if start < end else None


def parse_days(value: str) -> list[str]:
    """Expand NJIT's compact day codes into full weekday names."""
    return [DAY_CODES[code] for code in (value or "").strip().upper() if code in DAY_CODES]


def normalize_course_key(value: str) -> str:
    match = re.fullmatch(r"\s*([A-Z]+)\s*(\d+[A-Z]*)\s*", (value or "").upper())
    return f"{match.group(1)} {match.group(2)}" if match else (value or "").strip()


def normalize_location(value: str) -> str | None:
    location = " ".join((value or "").upper().split())
    if location in IGNORED_LOCATIONS or location.startswith("ONLINE"):
        return None
    if len(location.split()) < 2:
        return None
    return location


def term_label(term: str) -> str:
    """Translate NJIT Banner term codes, for example 202690 -> Fall 2026."""
    if not re.fullmatch(r"\d{6}", term or ""):
        return term or "Unknown term"
    season = {"10": "Spring", "50": "Summer", "90": "Fall"}.get(term[-2:], "Term")
    return f"{season} {term[:4]}"


def _read_source_updated_at(source_dir: Path) -> str | None:
    metadata_path = source_dir / "_update_metadata.txt"
    if not metadata_path.exists():
        return None
    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Last Updated:"):
            return line.partition(":")[2].strip() or None
    return None


def _dataset_timestamp(source_dir: Path, csv_files: list[Path]) -> str:
    """Return a source-derived timestamp so repeated builds are reproducible."""
    source_updated_at = _read_source_updated_at(source_dir)
    if source_updated_at:
        suffix = "" if source_updated_at.endswith(("Z", "+00:00")) else "Z"
        return f"{source_updated_at}{suffix}"
    newest_mtime = max(path.stat().st_mtime for path in csv_files)
    return datetime.fromtimestamp(newest_mtime, timezone.utc).isoformat().replace("+00:00", "Z")


def _iter_rows(csv_files: Iterable[Path]) -> Iterable[dict[str, str]]:
    for csv_file in csv_files:
        with csv_file.open(newline="", encoding="utf-8-sig") as handle:
            yield from csv.DictReader(handle)


def build_schedule_dataset(source_dir: str | Path, term: str | None = None) -> dict[str, Any]:
    """Build a compact, single-term room schedule from NJIT course CSV files."""
    source_path = Path(source_dir)
    csv_files = sorted(source_path.glob("*.csv"))
    if not csv_files:
        raise ScheduleDataError(f"No CSV files found in {source_path}")

    term_counts = Counter(
        row.get("Term", "").strip()
        for row in _iter_rows(csv_files)
        if row.get("Term", "").strip()
    )
    if not term_counts:
        raise ScheduleDataError("The source files contain no term information")
    selected_term = term or max(term_counts)
    if selected_term not in term_counts:
        raise ScheduleDataError(f"Term {selected_term} was not found in the source files")

    rooms: dict[str, dict[str, Any]] = {}
    seen_slots: set[tuple[Any, ...]] = set()
    skipped = Counter()

    for row in _iter_rows(csv_files):
        if row.get("Term", "").strip() != selected_term:
            skipped["other_term"] += 1
            continue
        if row.get("Status", "").strip().lower() in {"cancelled", "canceled"}:
            skipped["cancelled"] += 1
            continue

        location = normalize_location(row.get("Location", ""))
        parsed_range = parse_time_range(row.get("Times", ""))
        days = parse_days(row.get("Days", ""))
        if not location:
            skipped["no_physical_room"] += 1
            continue
        if not parsed_range or not days:
            skipped["no_fixed_meeting"] += 1
            continue

        start_min, end_min = parsed_range
        building, room_name = location.split(maxsplit=1)
        room = rooms.setdefault(
            location,
            {"building": building, "room": room_name, "slots": []},
        )
        for day in days:
            signature = (
                location,
                day,
                start_min,
                end_min,
                row.get("CRN", "").strip(),
            )
            if signature in seen_slots:
                skipped["duplicate"] += 1
                continue
            seen_slots.add(signature)
            room["slots"].append(
                {
                    "day": day,
                    "start_min": start_min,
                    "end_min": end_min,
                    "start_time": format_clock(start_min),
                    "end_time": format_clock(end_min),
                    "course": normalize_course_key(row.get("Course", "")),
                    "title": row.get("Title", "").strip(),
                    "section": row.get("Section", "").strip(),
                    "crn": row.get("CRN", "").strip(),
                    "instructor": row.get("Instructor", "").strip(),
                }
            )

    for room in rooms.values():
        room["slots"].sort(key=lambda slot: (DAYS.index(slot["day"]), slot["start_min"]))

    room_list = sorted(rooms)
    building_counts = Counter(rooms[name]["building"] for name in room_list)
    source_updated_at = _read_source_updated_at(source_path)
    return {
        "metadata": {
            "schema_version": 2,
            "term": selected_term,
            "term_name": term_label(selected_term),
            "generated_at": _dataset_timestamp(source_path, csv_files),
            "source_updated_at": source_updated_at,
            "source_file_count": len(csv_files),
            "source_row_count": term_counts[selected_term],
            "ignored_term_rows": sum(
                count for candidate, count in term_counts.items() if candidate != selected_term
            ),
            "skipped_rows": dict(skipped),
            "source_repository": "donovanmchenry/njitschedulepro",
        },
        "rooms": {name: rooms[name] for name in room_list},
        "room_list": room_list,
        "buildings": [
            {"code": code, "room_count": building_counts[code]}
            for code in sorted(building_counts)
        ],
    }


def save_schedule_dataset(dataset: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataset, separators=(",", ":")), encoding="utf-8")


def load_schedule_dataset(path: str | Path) -> dict[str, Any]:
    data_path = Path(path)
    if not data_path.exists():
        raise ScheduleDataError(
            f"Schedule data was not found at {data_path}. Run build_schedule_data.py first."
        )
    dataset = json.loads(data_path.read_text(encoding="utf-8"))
    if dataset.get("metadata", {}).get("schema_version") != 2:
        raise ScheduleDataError("Schedule data uses an unsupported schema version")
    return dataset


def room_schedule_by_day(room: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    schedule = {day: [] for day in DAYS}
    for slot in room["slots"]:
        schedule[slot["day"]].append(slot)
    return schedule


def find_room_availability(
    dataset: dict[str, Any],
    *,
    day: str,
    start_min: int,
    duration_minutes: int,
    building: str = "",
    query: str = "",
    sort: str = "longest",
) -> dict[str, Any]:
    """Find rooms free for the full requested interval."""
    end_min = start_min + duration_minutes
    if end_min > 24 * 60:
        raise ValueError("The requested duration extends past midnight")

    normalized_building = building.strip().upper()
    normalized_query = query.strip().upper()
    available: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []

    for room_name, room in dataset["rooms"].items():
        if normalized_building and room["building"] != normalized_building:
            continue
        if normalized_query and normalized_query not in room_name:
            continue

        slots = [slot for slot in room["slots"] if slot["day"] == day]
        conflict = next(
            (slot for slot in slots if slot["start_min"] < end_min and slot["end_min"] > start_min),
            None,
        )
        next_class = next((slot for slot in slots if slot["start_min"] >= start_min), None)

        base = {
            "room": room_name,
            "building": room["building"],
            "room_number": room["room"],
        }
        if conflict is None:
            free_minutes = next_class["start_min"] - start_min if next_class else None
            available.append(
                {
                    **base,
                    "available": True,
                    "free_minutes": free_minutes,
                    "available_until": next_class["start_time"] if next_class else None,
                    "next_class": next_class,
                }
            )
            continue

        occupied_now = conflict["start_min"] <= start_min < conflict["end_min"]
        unavailable.append(
            {
                **base,
                "available": False,
                "reason": "occupied" if occupied_now else "starts_soon",
                "blocking_class": conflict,
                "available_after": conflict["end_time"],
            }
        )

    if sort == "room":
        available.sort(key=lambda item: item["room"])
    elif sort == "soonest":
        available.sort(
            key=lambda item: (
                item["free_minutes"] is None,
                item["free_minutes"] or 10**9,
                item["room"],
            )
        )
    else:
        available.sort(
            key=lambda item: (
                item["free_minutes"] is not None,
                -(item["free_minutes"] or 0),
                item["room"],
            )
        )
    unavailable.sort(key=lambda item: item["room"])

    occupied_count = sum(item["reason"] == "occupied" for item in unavailable)
    starts_soon_count = len(unavailable) - occupied_count
    return {
        "day": day,
        "start_time": format_clock(start_min),
        "end_time": format_clock(end_min),
        "duration_minutes": duration_minutes,
        "building": normalized_building,
        "query": query.strip(),
        "available_rooms": available,
        "unavailable_rooms": unavailable,
        "summary": {
            "total_rooms": len(available) + len(unavailable),
            "available": len(available),
            "occupied": occupied_count,
            "starts_soon": starts_soon_count,
        },
    }
