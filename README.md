# NJIT Empty Room Finder

A fast, schedule-based tool for finding NJIT classrooms that stay free for the full time you need.

The app uses the current Schedule Pro course export, keeps one semester in its generated dataset, and distinguishes rooms that are occupied now from rooms with a class starting during the requested window.

## What it does

- Checks availability for a selected day, start time, and duration
- Filters by building or room name
- Shows occupied rooms and rooms whose next class starts too soon
- Opens a room's full weekly class schedule
- Defaults to dark mode and adapts to desktop and mobile screens
- Refreshes its committed schedule data from Schedule Pro every four hours

Availability is based on the published course schedule. Campus events, closures, reservations, and last-minute changes may not appear.

## Local setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
./start.sh
```

Open `http://127.0.0.1:5001`.

The repository includes `data/schedule_data.json`, so a fresh checkout starts without a separate data build.

## Refresh schedule data

Point the builder at a checkout of Schedule Pro:

```bash
python build_schedule_data.py \
  --source ../njitschedulepro/courseschedules \
  --output data/schedule_data.json
```

The builder selects the highest NJIT Banner term code by default. To build a specific term, pass `--term 202690`.

The scheduled GitHub Actions workflow clones Schedule Pro, rebuilds the artifact, and commits only when the source data changed.

## API

### `GET /health`

Returns service health, active term, and room count.

### `GET /api/meta`

Returns dataset term, provenance, source update time, and room/building totals.

### `GET /api/buildings`

Returns building codes and room counts.

### `POST /api/available-rooms`

Example request:

```json
{
  "day": "Monday",
  "time": "13:00",
  "duration_minutes": 60,
  "building": "CKB",
  "query": "214",
  "sort": "longest"
}
```

`duration_minutes` must be between 15 and 480. Sort values are `longest`, `soonest`, and `room`.

### `GET /api/room/<room_name>`

Returns the room's class meetings grouped by day.

## Tests

```bash
pytest -q
```

The suite covers parsing, term selection, reproducible generation, conflict boundaries, duration handling, filters, API validation, cache behavior, and response security headers.

## Deployment

`render.yaml` and `start.sh` provide a production Gunicorn setup with a health check. The generated data is loaded once per worker at startup, so normal room searches do not read CSV files or call an upstream service.
