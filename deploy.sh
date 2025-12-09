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

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up..."
    $DOCKER_COMPOSE_CMD down 2>/dev/null || true
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# Use docker compose (newer syntax) or docker-compose (legacy)
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "❌ Neither docker compose nor docker-compose found. Please install Docker Compose."
    exit 1
fi

echo "Using: $DOCKER_COMPOSE_CMD"
$DOCKER_COMPOSE_CMD up -d

# Clean up Docker to free space
echo "🧹 Cleaning up Docker to free space..."
docker system prune -f > /dev/null 2>&1 || true

# Start ChromaDB only
echo "🚀 Starting ChromaDB service..."
$DOCKER_COMPOSE_CMD up -d chromadb
sleep 10

# Wait for services to be ready
echo "⏳ Waiting for backend services to be ready..."
sleep 10

# Check if ChromaDB is ready
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

# Check if database needs to be loaded
echo "🔍 Checking if database needs to be loaded..."
DB_CHECK=$($DOCKER_COMPOSE_CMD run --rm hoku-app python -c "
import os
from chromadb import HttpClient
try:
    client = HttpClient(host=os.getenv('CHROMA_HOST'), port=os.getenv('CHROMA_PORT'))
    collections = client.list_collections()
    if any(c.name == 'general_faq' for c in collections):
        print('EXISTS')
    else:
        print('MISSING')
except:
    print('MISSING')
" 2>/dev/null | tail -1)

if [ "$DB_CHECK" = "EXISTS" ]; then
    echo "✅ Database already loaded, skipping..."
else
    echo "🗄️ Loading data into ChromaDB (this may take a while)..."
    $DOCKER_COMPOSE_CMD run --rm hoku-app python /app/load_db.py || {
        echo "❌ Failed to load database data"
        exit 1
    }
    echo "✅ Database loaded successfully"
fi

# Start the hoku-app service properly
echo "🚀 Starting Python API service..."
$DOCKER_COMPOSE_CMD up -d hoku-app

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

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "web/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd web
    if command -v pnpm > /dev/null; then
        pnpm install
    elif command -v npm > /dev/null; then
        npm install
    else
        echo "❌ Neither pnpm nor npm found. Please install Node.js and npm/pnpm."
        exit 1
    fi
    cd ..
fi

# Build the frontend for production
echo "🏗️  Building frontend for production..."
cd web
if command -v pnpm > /dev/null; then
    pnpm build
else
    npm run build
fi

# Kill any existing Next.js processes
echo "🧹 Stopping any existing frontend processes..."
pkill -f "next" 2>/dev/null || true
sleep 2

# Start the frontend on port 3000 in production mode
echo "🌐 Starting frontend on port 3000 (production mode)..."
if command -v pnpm > /dev/null; then
    pnpm start --port 3000 --hostname 0.0.0.0 &
else
    npm start -- --port 3000 --hostname 0.0.0.0 &
fi
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
echo "⏳ Waiting for frontend to be ready..."
sleep 5

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

echo ""
echo "🎉 Deployment successful!"
echo ""
echo "Services running:"
echo "  📊 ChromaDB:      http://localhost:8000"
echo "  🐍 Python API:   http://localhost:8001"
echo "  🌐 Frontend:     http://localhost:3000"
echo ""
echo "🌍 Access the application at: http://localhost:3000"
echo "   (Replace 'localhost' with your server's IP address when accessing remotely)"
echo ""
echo "Press Ctrl+C to stop all services..."

# Keep the script running
wait $FRONTEND_PID
