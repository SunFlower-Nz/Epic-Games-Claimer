#!/bin/bash
# Epic Games Claimer - Unix Scheduled Run Script
# Runs the claimer in scheduled mode (daily at 12:00)

cd "$(dirname "$0")/.."

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run in scheduled mode
python main.py --schedule
