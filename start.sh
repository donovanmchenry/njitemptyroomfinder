#!/bin/bash
# Start script for Empty Room Finder

echo "Starting Empty Room Finder..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if schedule_data.json exists
if [ ! -f "schedule_data.json" ]; then
    echo "Schedule data not found. Running parser..."
    python3 parse_schedules.py
    echo ""
fi

# Start Flask app
echo "Starting web server on http://localhost:5001"
python3 app.py
