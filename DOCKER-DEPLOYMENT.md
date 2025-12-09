# Docker Deployment Guide for AI-Agent-Askus

## Quick Start

For users who just want to get the application running quickly:

```bash
# 1. Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER && sudo reboot

# 2. Clone and deploy
git clone <REPOSITORY_URL> && cd AI-Agent-Askus
export OPENAI_API_KEY="your_openai_api_key_here"
chmod +x deploy-docker.sh && ./deploy-docker.sh

# 3. Access at http://YOUR_SERVER_IP:3000
```

## What This Deployment Includes

### Containerized Services
- **Frontend Container** (`ai-agent-frontend`): Next.js web application on port 3000
- **Backend Container** (`hoku-app`): Python FastAPI application on port 8001  
- **Database Container** (`chromadb`): Vector database for embeddings on port 8000

### Key Features
✅ **No local dependencies** - Only Docker required on host system
✅ **Automatic data loading** - FAQ and policy data loaded on first run
✅ **Health checks** - Validates all services are running correctly
✅ **Persistent storage** - Database data survives container restarts
✅ **Production ready** - Optimized builds and configurations

## Environment Variables

### Required
```bash
export OPENAI_API_KEY="sk-..."  # Required for AI functionality
```

### Optional
```bash
export GEMINI_API_KEY="..."     # Alternative AI provider (optional)
```

### Auto-configured (in docker-compose.yml)
- `CHROMA_HOST=chromadb` - Database hostname within Docker network
- `CHROMA_PORT=8000` - Database port
- `NODE_ENV=production` - Frontend environment
- `NEXT_PUBLIC_API_URL=http://hoku-app:8001` - Backend URL for frontend

## Deployment Scripts

### Primary Script: `deploy-docker.sh`
Full deployment with comprehensive checks and data loading:
```bash
./deploy-docker.sh
```

Features:
- Docker environment validation
- Disk space checking
- Automatic service health checks
- Database initialization
- Detailed status reporting

### Manual Deployment
If you prefer manual control:
```bash
# Set environment variables
export OPENAI_API_KEY="your_key_here"

# Start all services
docker compose up -d

# Wait for initialization
sleep 60

# Load initial data
docker compose exec hoku-app python /app/load_db.py

# Check status
docker compose ps
```

## Service Management

### View Status
```bash
docker compose ps                    # Container status
docker compose logs -f               # All logs (follow)
docker compose logs -f hoku-app      # Backend logs only
docker compose logs -f frontend      # Frontend logs only
docker compose logs -f chromadb      # Database logs only
```

### Control Services
```bash
docker compose up -d                 # Start all services
docker compose down                  # Stop all services
docker compose restart              # Restart all services
docker compose restart hoku-app     # Restart specific service
```

### Monitoring
```bash
docker stats                         # Resource usage
docker system df                     # Disk usage
curl http://localhost:3000           # Frontend health
curl http://localhost:8001/docs      # Backend health
curl http://localhost:8000/api/v1/heartbeat  # Database health
```

## Data Management

### Backup Database
```bash
# Create backup
docker run --rm -v chroma-data:/data -v $(pwd):/backup ubuntu \
  tar czf /backup/chroma-backup-$(date +%Y%m%d).tar.gz /data

# Restore backup
docker compose down
docker volume rm ai-agent-askus_chroma-data
docker volume create ai-agent-askus_chroma-data
docker run --rm -v chroma-data:/data -v $(pwd):/backup ubuntu \
  tar xzf /backup/chroma-backup-YYYYMMDD.tar.gz -C /
docker compose up -d
```

### Reset Database
```bash
# Warning: This removes all data
docker compose down -v
docker compose up -d
docker compose exec hoku-app python /app/load_db.py
```

## Troubleshooting

### Common Issues

**1. Permission Denied (Docker)**
```bash
sudo usermod -aG docker $USER
sudo reboot
```

**2. Port Already in Use**
```bash
sudo lsof -i :3000
# Kill the process or change port in docker-compose.yml
```

**3. Container Won't Start**
```bash
docker compose logs [service-name]
df -h  # Check disk space
```

**4. API Key Issues**
```bash
# Validate environment
./validate-environment.sh

# Set API key
export OPENAI_API_KEY="your_key_here"
docker compose restart hoku-app
```

**5. Database Connection Issues**
```bash
# Check ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# Restart database
docker compose restart chromadb
```

### Health Check Script
```bash
# Run comprehensive health check
./validate-environment.sh

# Manual health checks
echo "ChromaDB:" && curl -s http://localhost:8000/api/v1/heartbeat
echo "Backend:" && curl -s http://localhost:8001/docs > /dev/null && echo "OK"
echo "Frontend:" && curl -s http://localhost:3000 > /dev/null && echo "OK"
```

## Network Access

### Local Access (on server)
- Web UI: http://localhost:3000
- API Docs: http://localhost:8001/docs
- Database: http://localhost:8000

### Remote Access (from other machines)
- Web UI: http://YOUR_SERVER_IP:3000
- API Docs: http://YOUR_SERVER_IP:8001/docs

### Firewall Configuration
```bash
# Allow web access
sudo ufw allow 3000

# Optional: Allow direct API access
sudo ufw allow 8001
sudo ufw allow 8000
```

## Updates and Maintenance

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Update Docker Images
```bash
# Update base images
docker compose pull

# Clean up old images
docker system prune -f
```

### Maintenance Tasks
```bash
# Clean up Docker resources
docker system prune -a --volumes

# View disk usage
docker system df

# Update system packages
sudo apt update && sudo apt upgrade -y
```

## Architecture Details

### Container Communication
- Frontend connects to backend via internal Docker network
- Backend connects to ChromaDB via internal Docker network
- Only frontend port (3000) needs external access
- All services use Docker's built-in DNS resolution

### Data Persistence
- ChromaDB data stored in Docker volume `chroma-data`
- Volume persists across container restarts and updates
- Located at `/var/lib/docker/volumes/chroma-data`

### Security Considerations
- API keys passed as environment variables
- Internal services communicate via Docker network
- Only necessary ports exposed to host
- Consider using reverse proxy (nginx) for HTTPS in production

## Performance Optimization

### Resource Requirements
- **Minimum**: 8GB RAM, 20GB disk, 4 CPU cores
- **Recommended**: 16GB RAM, 50GB disk, 8 CPU cores

### Scaling Options
```bash
# Scale specific services (if needed)
docker compose up -d --scale hoku-app=2

# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

This deployment approach provides a robust, scalable, and maintainable solution for running AI-Agent-Askus in any Docker-capable environment.
