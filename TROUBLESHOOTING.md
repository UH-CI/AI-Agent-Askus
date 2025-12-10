# AI-Agent-Askus Troubleshooting Guide

## Common Deployment Issues

### 1. Database Loading Fails with "FileNotFoundError"

**Error Message:**
```
FileNotFoundError: [Errno 2] No such file or directory: '../web-scraper/data/kb_articles_extracted.json'
❌ Failed to load database data
```

**Cause:** The database loading script cannot find optional data files due to path resolution issues in Docker containers.

**Solution:** This has been fixed in the updated `load_db.py` script. The script now:
- ✅ Handles missing optional files gracefully
- ✅ Searches multiple possible file locations
- ✅ Provides clear status messages about what data was loaded
- ✅ Continues deployment even if optional files are missing

**To verify your data files:**
```bash
./check-data-files.sh
```

### 2. Low Disk Space Warning

**Error Message:**
```
⚠️  WARNING: Low disk space detected!
   Available: 6GB
   Recommended: 10GB+
```

**Solution:**
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Remove unused containers and images
docker container prune -f
docker image prune -a -f

# Check disk usage
df -h
docker system df
```

### 3. Docker Permission Denied

**Error Message:**
```
❌ Docker is not running. Please start Docker and try again.
# OR
permission denied while trying to connect to the Docker daemon socket
```

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Restart Docker service
sudo systemctl restart docker

# Reboot system (required for group membership)
sudo reboot
```

### 4. Port Already in Use

**Error Message:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:3000: bind: address already in use
```

**Solution:**
```bash
# Find what's using the port
sudo lsof -i :3000

# Kill the process (replace PID with actual process ID)
sudo kill -9 <PID>

# Or change the port in docker-compose.yml
# Edit the frontend service ports section:
# ports:
#   - "3001:3000"  # Use port 3001 instead
```

### 5. Container Fails to Start

**Symptoms:** Container exits immediately or shows error status

**Diagnosis:**
```bash
# Check container status
docker compose ps

# View container logs
docker compose logs hoku-app
docker compose logs frontend
docker compose logs chromadb

# Check system resources
docker stats
df -h
```

**Common Solutions:**
- Ensure API keys are set: `export OPENAI_API_KEY="your_key"`
- Check available memory: minimum 8GB RAM recommended
- Verify Docker daemon is running: `docker info`

### 6. Frontend Not Accessible

**Symptoms:** Cannot access http://localhost:3000 or http://SERVER_IP:3000

**Diagnosis:**
```bash
# Check if frontend container is running
docker compose ps

# Test local connectivity
curl http://localhost:3000

# Check firewall settings
sudo ufw status
```

**Solutions:**
```bash
# Allow port through firewall
sudo ufw allow 3000

# Check frontend logs
docker compose logs frontend

# Restart frontend service
docker compose restart frontend
```

### 7. API Connection Issues

**Symptoms:** Frontend loads but cannot communicate with backend

**Diagnosis:**
```bash
# Test backend API
curl http://localhost:8001/docs

# Check backend logs
docker compose logs hoku-app

# Verify environment variables
docker compose exec hoku-app env | grep -E "(CHROMA|OPENAI)"
```

**Solutions:**
- Verify OPENAI_API_KEY is set and valid
- Check backend container is running: `docker compose ps`
- Restart backend: `docker compose restart hoku-app`

### 8. Database Connection Issues

**Symptoms:** Backend cannot connect to ChromaDB

**Diagnosis:**
```bash
# Test ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# Check ChromaDB logs
docker compose logs chromadb
```

**Solutions:**
```bash
# Restart ChromaDB
docker compose restart chromadb

# Reset database (WARNING: removes all data)
docker compose down -v
docker compose up -d
```

## Validation Scripts

### Environment Validation
```bash
./validate-environment.sh
```
Checks all required environment variables and configurations.

### Data Files Check
```bash
./check-data-files.sh
```
Verifies all required and optional data files are present.

### Health Check
```bash
# Manual health checks
echo "ChromaDB:" && curl -s http://localhost:8000/api/v1/heartbeat
echo "Backend:" && curl -s http://localhost:8001/docs > /dev/null && echo "OK"
echo "Frontend:" && curl -s http://localhost:3000 > /dev/null && echo "OK"
```

## Getting Help

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f hoku-app
docker compose logs -f frontend
docker compose logs -f chromadb
```

### System Information
```bash
# Docker info
docker info
docker compose version

# System resources
df -h
free -h
docker stats

# Container status
docker compose ps
```

### Reset Everything
```bash
# Complete reset (WARNING: removes all data)
docker compose down -v
docker system prune -a --volumes
./deploy-docker.sh
```

## Contact and Support

If you encounter issues not covered in this guide:

1. Check the container logs: `docker compose logs`
2. Verify system requirements are met
3. Ensure all environment variables are properly set
4. Try the complete reset procedure above

The deployment scripts include comprehensive error checking and should provide clear guidance for most common issues.
