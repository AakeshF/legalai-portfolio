#!/bin/bash

echo "🚀 Launching Legal AI Backend..."
echo "================================"

# Kill any existing processes on port 8000
echo "✓ Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start the backend in the background
echo "✓ Starting backend server..."
python3 start.py &
BACKEND_PID=$!

# Wait for server to start
echo "✓ Waiting for server to initialize..."
sleep 5

# Check if server is running
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend server started successfully (PID: $BACKEND_PID)"
    
    # Test health endpoint
    echo ""
    echo "✓ Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health || echo "Failed to connect")
    
    if [[ $HEALTH_RESPONSE == *"\"status\":\"healthy\""* ]]; then
        echo "✅ Health check passed!"
        echo "Response: $HEALTH_RESPONSE"
    else
        echo "⚠️  Health check returned unexpected response:"
        echo "$HEALTH_RESPONSE"
    fi
    
    echo ""
    echo "🎉 Backend is running at:"
    echo "   - API: http://localhost:8000"
    echo "   - Docs: http://localhost:8000/docs"
    echo ""
    echo "To stop the server, run: kill $BACKEND_PID"
    
    # Save PID to file for easy stopping later
    echo $BACKEND_PID > backend.pid
    
else
    echo "❌ Failed to start backend server"
    exit 1
fi

# Keep the script running to show logs
echo ""
echo "📝 Server logs:"
echo "==============="
tail -f /dev/null