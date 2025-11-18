# Empty Room Finder

A web application that helps you find available classrooms at your school at any given time. Simply enter a day and time, and the app will show you all empty rooms, along with information about when they'll be occupied next.

**Live Demo:** https://njitemptyroomfinder.onrender.com/

## Features

- **Real-time Room Availability**: Find empty rooms instantly by selecting a day and time
- **Next Class Information**: See when the next class is scheduled in each available room
- **Comprehensive Data**: Tracks 184 unique rooms and 2,210 courses
- **User-Friendly Interface**: Modern, responsive web interface with intuitive design
- **Detailed Statistics**: View summary stats showing total, available, and occupied rooms
- **Room Schedules**: Each room card shows upcoming classes and current occupancy

## Project Structure

```
emptyroom/
├── classes/                    # CSV files with course schedules
├── templates/
│   └── index.html             # Frontend interface
├── app.py                     # Flask backend API
├── parse_schedules.py         # CSV parser script
├── schedule_data.json         # Parsed schedule data
├── requirements.txt           # Python dependencies
├── start.sh                   # Startup script
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.7+
- pip

### Setup

1. Clone or navigate to the project directory:
```bash
cd emptyroom
```

2. Create a virtual environment:
```bash
python3 -m venv venv
```

3. Activate the virtual environment:
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

Use the provided start script:
```bash
./start.sh
```

This will:
1. Activate the virtual environment
2. Parse the CSV files if needed
3. Start the web server on http://localhost:5000

### Manual Start

1. Parse the course schedules (if not already done):
```bash
python3 parse_schedules.py
```

2. Start the Flask application:
```bash
python3 app.py
```

3. Open your browser and go to:
```
http://localhost:5001
```

### Using the Application

1. **Select a Day**: Choose the day of the week you want to check
2. **Select a Time**: Enter the time you want to find available rooms (24-hour format)
3. **Click "Find Rooms"**: View all available and occupied rooms

The app will show you:
- Total number of rooms
- Number of available rooms
- Number of occupied rooms
- Details for each available room including when the next class starts
- Details for occupied rooms showing the current class

## API Endpoints

### `GET /`
Serves the main web interface

### `GET /api/rooms`
Returns a list of all rooms

**Response:**
```json
{
  "rooms": ["CKB 114", "FMH 307", ...],
  "total": 184
}
```

### `POST /api/available-rooms`
Find available rooms for a given day and time

**Request Body:**
```json
{
  "day": "Monday",
  "time": "18:00"
}
```

**Response:**
```json
{
  "day": "Monday",
  "time": "18:00",
  "available_rooms": [
    {
      "room": "CKB 114",
      "next_class": {
        "day": "Monday",
        "start_time": "20:00",
        "end_time": "21:30",
        "course": "COM312 - EFFECTIVE COMMUNICATION",
        "section": "101"
      }
    }
  ],
  "occupied_rooms": [...],
  "summary": {
    "total_rooms": 184,
    "available": 150,
    "occupied": 34
  }
}
```

### `GET /api/room/<room_name>`
Get the full schedule for a specific room

**Response:**
```json
{
  "room": "FMH 307",
  "schedule": {
    "Monday": [
      {
        "day": "Monday",
        "start_time": "08:30",
        "end_time": "09:50",
        "course": "COM230 - INTRODUCTION TO FILM",
        "section": "001"
      }
    ],
    "Tuesday": [...],
    ...
  }
}
```

## Data Format

### Input CSV Files

The application expects CSV files in the `classes/` directory with the following columns:
- Term
- Course
- Title
- Section
- CRN
- Days (e.g., "MW", "TR", "WF")
- Times (e.g., "8:30 AM - 9:50 AM")
- Location (room number)
- Status
- Max
- Now
- Instructor
- Delivery Mode
- Credits
- Info
- Comments

### Day Codes

- M = Monday
- T = Tuesday
- W = Wednesday
- R = Thursday
- F = Friday
- S = Saturday
- U = Sunday

## Features in Detail

### Available Rooms Display
- Shows all rooms that are currently empty
- Displays the next scheduled class for each room
- Shows "Free for the rest of the day" if no more classes are scheduled

### Occupied Rooms Display
- Lists all currently occupied rooms
- Shows the current class information
- Displays start and end times

### Smart Parsing
- Automatically skips cancelled courses
- Filters out online courses (no physical room needed)
- Handles TBA times and locations gracefully

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Data Processing**: Python CSV module
- **API**: RESTful JSON API

## Example Use Cases

1. **Finding a Study Space**: Check if there's an empty classroom to study during your break
2. **Meeting Planning**: Find available rooms for group meetings
3. **Event Planning**: Locate rooms for events or activities
4. **Campus Navigation**: See which areas of campus are busy at different times

## Notes

- The app runs in debug mode by default (for development)
- Data is loaded from `schedule_data.json` on startup
- Times are in 24-hour format (e.g., 18:00 for 6:00 PM)
- The app automatically defaults to the current day and time

## Future Enhancements

Potential features to add:
- Filter rooms by building
- Filter by room capacity
- Save favorite rooms
- Week view showing room availability across multiple days
- Email/SMS notifications for when rooms become available
- Mobile app version
- Integration with campus calendar systems
