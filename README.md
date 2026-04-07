# Waya - AI-Powered Telegram Bot Builder

An intelligent Telegram bot that helps users create custom bots, set reminders, take notes, manage tasks, and chat with AI. Powered by Groq AI for lightning-fast responses with real-time streaming.

## Features

- **AI Chat with Streaming** - Real-time typing effect as AI responds
- **Bot Builder** - Create custom Telegram bots just by describing them
- **Voice Messages** - Transcription with Groq Whisper + text-to-speech with ElevenLabs
- **Smart Reminders** - Natural language ("remind me to call mom in 2 hours")
- **Notes & Tasks** - Quick note-taking and task management
- **AI Personalities** - Create custom AI personalities
- **Emotion AI** - Empathic responses based on your mood
- **Gamification** - XP, levels, streaks, and achievements

---

## Deploy to DigitalOcean (3 Options)

### Option 1: One-Click Docker Setup (Easiest)

```bash
# 1. Create a DigitalOcean Droplet
#    - Image: Ubuntu 22.04
#    - Plan: Basic $6/mo (1GB RAM)
#    - Add your SSH key

# 2. SSH into your droplet
ssh root@your-droplet-ip

# 3. Clone the repo
git clone https://github.com/sidihost/Wayabot-vz.git
cd Wayabot-vz

# 4. Run the setup script
chmod +x setup.sh
sudo ./setup.sh
```

The script will ask for your API keys and set everything up automatically.

---

### Option 2: Docker Compose (Manual)

```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone repo
git clone https://github.com/sidihost/Wayabot-vz.git
cd Wayabot-vz

# Create .env file
cp .env.example .env
nano .env   # Add your API keys

# Start everything
docker compose up -d

# Set webhook (replace YOUR_IP with your droplet IP)
curl -X POST http://localhost:8000/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "http://YOUR_IP:8000"}'
```

---

### Option 3: Manual Setup (No Docker)

```bash
# SSH into droplet
ssh root@your-droplet-ip

# Install dependencies
apt update && apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib

# Setup PostgreSQL
sudo -u postgres psql << EOF
CREATE USER waya WITH PASSWORD 'wayabot123';
CREATE DATABASE wayabot OWNER waya;
EOF

# Clone repo
git clone https://github.com/sidihost/Wayabot-vz.git
cd Wayabot-vz/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env
cat > .env << EOF
TELEGRAM_BOT_TOKEN=your_token_here
GROQ_API_KEY=your_key_here
DATABASE_URL=postgresql://waya:wayabot123@localhost:5432/wayabot
EOF

# Run
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Getting Your API Keys

### 1. Telegram Bot Token (Required)

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow the prompts to name your bot
4. Copy the token (looks like: `123456789:ABCdefGHI...`)

### 2. Groq API Key (Required)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / Log in
3. Go to **API Keys** in the sidebar
4. Click **Create API Key**
5. Copy the key

### 3. ElevenLabs API Key (Optional - Voice)

1. Go to [elevenlabs.io](https://elevenlabs.io)
2. Sign up and go to your profile
3. Copy your API key

### 4. Hume AI API Key (Optional - Emotions)

1. Go to [hume.ai](https://hume.ai)
2. Sign up and get API key from dashboard

---

## Environment Variables

Create a `.env` file with these variables:

```env
# REQUIRED
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://waya:wayabot123@postgres:5432/wayabot

# For Docker Compose
DB_USER=waya
DB_PASSWORD=wayabot123
DB_NAME=wayabot

# OPTIONAL
ELEVENLABS_API_KEY=your_elevenlabs_key
HUME_API_KEY=your_hume_key
```

---

## Setting Up Webhook

After the bot is running, set up the Telegram webhook:

```bash
# With domain (HTTPS)
curl -X POST https://your-domain.com/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com"}'

# With IP only (HTTP - for testing)
curl -X POST http://YOUR_IP:8000/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "http://YOUR_IP:8000"}'
```

Check webhook status:
```bash
curl http://localhost:8000/webhook-info
```

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show all commands |
| `/menu` | Interactive menu |
| `/build <description>` | Create a custom bot |
| `/mybots` | List your bots |
| `/remind <text>` | Set a reminder |
| `/reminders` | View reminders |
| `/note <text>` | Save a note |
| `/notes` | View notes |
| `/task <text>` | Create a task |
| `/tasks` | View tasks |
| `/voice` | Toggle voice mode |
| `/voices` | Available voices |
| `/setvoice <name>` | Set your voice |
| `/profile` | Your stats |
| `/settings` | Bot settings |

### Smart Natural Language

Just type naturally - no commands needed:

- `"remind me to call mom tomorrow at 3pm"`
- `"note: meeting ideas for the project"`
- `"task: buy groceries"`
- `"create a customer support bot for my coffee shop"`

---

## Useful Commands

```bash
# View logs
docker compose logs -f waya

# Restart bot
docker compose restart waya

# Stop everything
docker compose down

# Start everything
docker compose up -d

# Check health
curl http://localhost:8000/health

# Check bot info
curl http://localhost:8000/bot-info
```

---

## Production Setup with SSL

For HTTPS (required for production webhooks):

```bash
# Install Nginx and Certbot
apt install nginx certbot python3-certbot-nginx -y

# Create Nginx config
cat > /etc/nginx/sites-available/wayabot << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/wayabot /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# Get SSL certificate
certbot --nginx -d your-domain.com

# Set webhook with HTTPS
curl -X POST https://your-domain.com/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com"}'
```

---

## Running as a Service (systemd)

```bash
# Create service file
cat > /etc/systemd/system/wayabot.service << 'EOF'
[Unit]
Description=Waya Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Wayabot-vz/backend
EnvironmentFile=/root/Wayabot-vz/backend/.env
ExecStart=/root/Wayabot-vz/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable wayabot
systemctl start wayabot

# Check status
systemctl status wayabot

# View logs
journalctl -u wayabot -f
```

---

## Troubleshooting

### Bot not responding?
```bash
# Check if running
docker compose ps
# or
systemctl status wayabot

# Check logs
docker compose logs -f waya
# or
journalctl -u wayabot -f

# Verify webhook
curl http://localhost:8000/webhook-info
```

### Database connection error?
```bash
# Check PostgreSQL
docker compose ps postgres
# or
systemctl status postgresql

# Test connection
psql -U waya -d wayabot -h localhost
```

### Model not found error?
The bot uses `llama-3.3-70b-versatile`. Make sure your Groq API key is valid at [console.groq.com](https://console.groq.com).

### Voice not working?
1. Add `ELEVENLABS_API_KEY` to your `.env`
2. Restart: `docker compose restart waya`

---

## Project Structure

```
Wayabot-vz/
├── backend/
│   ├── main.py           # FastAPI app & webhooks
│   ├── handlers.py       # Telegram handlers
│   ├── ai_engine.py      # Groq AI (Llama 3.3)
│   ├── voice_engine.py   # ElevenLabs TTS
│   ├── emotion_engine.py # Hume AI emotions
│   ├── database.py       # PostgreSQL
│   ├── scheduler.py      # Reminders
│   ├── config.py         # Settings
│   └── requirements.txt  # Python deps
├── docker-compose.yml    # Docker setup
├── Dockerfile           # Bot container
├── nginx.conf           # Reverse proxy
├── setup.sh             # One-click setup
├── .env.example         # Env template
└── README.md            # This file
```

---

## License

MIT License - feel free to use and modify!
