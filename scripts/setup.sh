#!/bin/bash
# =============================================================================
# Verity MVP - Setup Script (Linux/Mac)
# =============================================================================
# Reproducible setup script for Linux/Mac development environment
# Usage: ./scripts/setup.sh
# =============================================================================

set -e

echo "========================================"
echo "  Verity MVP - Setup"
echo "========================================"

# Check Python version
echo -e "\n[1/5] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.11+"
    exit 1
fi
python3 --version

# Create virtual environment
echo -e "\n[2/5] Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "Virtual environment already exists, skipping..."
else
    python3 -m venv .venv
    echo "Virtual environment created"
fi

# Activate virtual environment
echo -e "\n[3/5] Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo -e "\n[4/5] Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"
echo "Dependencies installed"

# Create .env from template
echo -e "\n[5/5] Setting up environment file..."
if [ -f ".env" ]; then
    echo ".env already exists, skipping..."
else
    cp .env.example .env
    echo ".env created from template"
    echo "IMPORTANT: Edit .env with your Supabase and GCP credentials"
fi

echo -e "\n========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run: ./scripts/run.sh"
echo "  3. Visit: http://localhost:8001/docs"
