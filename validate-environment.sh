#!/bin/bash

# Environment Validation Script for AI-Agent-Askus
# This script validates that all required environment variables are properly configured

echo "🔍 Validating environment configuration for AI-Agent-Askus..."

# Check if running in Docker environment
if [ -f /.dockerenv ]; then
    echo "✅ Running inside Docker container"
    DOCKER_ENV=true
else
    echo "ℹ️  Running on host system"
    DOCKER_ENV=false
fi

# Function to check environment variable
check_env_var() {
    local var_name=$1
    local required=$2
    local default_value=$3
    
    if [ -n "${!var_name}" ]; then
        echo "✅ $var_name is set"
        return 0
    elif [ "$required" = "true" ]; then
        echo "❌ $var_name is REQUIRED but not set"
        return 1
    else
        echo "⚠️  $var_name is optional (not set)"
        if [ -n "$default_value" ]; then
            echo "   Default value would be: $default_value"
        fi
        return 0
    fi
}

echo ""
echo "🔑 Checking API Keys:"
check_env_var "OPENAI_API_KEY" "true"
OPENAI_OK=$?
check_env_var "GEMINI_API_KEY" "false"

echo ""
echo "🗄️  Checking Database Configuration:"
check_env_var "CHROMA_HOST" "false" "localhost"
check_env_var "CHROMA_PORT" "false" "8000"

echo ""
echo "🌐 Checking Frontend Configuration:"
check_env_var "NODE_ENV" "false" "production"
check_env_var "NEXT_PUBLIC_API_URL" "false" "http://localhost:8001"

echo ""
echo "🐍 Checking Backend Configuration:"
check_env_var "HOST" "false" "0.0.0.0"
check_env_var "PORT" "false" "8001"

echo ""
if [ $OPENAI_OK -eq 0 ]; then
    echo "✅ Environment validation passed!"
    echo ""
    echo "📋 Configuration Summary:"
    echo "   🔑 OpenAI API Key: Set"
    echo "   🗄️  ChromaDB: ${CHROMA_HOST:-localhost}:${CHROMA_PORT:-8000}"
    echo "   🌐 Frontend: ${NODE_ENV:-production} mode"
    echo "   🐍 Backend: ${HOST:-0.0.0.0}:${PORT:-8001}"
    
    if [ -n "$GEMINI_API_KEY" ]; then
        echo "   🔑 Gemini API Key: Set (optional)"
    fi
    
    exit 0
else
    echo "❌ Environment validation failed!"
    echo ""
    echo "💡 To fix this issue:"
    echo "   export OPENAI_API_KEY='your_openai_api_key_here'"
    echo "   # OR create .env file:"
    echo "   echo 'OPENAI_API_KEY=your_openai_api_key_here' > .env"
    exit 1
fi
