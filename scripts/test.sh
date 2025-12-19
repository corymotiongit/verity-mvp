#!/bin/bash
# =============================================================================
# Verity MVP - Test Script (Linux/Mac)
# =============================================================================
# Runs tests with coverage
# Usage: ./scripts/test.sh
# =============================================================================

set -e

echo "========================================"
echo "  Verity MVP - Running Tests"
echo "========================================"

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Run linting
echo -e "\n[1/3] Running linter..."
ruff check src/

# Run type checking
echo -e "\n[2/3] Running type checker..."
mypy src/verity/ --ignore-missing-imports || true

# Run tests
echo -e "\n[3/3] Running tests..."
pytest tests/ -v --cov=verity --cov-report=html --cov-report=term

echo -e "\n========================================"
echo "  Tests Complete!"
echo "========================================"
echo "Coverage report: htmlcov/index.html"
