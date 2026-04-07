#!/bin/bash

# =============================================================================
# WAYA TELEGRAM BOT - ONE-CLICK SETUP FOR DIGITALOCEAN
# =============================================================================
# This script will:
# 1. Install Docker and Docker Compose
# 2. Set up environment variables
# 3. Generate SSL certificates
# 4. Start the bot
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║   WAYA - Intelligent Telegram Bot Builder                     ║"
echo "║   DigitalOcean Deployment Setup                               ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# =============================================================================
# STEP 1: Install Docker
# =============================================================================
echo -e "\n${YELLOW}[1/6] Installing Docker...${NC}"

if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker already installed${NC}"
else
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}Docker installed successfully${NC}"
fi

# Install Docker Compose
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo -e "${GREEN}Docker Compose already installed${NC}"
else
    apt-get update
    apt-get install -y docker-compose-plugin
    echo -e "${GREEN}Docker Compose installed successfully${NC}"
fi

# =============================================================================
# STEP 2: Create Environment File
# =============================================================================
echo -e "\n${YELLOW}[2/6] Setting up environment variables...${NC}"

if [ -f .env ]; then
    echo -e "${GREEN}Found existing .env file${NC}"
    read -p "Do you want to reconfigure? (y/n): " reconfigure
    if [ "$reconfigure" != "y" ]; then
        echo "Keeping existing configuration"
    else
        rm .env
    fi
fi

if [ ! -f .env ]; then
    echo ""
    echo -e "${BLUE}How would you like to configure your bot?${NC}"
    echo ""
    echo "  1) Import from Vercel (if you have env vars there)"
    echo "  2) Enter manually"
    echo ""
    read -p "Choose option [1/2]: " CONFIG_OPTION
    
    if [ "$CONFIG_OPTION" = "1" ]; then
        # =============================================================================
        # OPTION 1: Import from Vercel
        # =============================================================================
        echo ""
        echo -e "${YELLOW}Importing from Vercel...${NC}"
        
        # Check if npm is installed
        if ! command -v npm &> /dev/null; then
            echo "Installing Node.js..."
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
            apt-get install -y nodejs
        fi
        
        # Install Vercel CLI
        if ! command -v vercel &> /dev/null; then
            echo "Installing Vercel CLI..."
            npm i -g vercel
        fi
        
        echo ""
        echo -e "${BLUE}You'll need to login to Vercel and link your project.${NC}"
        echo ""
        
        # Login to Vercel
        vercel login
        
        # Link to project
        echo ""
        echo "Now link to your Vercel project..."
        vercel link
        
        # Pull env vars
        echo ""
        echo "Pulling environment variables..."
        vercel env pull .env
        
        # Add any missing vars
        if ! grep -q "BOT_DOMAIN" .env 2>/dev/null; then
            echo "" >> .env
            echo "# Domain for webhook" >> .env
            echo "BOT_DOMAIN=waya.qzz.io" >> .env
        fi
        
        # Add database vars if missing
        if ! grep -q "DATABASE_URL" .env 2>/dev/null; then
            echo "" >> .env
            echo "# Database (local Docker PostgreSQL)" >> .env
            echo "DB_USER=waya" >> .env
            echo "DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)" >> .env
            echo "DB_NAME=wayabot" >> .env
            source .env 2>/dev/null || true
            echo "DATABASE_URL=postgresql://\${DB_USER}:\${DB_PASSWORD}@postgres:5432/\${DB_NAME}" >> .env
        fi
        
        chmod 600 .env
        echo -e "${GREEN}Environment imported from Vercel!${NC}"
        
    else
        # =============================================================================
        # OPTION 2: Manual Configuration
        # =============================================================================
        echo ""
        echo -e "${BLUE}Let's configure your bot manually:${NC}"
        echo ""
    
        # Telegram Bot Token
        echo -e "${YELLOW}1. TELEGRAM BOT TOKEN${NC}"
    echo "   Get it from @BotFather on Telegram"
    echo "   - Open Telegram and search for @BotFather"
    echo "   - Send /newbot and follow instructions"
    echo "   - Copy the token (looks like: 123456:ABC-DEF1234...)"
    echo ""
    read -p "Enter your Telegram Bot Token: " TELEGRAM_BOT_TOKEN
    
    # Groq API Key
    echo ""
    echo -e "${YELLOW}2. GROQ API KEY${NC}"
    echo "   Get it from https://console.groq.com/keys"
    echo "   - Sign up/login at console.groq.com"
    echo "   - Go to API Keys section"
    echo "   - Create a new key and copy it"
    echo ""
    read -p "Enter your Groq API Key: " GROQ_API_KEY
    
    # Domain for webhook (pre-filled with your domain)
    echo ""
    echo -e "${YELLOW}3. YOUR DOMAIN (for webhook)${NC}"
    echo "   Your domain: waya.qzz.io"
    echo ""
    read -p "Enter your domain/IP [waya.qzz.io]: " BOT_DOMAIN
    BOT_DOMAIN=${BOT_DOMAIN:-waya.qzz.io}
    
    # Database credentials
    echo ""
    echo -e "${YELLOW}4. DATABASE CREDENTIALS (press Enter for defaults)${NC}"
    read -p "Database user [waya]: " DB_USER
    DB_USER=${DB_USER:-waya}
    read -p "Database password [auto-generate]: " DB_PASSWORD
    DB_PASSWORD=${DB_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)}
    read -p "Database name [wayabot]: " DB_NAME
    DB_NAME=${DB_NAME:-wayabot}
    
    # Optional: ElevenLabs
    echo ""
    echo -e "${YELLOW}5. ELEVENLABS API KEY (optional - for voice replies)${NC}"
    echo "   Get it from https://elevenlabs.io"
    echo "   Press Enter to skip"
    read -p "ElevenLabs API Key: " ELEVENLABS_API_KEY
    
    # Optional: Hume AI
    echo ""
    echo -e "${YELLOW}6. HUME AI API KEY (optional - for emotion detection)${NC}"
    echo "   Get it from https://hume.ai"
    echo "   Press Enter to skip"
    read -p "Hume API Key: " HUME_API_KEY
    
    # Create .env file
    cat > .env << EOF
