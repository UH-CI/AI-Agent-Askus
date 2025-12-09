#!/bin/bash

# AI-Agent-Askus Docker-Only Deployment Script
# This script deploys the application using only Docker containers

set -e  # Exit on any error

echo "🐳 Starting AI-Agent-Askus Docker deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    echo "   Run: sudo systemctl start docker"
    exit 1
fi

# Check if user is in docker group
if ! groups | grep -q docker; then
    echo "❌ Current user is not in the docker group."
    echo "   Run: sudo usermod -aG docker $USER && sudo reboot"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version > /dev/null 2>&1; then
    echo "❌ Docker Compose is not available."
    echo "   Run: sudo apt install docker-compose-plugin -y"
    exit 1
fi

# Check if required files exist
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Check for API keys
if [ -z "$OPENAI_API_KEY" ] && [ ! -f ".env" ]; then
    echo "⚠️  WARNING: No OPENAI_API_KEY found in environment or .env file"
    echo "   The application requires an OpenAI API key to function properly."
    echo ""
    echo "   Set it with: export OPENAI_API_KEY='your_key_here'"
    echo "   Or create .env file: echo 'OPENAI_API_KEY=your_key_here' > .env"
    echo ""
    read -p "Continue without API key? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up on exit..."
}
trap cleanup EXIT INT TERM

# Check available disk space
echo "🔍 Checking available disk space..."
AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
REQUIRED_SPACE=10000000  # 10GB in KB

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo "⚠️  WARNING: Low disk space detected!"
    echo "   Available: $(($AVAILABLE_SPACE / 1024 / 1024))GB"
    echo "   Recommended: 10GB+"
    echo ""
    echo "💡 To free up space, try:"
    echo "   docker system prune -a --volumes  # Remove unused Docker data"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker compose down 2>/dev/null || true

# Clean up Docker to free space
echo "🧹 Cleaning up Docker to free space..."
docker system prune -f > /dev/null 2>&1 || true

# Build and start all containers
echo "🏗️  Building and starting all containers..."
echo "   This may take several minutes on first run..."
docker compose up -d --build

# Wait for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 30

# Check if ChromaDB is ready
echo "🔍 Checking ChromaDB connection..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
        echo "✅ ChromaDB is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ ChromaDB failed to start after 30 attempts"
        echo "   Check logs: docker compose logs chromadb"
        exit 1
    fi
    echo "   Waiting for ChromaDB... ($i/30)"
    sleep 2
done

# Check if backend is ready
echo "🔍 Checking Python backend connection..."
for i in {1..30}; do
    if curl -s http://localhost:8001/docs > /dev/null 2>&1; then
        echo "✅ Python backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Python backend failed to start after 30 attempts"
        echo "   Check logs: docker compose logs hoku-app"
        exit 1
    fi
    echo "   Waiting for Python backend... ($i/30)"
    sleep 2
done

# Check if database needs to be loaded
echo "🔍 Checking if database needs to be loaded..."
DB_CHECK=$(docker compose exec -T hoku-app python -c "
import os
from chromadb import HttpClient
try:
    client = HttpClient(host=os.getenv('CHROMA_HOST'), port=os.getenv('CHROMA_PORT'))
    collections = client.list_collections()
    if any(c.name == 'general_faq' for c in collections):
        print('EXISTS')
    else:
        print('MISSING')
except Exception as e:
    print('MISSING')
" 2>/dev/null | tail -1)

if [ "$DB_CHECK" = "EXISTS" ]; then
    echo "✅ Database already loaded, skipping..."
else
    echo "🗄️  Loading data into ChromaDB (this may take a while)..."
    if docker compose exec -T hoku-app python /app/load_db.py; then
        echo "✅ Database loaded successfully"
    else
        echo "❌ Failed to load database data"
        echo "   Check logs: docker compose logs hoku-app"
        exit 1
    fi
fi

# Check if frontend is ready
echo "🔍 Checking frontend connection..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Frontend failed to start after 30 attempts"
        echo "   Check logs: docker compose logs frontend"
        exit 1
    fi
    echo "   Waiting for frontend... ($i/30)"
    sleep 2
done

# Final health check
echo "🔍 Performing final health checks..."
HEALTH_CHECK_FAILED=false

if ! curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
    echo "❌ ChromaDB health check failed"
    HEALTH_CHECK_FAILED=true
fi

if ! curl -s http://localhost:8001/docs > /dev/null 2>&1; then
    echo "❌ Backend API health check failed"
    HEALTH_CHECK_FAILED=true
fi

if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "❌ Frontend health check failed"
    HEALTH_CHECK_FAILED=true
fi

if [ "$HEALTH_CHECK_FAILED" = true ]; then
    echo ""
    echo "❌ Some services failed health checks. Check the logs:"
    echo "   docker compose logs"
    exit 1
fi

echo ""
echo "🎉 Deployment successful!"
echo ""
echo "📊 Services running:"
echo "  🗄️  ChromaDB:      http://localhost:8000"
echo "  🐍 Python API:   http://localhost:8001/docs"
echo "  🌐 Frontend:     http://localhost:3000"
echo ""
echo "🌍 Access the application:"
echo "  📱 Web UI:       http://localhost:3000"
echo "  🔧 API Docs:     http://localhost:8001/docs"
echo ""

# Get server IP for remote access info
SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "YOUR_SERVER_IP")
if [ "$SERVER_IP" != "YOUR_SERVER_IP" ]; then
    echo "🌐 Remote access (replace with your actual server IP):"
    echo "  📱 Web UI:       http://$SERVER_IP:3000"
    echo "  🔧 API Docs:     http://$SERVER_IP:8001/docs"
    echo ""
fi

echo "📋 Container status:"
docker compose ps

echo ""
echo "💡 Useful commands:"
echo "  📊 View logs:     docker compose logs -f"
echo "  🔄 Restart:       docker compose restart"
echo "  🛑 Stop:          docker compose down"
echo "  📈 Monitor:       docker stats"
echo ""
echo "✅ Deployment complete! The application is ready to use."
