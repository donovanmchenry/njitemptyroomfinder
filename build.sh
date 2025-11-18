#!/bin/bash
# Build script for Render deployment

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Parsing course schedules..."
python parse_schedules.py

echo "Build complete!"
