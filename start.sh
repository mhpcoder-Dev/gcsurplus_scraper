#!/bin/bash
# Quick Start Script for FastAPI Backend (Linux/Mac)
# Handles everything automatically

echo ""
echo "============================================================"
echo "  Starting Auction Scraper Backend"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python is not installed"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

echo "[OK] Python found"

# Navigate to the script directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file with defaults..."
    cat > .env << EOF
DATABASE_URL=sqlite:///./auction_data.db
GSA_API_KEY=rXyfDnTjMh3d0Zu56fNcMbHb5dgFBQrmzfTjZqq3
DELETE_CLOSED_IMMEDIATELY=true
EOF
    echo "[OK] Created .env file with SQLite database"
fi

# Run the quick start script
echo ""
echo "Starting server..."
echo ""
python3 start.py

# Deactivate virtual environment on exit
deactivate
