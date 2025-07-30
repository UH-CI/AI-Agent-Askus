#!/bin/bash

# AI-Agent-Askus Lightweight Deployment Script
# This script uses pre-built images and local Python environment to avoid disk space issues

set -e  # Exit on any error

echo "🚀 Starting AI-Agent-Askus lightweight deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Python 3.10 is available
if ! python3.10 --version > /dev/null 2>&1; then
    if ! python3 --version | grep -q "3.10"; then
        echo "❌ Python 3.10 is required but not found."
        echo "Please install Python 3.10 or create a conda environment:"
        echo "  conda create -n askus_env python=3.10"
        echo "  conda activate askus_env"
        exit 1
    fi
fi

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up..."
    docker stop chromadb 2>/dev/null || true
    docker rm chromadb 2>/dev/null || true
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# Start only ChromaDB using Docker
echo "📦 Starting ChromaDB..."
docker run -d \
    --name chromadb \
    -p 8000:8000 \
    -v chroma-data:/chroma/chroma \
    -e ALLOW_RESET=true \
    ghcr.io/chroma-core/chroma:0.4.13

# Wait for ChromaDB to be ready
echo "⏳ Waiting for ChromaDB to be ready..."
sleep 5

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

# Install Python backend dependencies locally
echo "🐍 Setting up Python backend..."
cd app

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3.10 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies (this may take a while)..."
pip install --upgrade pip
pip install -e .

# Set environment variables
export CHROMA_HOST=localhost
export CHROMA_PORT=8000

# Load the database with FAQ and policy data
echo "🗄️ Loading data into ChromaDB..."
python load_db.py

# Set environment variables
export CHROMA_HOST=localhost
export CHROMA_PORT=8000

# Start the Python backend using main.py
echo "🚀 Starting Python backend on port 8001..."
python main.py &
BACKEND_PID=$!

# Give the backend a moment to initialize
sleep 5

cd ..

# Wait for backend to be ready
echo "⏳ Waiting for Python backend to be ready..."
sleep 10

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
echo "🎉 Lightweight deployment successful!"
echo ""
echo "Services running:"
echo "  📊 ChromaDB:      http://localhost:8000"
echo "  🐍 Python API:   http://localhost:8001"
echo "  🌐 Frontend:     http://localhost:3000"
echo ""
echo "🌍 Access the application at: http://localhost:3000"
echo "   (Replace 'localhost' with your server's IP address when accessing remotely)"
echo ""
echo "💡 This lightweight version uses:"
echo "   - Pre-built ChromaDB Docker image (no build required)"
echo "   - Local Python environment (no Docker build)"
echo "   - Standard Node.js frontend build"
echo ""
echo "Press Ctrl+C to stop all services..."

# Keep the script running
wait $FRONTEND_PID
