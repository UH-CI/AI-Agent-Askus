#!/bin/bash

# AI-Agent-Askus Development Deployment Script
# This script starts services without rebuilding database

set -e  # Exit on any error

echo "🚀 Starting AI-Agent-Askus (development mode)..."

# Use docker compose (newer syntax) or docker-compose (legacy)
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "❌ Neither docker compose nor docker-compose found. Please install Docker Compose."
    exit 1
fi

# Start backend services
echo "🚀 Starting backend services..."
$DOCKER_COMPOSE_CMD up -d

# Wait for services
sleep 10

# Check if services are ready
echo "🔍 Checking services..."
for i in {1..15}; do
    if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null && curl -s http://localhost:8001/docs > /dev/null; then
        echo "✅ Backend services are ready"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "❌ Services failed to start"
        exit 1
    fi
    sleep 2
done

# Kill any existing frontend processes
echo "🧹 Stopping any existing frontend processes..."
pkill -f "next" 2>/dev/null || true
sleep 2

# Start frontend in development mode (faster)
echo "🌐 Starting frontend in development mode..."
cd web
if command -v pnpm > /dev/null; then
    pnpm dev --port 3000 --hostname 0.0.0.0 &
else
    npm run dev -- --port 3000 --hostname 0.0.0.0 &
fi
FRONTEND_PID=$!
cd ..

# Wait for frontend
sleep 5
for i in {1..15}; do
    if curl -s http://localhost:3000 > /dev/null; then
        echo "✅ Frontend is ready"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "❌ Frontend failed to start"
        exit 1
    fi
    sleep 2
done

echo ""
echo "🎉 Development deployment successful!"
echo ""
echo "Services running:"
echo "  📊 ChromaDB:      http://localhost:8000"
echo "  🐍 Python API:   http://localhost:8001"
echo "  🌐 Frontend:     http://localhost:3000 (dev mode)"
echo ""
echo "Press Ctrl+C to stop all services..."

# Keep the script running
wait $FRONTEND_PID
