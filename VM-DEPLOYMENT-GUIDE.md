# AI-Agent-Askus VM Deployment Guide (Fully Containerized)

## Project Overview

AI-Agent-Askus is a multi-service application consisting of:

- **Backend**: Python FastAPI application using LangChain/LangGraph for AI functionality
- **Frontend**: Next.js web application 
- **Database**: ChromaDB vector database for embeddings
- **Architecture**: Fully containerized with Docker Compose

## System Requirements

- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: Minimum 20GB free space
- **CPU**: 4+ cores recommended
- **Network**: Internet access for downloading dependencies

## Prerequisites Installation (Docker Only!)

### 1. System Updates

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Docker Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### 3. Git Installation

```bash
sudo apt install git -y
```

### 4. Reboot (Important!)

```bash
# Log out and back in (or reboot) for Docker group membership to take effect
sudo reboot
```

## Deployment Instructions

### 1. Clone Repository

```bash
git clone <REPOSITORY_URL>
cd AI-Agent-Askus
```

### 2. Environment Configuration

Set your API keys (required for AI functionality):

```bash
# Option A: Export environment variables
export OPENAI_API_KEY="your_openai_api_key_here"
export GEMINI_API_KEY="your_gemini_api_key_here"  # optional

# Option B: Create .env file
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
echo "GEMINI_API_KEY=your_gemini_api_key_here" >> .env
```

### 3. Quick Deployment

Use the provided Docker-only deployment script:

```bash
# Make deployment script executable
chmod +x deploy-docker.sh

# Run deployment
./deploy-docker.sh
```

### 4. Manual Deployment (Alternative)

If you prefer to run commands manually:

```bash
# Build and start all containers
docker compose up -d

# Wait for services to initialize (about 2-3 minutes)
sleep 180

# Check if all services are running
docker compose ps

# Load initial data into ChromaDB
docker compose exec hoku-app python /app/load_db.py
```

### 5. Verify Deployment

```bash
# Check service health
curl -s http://localhost:8000/api/v1/heartbeat  # ChromaDB
curl -s http://localhost:8001/docs              # Backend API
curl -s http://localhost:3000                   # Frontend
```

### 6. Firewall Configuration

```bash
# Allow frontend access from external networks
sudo ufw allow 3000

# Optional: Allow direct API access
sudo ufw allow 8001  # Backend API
sudo ufw allow 8000  # ChromaDB
```

## Service Architecture

### Container Services

- **ai-agent-frontend**: Next.js web application (Port 3000)
- **hoku-app**: Python FastAPI backend (Port 8001)
- **chromadb**: Vector database for embeddings (Port 8000)

### Access Points

- **Web Application**: http://YOUR_VM_IP:3000
- **API Documentation**: http://YOUR_VM_IP:8001/docs
- **ChromaDB**: http://YOUR_VM_IP:8000

## Service Management

### Basic Operations

```bash
# View running containers
docker compose ps

# Stop all services
docker compose down

# Start services
docker compose up -d

# Restart specific service
docker compose restart hoku-app

# View logs
docker compose logs -f hoku-app      # Backend logs
docker compose logs -f chromadb      # Database logs
docker compose logs -f frontend      # Frontend logs
```

### Monitoring

```bash
# Real-time logs from all services
docker compose logs -f

# Check resource usage
docker stats

# Check disk usage
docker system df
```

## Data Management

### Persistence

- ChromaDB data persists in Docker volume `chroma-data`
- Data survives container restarts and updates
- Volume location: `/var/lib/docker/volumes/chroma-data`

### Backup and Reset

```bash
# Backup ChromaDB data
docker run --rm -v chroma-data:/data -v $(pwd):/backup ubuntu tar czf /backup/chroma-backup.tar.gz /data

# Reset database (removes all data)
docker compose down -v
docker compose up -d
docker compose exec hoku-app python /app/load_db.py
```

## Environment Variables

### Required

- `OPENAI_API_KEY`: OpenAI API key for AI functionality

### Optional

- `GEMINI_API_KEY`: Google Gemini API key (alternative AI provider)

### Auto-configured (in docker-compose.yml)

- `CHROMA_HOST=chromadb`
- `CHROMA_PORT=8000`
- `NODE_ENV=production`
- `NEXT_PUBLIC_API_URL=http://hoku-app:8001`

## Troubleshooting

### Common Issues

1. **Docker permission denied**
   ```bash
   # Add user to docker group and reboot
   sudo usermod -aG docker $USER
   sudo reboot
   ```

2. **Port already in use**
   ```bash
   # Check what's using the port
   sudo lsof -i :3000
   # Kill the process or change port in docker-compose.yml
   ```

3. **Container fails to start**
   ```bash
   # Check container logs
   docker compose logs [service-name]
   # Check available disk space
   df -h
   ```

4. **Frontend not accessible**
   ```bash
   # Verify frontend container is running
   docker compose ps
   # Check frontend logs
   docker compose logs frontend
   ```

5. **Low disk space**
   ```bash
   # Clean up Docker resources
   docker system prune -a --volumes
   ```

### Health Checks

```bash
# Verify all services are responding
echo "Checking ChromaDB..." && curl -s http://localhost:8000/api/v1/heartbeat
echo "Checking Backend..." && curl -s http://localhost:8001/docs > /dev/null && echo "OK"
echo "Checking Frontend..." && curl -s http://localhost:3000 > /dev/null && echo "OK"
```

## Updates and Maintenance

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart containers
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Docker Maintenance

```bash
# Update base images
docker compose pull

# Clean up unused resources
docker system prune -f

# View disk usage
docker system df
```

## Security Considerations

### Production Deployment

- Set strong API keys before deployment
- Use firewall rules to restrict port access
- Consider reverse proxy (nginx) for HTTPS
- Regularly update Docker images
- Monitor logs for suspicious activity

### Network Security

```bash
# Restrict access to specific IPs (example)
sudo ufw allow from 192.168.1.0/24 to any port 3000

# Enable firewall
sudo ufw enable
```

## Advantages of This Approach

✅ **Consistency**: Same environment across all deployments

✅ **Isolation**: Each service runs in its own container

✅ **Scalability**: Easy to scale individual services

✅ **Maintenance**: Simple updates and rollbacks

✅ **Dependencies**: No need to install Node.js, Python, or other dependencies on host

✅ **Portability**: Runs the same on any Docker-capable system

## Quick Start Summary

For experienced users, here's the minimal command sequence:

```bash
# Prerequisites (run once)
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER && sudo apt install docker-compose-plugin git -y
sudo reboot

# Deployment
git clone <REPOSITORY_URL> && cd AI-Agent-Askus
export OPENAI_API_KEY="your_key_here"
chmod +x deploy-docker.sh && ./deploy-docker.sh

# Access at http://YOUR_VM_IP:3000
```
