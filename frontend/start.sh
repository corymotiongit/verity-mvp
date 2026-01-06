#!/bin/bash
# Quick start script for Verity frontend

set -e

echo "🚀 Verity Frontend - Quick Start"
echo "=================================="

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "⚠️  .env.local not found. Creating from template..."
    cp .env.example .env.local
    echo "✅ Created .env.local"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env.local and set your VITE_GEMINI_API_KEY"
    echo "   Get your key from: https://aistudio.google.com/app/apikey"
    echo ""
    read -p "Press Enter after setting your API key..."
fi

# Check if node_modules exists
if [ ! -d node_modules ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
fi

# Start dev server
echo ""
echo "🌐 Starting Vite dev server..."
echo "   Frontend: http://localhost:5173"
echo "   Backend should be running on: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev
