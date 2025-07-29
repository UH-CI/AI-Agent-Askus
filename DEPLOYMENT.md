# AI-Agent-Askus Deployment Guide

This guide explains how to deploy the AI-Agent-Askus application on a server and access it from your laptop.

## Prerequisites

- Docker and Docker Compose installed on the server
- Node.js (v18+) and npm/pnpm installed on the server
- Git installed on the server

## Quick Deployment

1. **Clone the repository on your server:**
   ```bash
   git clone <repository-url>
   cd AI-Agent-Askus
   ```

2. **Run the deployment script:**
   ```bash
   ./deploy.sh
   ```

The script will:
- Start ChromaDB (vector database) on port 8000
- Start the Python backend API on port 8001
- Build and start the Next.js frontend on port 3000
- Perform health checks to ensure all services are running

## Accessing the Application

Once deployed, you can access the application at:
- **From the server:** `http://localhost:3000`
- **From your laptop:** `http://YOUR_SERVER_IP:3000`

Replace `YOUR_SERVER_IP` with the actual IP address of your server.

## Service Endpoints

- **Frontend (Web UI):** Port 3000
- **Backend API:** Port 8001
- **ChromaDB:** Port 8000

## Firewall Configuration

Make sure your server's firewall allows incoming connections on port 3000:

```bash
# For Ubuntu/Debian with ufw
sudo ufw allow 3000

# For CentOS/RHEL with firewalld
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --reload
```

## Stopping the Application

Press `Ctrl+C` in the terminal where the deployment script is running. This will gracefully stop all services.

## Troubleshooting

### Common Issues

1. **Docker not running:**
   - Start Docker: `sudo systemctl start docker`

2. **Port already in use:**
   - Check what's using the port: `sudo lsof -i :3000`
   - Kill the process or change the port in the script

3. **Frontend build fails:**
   - Ensure Node.js v18+ is installed
   - Clear node_modules: `rm -rf web/node_modules` and run the script again

4. **Cannot access from laptop:**
   - Check firewall settings
   - Ensure the server IP is correct
   - Try accessing from the server first: `curl http://localhost:3000`

### Logs

- **Backend logs:** `docker-compose logs hoku-app`
- **ChromaDB logs:** `docker-compose logs chromadb`
- **Frontend logs:** Check the terminal where the deployment script is running

## Manual Deployment (Alternative)

If you prefer to start services manually:

1. **Start backend services:**
   ```bash
   docker-compose up -d
   ```

2. **Start frontend:**
   ```bash
   cd web
   npm install
   npm run build
   npm start -- --port 3000 --hostname 0.0.0.0
   ```

## Environment Variables

The application uses the following environment variables (configured in docker-compose.yml):
- `CHROMA_HOST`: ChromaDB hostname
- `CHROMA_PORT`: ChromaDB port
- `OPENAI_API_KEY`: OpenAI API key (required for AI functionality)
- `GEMINI_API_KEY`: Google Gemini API key (optional)

Make sure to update these in `docker-compose.yml` with your actual API keys before deployment.
