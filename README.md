# Waya - AI-Powered Telegram Bot Builder

An intelligent Telegram bot that helps users create custom bots, set reminders, take notes, manage tasks, and chat with AI. Powered by Groq AI for lightning-fast responses with real-time streaming.

## Features

- **AI Chat with Streaming** - Real-time typing effect as AI responds
- **Advanced Bot Builder** - Create powerful AI bots with cards, automation, and code export
  - Create with AI: Describe what you want, get a working bot
  - Feature Cards: Select capabilities like auto-replies, scheduling, forms
  - Template Library: Pre-built bots for business, education, lifestyle
  - Bot Management: View, edit, delete, and share your bots
  - Knowledge Base: Train your bot with custom Q&A
  - Automations: Auto-reply rules for keywords
  - Export Code: Get standalone Python code for your bot
- **Voice Messages** - Transcription with Groq Whisper + text-to-speech with ElevenLabs
- **Smart Reminders** - Natural language ("remind me to call mom in 2 hours")
- **Notes & Tasks** - Quick note-taking and task management
- **AI Personalities** - Create custom AI personalities
- **Emotion AI** - Empathic responses based on your mood
- **Gamification** - XP, levels, streaks, and achievements

## Bot Builder - Full Feature List

### Create Bots

```
/build a coffee shop assistant bot
/build a fitness coach that motivates users
/build a coding tutor for Python
/build a customer support bot for my store
/build a quiz bot about science
```

Or just type naturally:
```
I need a bot for my restaurant
create a meditation guide bot
make me a quiz bot about history
```

### Manage Bots

- `/mybots` - View all your bots
- Tap "Edit" on any bot to:
  - Change name, personality, greeting
  - Add custom commands
  - Add knowledge base entries
  - Create automation rules
  - View analytics
  - Export as Python code

### Edit via Prompt

Just describe what you want to change:
```
make my coffee bot more friendly
add a pricing command to my support bot
change the greeting to be more professional
```

### Bot Features You Can Add

| Feature | Description |
|---------|-------------|
| AI Chat | Smart conversations with context memory |
| Commands | Custom /commands your bot responds to |
| Auto Replies | Trigger responses on keywords |
| Scheduler | Send messages at specific times |
| Knowledge Base | Train bot with custom Q&A |
| Buttons | Interactive menus and actions |
| Forms | Collect user information |
| Analytics | Track bot usage and stats |
| Voice | Voice messages and TTS |
| Multi-Language | Support multiple languages |

### After Creation

- Get a shareable link: `t.me/YourBot?start=bot_123`
- Bot is immediately active
- AI greets users automatically
- Export standalone Python code to run anywhere

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

The script gives you two options:
1. **Import from Vercel** - If you have env vars in Vercel, it will pull them automatically
2. **Enter manually** - Walk through each API key step by step

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

# Start everything (webhook auto-configures if BOT_DOMAIN is set!)
docker compose up -d

# Check logs to verify webhook is set
docker compose logs -f wayabot
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
# With your domain (HTTPS)
curl -X POST https://waya.qzz.io/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://waya.qzz.io"}'
```

Check webhook status:
```bash
curl https://waya.qzz.io/webhook-info
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
    server_name waya.qzz.io;

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
certbot --nginx -d waya.qzz.io

# Set webhook with HTTPS
curl -X POST https://waya.qzz.io/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://waya.qzz.io"}'
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
