#!/bin/sh
set -eu

if [ ! -f data/schedule_data.json ]; then
    echo "Missing data/schedule_data.json. Run build_schedule_data.py with a schedule source first." >&2
    exit 1
fi

exec gunicorn app:app \
    --bind "0.0.0.0:${PORT:-5001}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads "${WEB_THREADS:-4}" \
    --timeout 30
