#!/bin/bash
# =============================================================================
# Verity MVP - Run Script (Linux/Mac)
# =============================================================================
# Runs the development server
# Usage: ./scripts/run.sh
# =============================================================================

set -e

echo "========================================"
echo "  Verity MVP - Development Server"
echo "========================================"

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo -e "\nActivating virtual environment..."
source .venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env not found. Creating from template..."
    cp .env.example .env
fi

# Start server
echo -e "\nStarting Uvicorn server..."
echo "API Docs: http://localhost:8001/docs"
echo "OpenAPI:  http://localhost:8001/openapi.json"
echo "Press Ctrl+C to stop"
echo ""

uvicorn verity.main:app --reload --host 0.0.0.0 --port 8001
