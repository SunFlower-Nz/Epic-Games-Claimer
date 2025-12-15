#!/bin/bash
# Epic Games Claimer - Unix Run Script
# Runs the claimer once

cd "$(dirname "$0")/.."

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the claimer
python main.py "$@"
