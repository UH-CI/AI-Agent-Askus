#!/bin/bash

set -e

echo "Starting Hoku..."

# Kill ALL related processes (more thorough cleanup)
echo "Stopping existing processes..."
pkill -f "python main.py" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
pkill -f "chroma run" 2>/dev/null || true
docker stop $(docker ps -q --filter ancestor=chromadb/chroma) 2>/dev/null || true

# Wait for ports to be freed
echo "Waiting for cleanup..."
sleep 5

# Activate conda environment
echo "Activating conda environment..."
eval "$(conda shell.bash hook)"
conda activate ai-agent-askus

# Start ChromaDB server
echo "Starting ChromaDB server..."
mkdir -p /home/exouser/AI-Agent-Askus/chromadb_data
nohup docker run -p 127.0.0.1:8000:8000 -v /home/exouser/AI-Agent-Askus/chromadb_data:/chroma/chroma chromadb/chroma > ../chromadb.log 2>&1 &

echo "Waiting for ChromaDB to start..."
sleep 10

echo "Testing ChromaDB connection..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
        echo "ChromaDB is ready!"
        break
    elif [ $i -eq 30 ]; then
        echo "ChromaDB failed to start after 30 attempts"
        exit 1
    else
        echo "Waiting for ChromaDB... attempt $i/30"
        sleep 2
    fi
done

# Load database (only if collections are empty)
cd /home/exouser/AI-Agent-Askus/app
DOC_COUNT=$(python3 -c "
import chromadb
client = chromadb.HttpClient(host='localhost', port=8000)
total = sum(client.get_collection(c.name).count() for c in client.list_collections())
print(total)
" 2>/dev/null || echo "0")

if [ "$DOC_COUNT" -eq "0" ]; then
    echo "Collections empty, loading database..."
    python load_db.py
else
    echo "Collections already populated ($DOC_COUNT docs), skipping load_db.py"
fi

# Start backend
echo "Starting backend..."
nohup python main.py > ../backend.log 2>&1 &

# Give backend time to start
sleep 5

# Start frontend (clean cache + force port)
echo "Starting frontend..."
cd /home/exouser/AI-Agent-Askus/web
rm -rf .next
nohup npm run dev -- --hostname 0.0.0.0 --port 3000 > ../frontend.log 2>&1 &

echo "Hoku started"