# =============================================================================
# WAYA BOT CONFIGURATION
# Generated on $(date)
# =============================================================================

# Telegram Bot (REQUIRED)
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}

# Groq AI (REQUIRED)
GROQ_API_KEY=${GROQ_API_KEY}

# Domain for webhook
BOT_DOMAIN=${BOT_DOMAIN}

# Database
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}

# ElevenLabs Voice AI (optional)
ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}

# Hume Emotion AI (optional)
HUME_API_KEY=${HUME_API_KEY}
EOF

    chmod 600 .env
    echo -e "${GREEN}Environment file created${NC}"
    fi  # End of manual config option
fi  # End of .env check

# Load environment
source .env

# =============================================================================
# STEP 3: Create SSL Directory
# =============================================================================
echo -e "\n${YELLOW}[3/6] Setting up SSL...${NC}"

mkdir -p ssl

# Create self-signed cert for initial setup (will be replaced by Let's Encrypt)
if [ ! -f ssl/fullchain.pem ]; then
    echo "Creating temporary self-signed certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/privkey.pem \
        -out ssl/fullchain.pem \
        -subj "/CN=${BOT_DOMAIN:-localhost}"
    echo -e "${GREEN}SSL certificates created${NC}"
fi

# =============================================================================
# STEP 4: Build and Start Containers
# =============================================================================
echo -e "\n${YELLOW}[4/6] Building and starting containers...${NC}"

docker compose down 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

echo -e "${GREEN}Containers started${NC}"

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# =============================================================================
# STEP 5: Set Up Webhook
# =============================================================================
echo -e "\n${YELLOW}[5/6] Setting up Telegram webhook...${NC}"

# Determine protocol
if [ -f ssl/fullchain.pem ]; then
    WEBHOOK_URL="https://${BOT_DOMAIN}"
else
    WEBHOOK_URL="http://${BOT_DOMAIN}"
fi

# Set webhook
echo "Setting webhook to: ${WEBHOOK_URL}/webhook"

response=$(curl -s -X POST "http://localhost:8000/set-webhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${WEBHOOK_URL}\"}")

if echo "$response" | grep -q "success"; then
    echo -e "${GREEN}Webhook set successfully${NC}"
else
    echo -e "${YELLOW}Webhook response: ${response}${NC}"
    echo "You may need to set it manually after SSL is configured"
fi

# =============================================================================
# STEP 6: Final Status
# =============================================================================
echo -e "\n${YELLOW}[6/6] Checking status...${NC}"

# Health check
health=$(curl -s http://localhost:8000/health 2>/dev/null || echo '{"status":"error"}')
echo "Health check: $health"

echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║   WAYA BOT SETUP COMPLETE!                                    ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}Your bot is now running!${NC}"
echo ""
echo "Commands:"
echo "  - View logs:        docker compose logs -f waya"
echo "  - Restart bot:      docker compose restart waya"
echo "  - Stop all:         docker compose down"
echo "  - Start all:        docker compose up -d"
echo ""
echo "Webhook URL: ${WEBHOOK_URL}/webhook"
echo ""
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "1. Open Telegram and message your bot"
echo "2. Send /start to begin"
echo ""

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo -e "${YELLOW}TIP: Add ELEVENLABS_API_KEY to .env for voice replies${NC}"
fi

echo ""
echo -e "${GREEN}Enjoy using Waya!${NC}"
