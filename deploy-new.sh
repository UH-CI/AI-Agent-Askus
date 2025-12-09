#!/bin/bash

# AI-Agent-Askus Deployment Script
# This script starts all services and exposes the app on port 3000

set -e  # Exit on any error

echo "🚀 Starting AI-Agent-Askus deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check available disk space
echo "🔍 Checking available disk space..."
AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
REQUIRED_SPACE=5000000  # 5GB in KB

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo "⚠️  WARNING: Low disk space detected!"
    echo "   Available: $(($AVAILABLE_SPACE / 1024 / 1024))GB"
    echo "   Recommended: 5GB+"
    echo ""
    echo "💡 To free up space, try:"
    echo "   docker system prune -a --volumes  # Remove unused Docker data"
    echo "   docker builder prune              # Remove build cache"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if required files exist
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

if [ ! -f "web/package.json" ]; then
    echo "❌ web/package.json not found. Please ensure the web directory exists."
    exit 1
fi

# Use docker compose (newer syntax) or docker-compose (legacy)
if command -v "docker compose" > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v "docker-compose" > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "❌ Neither docker compose nor docker-compose found. Please install Docker Compose."
fi

DOCKER_COMPOSE_CMD='docker compose'

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up..."
    $DOCKER_COMPOSE_CMD down 2>/dev/null || true
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    if [ -n "$BACKEND_PID" ]; then
        docker rm -f hoku-app 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# Clean up Docker to free space
echo "🧹 Cleaning up Docker to free space..."
docker system prune -f > /dev/null 2>&1 || true

# Start ChromaDB only
echo "🚀 Starting ChromaDB service..."
$DOCKER_COMPOSE_CMD up -d chromadb

# Wait for ChromaDB to be ready
echo "🔍 Checking ChromaDB connection..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null; then
        echo "✅ ChromaDB is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ ChromaDB failed to start after 30 attempts"
        exit 1
    fi
    sleep 2
done

# Load database data into ChromaDB
echo "🗄️ Loading data into ChromaDB (this may take a while)..."
cd app
$DOCKER_COMPOSE_CMD run --rm -e CHROMA_HOST=chromadb -e CHROMA_PORT=8000 hoku-app python /app/load_db.py || {
    echo "❌ Failed to load database data"
    cd ..
    exit 1
}
cd ..
echo "✅ Database loaded successfully"

# Start the backend with main.py
echo "🚀 Starting backend with main.py..."
docker stop hoku-app 2>/dev/null || true
docker rm -f hoku-app 2>/dev/null || true
$DOCKER_COMPOSE_CMD run -d --name hoku-app -p 8001:8001 -e HOST=0.0.0.0 -e PORT=8001 -e CHROMA_HOST=chromadb -e CHROMA_PORT=8000 hoku-app python /app/main.py
BACKEND_PID=$!

# Check if Python backend is ready
echo "🔍 Checking Python backend connection..."
for i in {1..30}; do
    if curl -s http://localhost:8001/docs > /dev/null; then
        echo "✅ Python backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Python backend failed to start after 30 attempts"
        exit 1
    fi
    sleep 2
done

# Install frontend dependencies and build
echo "🏗️ Installing frontend dependencies and building..."
cd web
if command -v pnpm > /dev/null 2>&1; then
    PACKAGE_MANAGER="pnpm"
else
    PACKAGE_MANAGER="npm"
fi
$PACKAGE_MANAGER install
$PACKAGE_MANAGER run build

# Start the frontend
echo "🚀 Starting frontend on port 3000..."
$PACKAGE_MANAGER start -- -H 0.0.0.0 -p 3000 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
echo "🔍 Checking frontend connection..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null; then
        echo "✅ Frontend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Frontend failed to start after 30 attempts"
        exit 1
    fi
    sleep 2
done

# Print success message
echo ""
echo "✅ AI-Agent-Askus is now running!"
echo "   - ChromaDB is running on port 8000"
echo "   - Python backend is running on port 8001"
echo "   - Frontend is running on port 3000"
echo ""
echo "📱 You can access the application at:"
echo "   http://localhost:3000"
echo ""
echo "🔍 To access the API docs, visit:"
echo "   http://localhost:8001/docs"
echo ""
echo "🛑 To stop all services, press Ctrl+C"

# Keep script running until Ctrl+C
wait
