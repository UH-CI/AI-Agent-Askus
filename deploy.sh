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
    docker-compose down
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# Start backend services (ChromaDB and Python app)
echo "📦 Starting backend services..."
docker-compose up -d

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

# Start the frontend on port 3000
echo "🌐 Starting frontend on port 3000..."
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
