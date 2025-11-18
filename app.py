#!/usr/bin/env python3
"""
Flask API for finding empty rooms
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, time
import json
import os
from typing import List, Dict

app = Flask(__name__)
CORS(app)

# Load schedule data
with open('schedule_data.json', 'r') as f:
    SCHEDULE_DATA = json.load(f)


def time_str_to_minutes(time_str: str) -> int:
    """Convert time string 'HH:MM' to minutes since midnight"""
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes


def is_room_occupied(room_schedule: List[Dict], day: str, check_time: str) -> tuple[bool, Dict | None]:
    """
    Check if a room is occupied at the given day and time
    Returns (is_occupied, occupying_course_info)
    """
    check_minutes = time_str_to_minutes(check_time)

    for slot in room_schedule:
        if slot['day'] != day:
            continue

        start_minutes = time_str_to_minutes(slot['start_time'])
        end_minutes = time_str_to_minutes(slot['end_time'])

        # Check if the time falls within this slot
        if start_minutes <= check_minutes < end_minutes:
            return True, slot

    return False, None


def find_next_class(room_schedule: List[Dict], day: str, check_time: str) -> Dict | None:
    """Find the next class in this room after the given time"""
    check_minutes = time_str_to_minutes(check_time)
    next_class = None
    min_diff = float('inf')

    for slot in room_schedule:
        if slot['day'] != day:
            continue

        start_minutes = time_str_to_minutes(slot['start_time'])

        if start_minutes > check_minutes:
            diff = start_minutes - check_minutes
            if diff < min_diff:
                min_diff = diff
                next_class = slot

    return next_class


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/rooms', methods=['GET'])
def get_all_rooms():
    """Get list of all rooms"""
    return jsonify({
        'rooms': SCHEDULE_DATA['room_list'],
        'total': len(SCHEDULE_DATA['room_list'])
    })


@app.route('/api/available-rooms', methods=['POST'])
def get_available_rooms():
    """
    Find available rooms for a given day and time

    Expected JSON body:
    {
        "day": "Monday",
        "time": "18:00"  # 24-hour format HH:MM
    }
    """
    data = request.get_json()

    if not data or 'day' not in data or 'time' not in data:
        return jsonify({'error': 'Missing day or time parameter'}), 400

    day = data['day']
    check_time = data['time']

    # Validate day
    valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    if day not in valid_days:
        return jsonify({'error': f'Invalid day. Must be one of {valid_days}'}), 400

    # Validate time format
    try:
        time_str_to_minutes(check_time)
    except (ValueError, AttributeError):
        return jsonify({'error': 'Invalid time format. Use HH:MM in 24-hour format'}), 400

    available_rooms = []
    occupied_rooms = []

    for room, schedule in SCHEDULE_DATA['rooms'].items():
        is_occupied, occupying_course = is_room_occupied(schedule, day, check_time)

        if is_occupied:
            occupied_rooms.append({
                'room': room,
                'current_class': occupying_course
            })
        else:
            next_class = find_next_class(schedule, day, check_time)
            available_rooms.append({
                'room': room,
                'next_class': next_class
            })

    # Sort available rooms alphabetically
    available_rooms.sort(key=lambda x: x['room'])
    occupied_rooms.sort(key=lambda x: x['room'])

    return jsonify({
        'day': day,
        'time': check_time,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms,
        'summary': {
            'total_rooms': len(SCHEDULE_DATA['room_list']),
            'available': len(available_rooms),
            'occupied': len(occupied_rooms)
        }
    })


@app.route('/api/room/<room_name>', methods=['GET'])
def get_room_schedule(room_name):
    """Get the full schedule for a specific room"""
    if room_name not in SCHEDULE_DATA['rooms']:
        return jsonify({'error': 'Room not found'}), 404

    schedule = SCHEDULE_DATA['rooms'][room_name]

    # Organize by day
    by_day = {
        'Monday': [],
        'Tuesday': [],
        'Wednesday': [],
        'Thursday': [],
        'Friday': [],
        'Saturday': [],
        'Sunday': []
    }

    for slot in schedule:
        by_day[slot['day']].append(slot)

    # Sort each day by start time
    for day in by_day:
        by_day[day].sort(key=lambda x: x['start_time'])

    return jsonify({
        'room': room_name,
        'schedule': by_day
    })


if __name__ == '__main__':
    print("Starting Empty Room Finder API...")
    print(f"Loaded {len(SCHEDULE_DATA['room_list'])} rooms")
    print(f"Loaded {len(SCHEDULE_DATA['courses'])} courses")

    # Use PORT environment variable for production (e.g., Render)
    # Fall back to 5001 for local development
    port = int(os.environ.get('PORT', 5001))

    print("\n" + "="*50)
    print(f"Access the app at: http://localhost:{port}")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=port)
