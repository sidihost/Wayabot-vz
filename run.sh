#!/bin/bash

# =============================================================================
# WAYA BOT - Quick Run Script
# =============================================================================
# This script helps you run the bot quickly for testing
# =============================================================================

set -e

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    WAYA BOT RUNNER                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for .env file
if [ ! -f "backend/.env" ] && [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found!${NC}"
    echo ""
    echo "Please create one with your API keys:"
    echo ""
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
    exit 1
fi

# Copy .env to backend if it exists in root
if [ -f ".env" ] && [ ! -f "backend/.env" ]; then
    cp .env backend/.env
fi

# Parse command line args
MODE="docker"
if [ "$1" == "--local" ] || [ "$1" == "-l" ]; then
    MODE="local"
elif [ "$1" == "--polling" ] || [ "$1" == "-p" ]; then
    MODE="polling"
elif [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: ./run.sh [option]"
    echo ""
    echo "Options:"
    echo "  (none)      Run with Docker Compose (recommended)"
    echo "  --local     Run locally with Python (requires PostgreSQL)"
    echo "  --polling   Run locally in polling mode (no webhook needed)"
    echo "  --help      Show this help"
    echo ""
    exit 0
fi

if [ "$MODE" == "docker" ]; then
    echo -e "${GREEN}Starting with Docker Compose...${NC}"
    echo ""
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        echo "Docker not found. Installing..."
        curl -fsSL https://get.docker.com | sh
    fi
    
    # Start services
    docker compose -f docker-compose.simple.yml up -d
    
    echo ""
    echo -e "${GREEN}Bot started!${NC}"
    echo ""
    echo "Commands:"
    echo "  docker compose logs -f waya    # View logs"
    echo "  docker compose restart waya    # Restart"
    echo "  docker compose down            # Stop"
    echo ""
    echo "Set webhook:"
    echo "  curl -X POST http://localhost:8000/set-webhook \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"url\": \"https://waya.qzz.io\"}'"
    
elif [ "$MODE" == "local" ] || [ "$MODE" == "polling" ]; then
    echo -e "${GREEN}Starting locally...${NC}"
    
    cd backend
    
    # Create venv if needed
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate venv
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
    
    # Run bot
    if [ "$MODE" == "polling" ]; then
        echo -e "${GREEN}Starting in POLLING mode (no webhook needed)...${NC}"
        python main.py --polling
    else
        echo -e "${GREEN}Starting FastAPI server...${NC}"
        uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    fi
fi
