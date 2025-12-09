#!/bin/bash
cd /home/exouser/AI-Agent-Askus

echo "🚀 Starting AI Agent Askus..."

# Start Docker containers
echo "📦 Starting Docker containers..."
docker compose up -d

# Wait for backend to be ready
echo "⏳ Waiting for backend services..."
sleep 10

# Kill any existing screen session
screen -S ai-agent-frontend -X quit 2>/dev/null || true

# Start frontend in screen session
echo "🌐 Starting frontend in screen session..."
screen -dmS ai-agent-frontend bash -c "cd /home/exouser/AI-Agent-Askus/web && npm start -- --port 3000 --hostname 0.0.0.0"

# Wait for frontend to start
sleep 5

echo ""
echo "✅ AI Agent Askus started successfully!"
echo ""
echo "Services:"
echo "  🌐 Frontend:  http://localhost:3000"
echo "  🐍 Backend:   http://localhost:8001"
echo "  📊 ChromaDB:  http://localhost:8000"
echo ""
echo "📺 To view frontend logs: screen -r ai-agent-frontend"
echo "🔄 To restart frontend: screen -S ai-agent-frontend -X quit && screen -dmS ai-agent-frontend bash -c 'cd /home/exouser/AI-Agent-Askus/web && npm start -- --port 3000 --hostname 0.0.0.0'"
