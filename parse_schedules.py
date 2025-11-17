#!/usr/bin/env python3
"""
Parse course schedule CSV files to extract room availability data
"""

import csv
import json
import os
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Set


def parse_time(time_str: str) -> tuple[time, time] | None:
    """
    Parse time string like '8:30 AM - 9:50 AM' into start and end time objects
    Returns None if parsing fails or time is TBA
    """
    if not time_str or time_str.strip() == 'TBA':
        return None

    try:
        parts = time_str.split(' - ')
        if len(parts) != 2:
            return None

        start_str, end_str = parts
        start_time = datetime.strptime(start_str.strip(), '%I:%M %p').time()
        end_time = datetime.strptime(end_str.strip(), '%I:%M %p').time()

        return start_time, end_time
    except (ValueError, AttributeError):
        return None


def parse_days(days_str: str) -> List[str]:
    """
    Parse days string like 'MWF' or 'TR' into list of day names
    M=Monday, T=Tuesday, W=Wednesday, R=Thursday, F=Friday, S=Saturday
    """
    if not days_str or days_str.strip() == '':
        return []

    day_map = {
        'M': 'Monday',
        'T': 'Tuesday',
        'W': 'Wednesday',
        'R': 'Thursday',
        'F': 'Friday',
        'S': 'Saturday',
        'U': 'Sunday'
    }

    days = []
    for char in days_str.strip():
        if char in day_map:
            days.append(day_map[char])

    return days


def parse_csv_files(classes_dir: str = 'classes') -> Dict:
    """
    Parse all CSV files in the classes directory and extract room schedules

    Returns a dictionary with:
    - rooms: dict mapping room names to their schedule
    - courses: list of all courses with their details
    """
    classes_path = Path(classes_dir)
    csv_files = list(classes_path.glob('*.csv'))

    print(f"Found {len(csv_files)} CSV files to parse")

    all_rooms = {}  # room_name -> list of occupied time slots
    all_courses = []
    rooms_set = set()

    for csv_file in csv_files:
        print(f"Parsing {csv_file.name}...")

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Skip cancelled courses or online courses
                    if row.get('Status') == 'Cancelled':
                        continue
                    if 'Online' in row.get('Delivery Mode', ''):
                        continue

                    location = row.get('Location', '').strip()
                    days_str = row.get('Days', '').strip()
                    times_str = row.get('Times', '').strip()

                    # Skip if no location or it's TBA/empty
                    if not location or location == '' or location == 'TBA':
                        continue

                    # Parse times
                    time_range = parse_time(times_str)
                    if not time_range:
                        continue

                    start_time, end_time = time_range

                    # Parse days
                    days = parse_days(days_str)
                    if not days:
                        continue

                    rooms_set.add(location)

                    # Create course entry
                    course_entry = {
                        'course': row.get('Course', ''),
                        'title': row.get('Title', ''),
                        'section': row.get('Section', ''),
                        'crn': row.get('CRN', ''),
                        'days': days,
                        'start_time': start_time.strftime('%H:%M'),
                        'end_time': end_time.strftime('%H:%M'),
                        'location': location,
                        'instructor': row.get('Instructor', ''),
                    }

                    all_courses.append(course_entry)

                    # Add to room schedule
                    if location not in all_rooms:
                        all_rooms[location] = []

                    for day in days:
                        all_rooms[location].append({
                            'day': day,
                            'start_time': start_time.strftime('%H:%M'),
                            'end_time': end_time.strftime('%H:%M'),
                            'course': f"{row.get('Course', '')} - {row.get('Title', '')}",
                            'section': row.get('Section', '')
                        })

        except Exception as e:
            print(f"Error parsing {csv_file.name}: {e}")
            continue

    print(f"\nParsing complete!")
    print(f"Total unique rooms found: {len(rooms_set)}")
    print(f"Total courses parsed: {len(all_courses)}")

    return {
        'rooms': all_rooms,
        'courses': all_courses,
        'room_list': sorted(list(rooms_set))
    }


def save_schedule_data(data: Dict, output_file: str = 'schedule_data.json'):
    """Save parsed schedule data to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"\nSchedule data saved to {output_file}")


if __name__ == '__main__':
    # Parse all CSV files
    schedule_data = parse_csv_files()

    # Save to JSON
    save_schedule_data(schedule_data)

    # Print some sample rooms
    print("\nSample rooms:")
    for room in list(schedule_data['room_list'])[:10]:
        print(f"  - {room}")
