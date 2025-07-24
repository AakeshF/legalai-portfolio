#!/bin/bash

echo "🚀 Legal AI Backend Setup and Launch Script"
echo "=========================================="

# Check Python version
echo "✓ Checking Python version..."
python3 --version

# Install missing dependencies
echo "✓ Installing dependencies..."
pip3 install aiohttp beautifulsoup4 passlib[bcrypt] python-jose[cryptography]

# Download spaCy model
echo "✓ Downloading spaCy language model..."
python3 -m spacy download en_core_web_sm

# Initialize database
echo "✓ Initializing database..."
python3 init_full_database.py

# Kill any existing processes on port 8000
echo "✓ Checking for existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start the backend
echo "✓ Starting backend server..."
echo ""
echo "🎉 Backend starting at http://localhost:8000"
echo "📚 API Documentation at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the backend
python3 start.py