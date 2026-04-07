# Waya Bot - AI-Powered Telegram Bot Builder

An intelligent Telegram bot that helps users create custom bots, set reminders, take notes, manage tasks, and chat with AI. Powered by Groq AI for lightning-fast responses.

## Features

- **AI Chat** - Natural conversations powered by Groq's Llama 3.3 70B
- **Bot Builder** - Create custom Telegram bots instantly with AI
- **Voice Messages** - Transcription with Whisper + text-to-speech with ElevenLabs
- **Reminders** - Natural language reminder parsing
- **Notes & Tasks** - Quick note-taking and task management
- **Gamification** - XP, levels, streaks, and achievements

## Quick Start (DigitalOcean)

### Prerequisites

- DigitalOcean account
- Domain name (optional but recommended)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Groq API Key (from [console.groq.com](https://console.groq.com))

### Step 1: Create a DigitalOcean Droplet

1. Go to [DigitalOcean](https://cloud.digitalocean.com)
2. Click **Create** > **Droplets**
3. Choose:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic, $6/mo (1GB RAM) minimum
   - **Region**: Choose closest to your users
4. Add your SSH key or create a password
5. Click **Create Droplet**

### Step 2: Set Up PostgreSQL Database

**Option A: DigitalOcean Managed Database (Recommended)**

1. Go to **Databases** > **Create Database Cluster**
2. Choose **PostgreSQL 15**
3. Select $15/mo plan (1GB RAM)
4. Click **Create**
5. Copy the connection string from the **Connection Details**

**Option B: Install PostgreSQL on Droplet**

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib -y

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
```

```sql
CREATE USER wayabot WITH PASSWORD 'your_secure_password';
CREATE DATABASE wayabot OWNER wayabot;
GRANT ALL PRIVILEGES ON DATABASE wayabot TO wayabot;
\q
```

### Step 3: Deploy the Bot

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Install required packages
sudo apt update
sudo apt install python3 python3-pip python3-venv git nginx -y

# Clone the repository
git clone https://github.com/sidihost/Wayabot-vz.git
cd Wayabot-vz/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn python-telegram-bot groq asyncpg pydantic-settings httpx

# Create environment file
nano .env
```

### Step 4: Configure Environment Variables

Create a `.env` file in the `backend` folder:

```env
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
GROQ_API_KEY=your_groq_api_key_from_console
DATABASE_URL=postgresql://wayabot:your_secure_password@localhost:5432/wayabot

# Optional - Voice AI (ElevenLabs)
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Optional - Emotion AI (Hume)
HUME_API_KEY=your_hume_api_key
```

**How to get API keys:**

1. **Telegram Bot Token**: Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, follow prompts
2. **Groq API Key**: Sign up at [console.groq.com](https://console.groq.com), go to API Keys
3. **ElevenLabs API Key** (optional): Sign up at [elevenlabs.io](https://elevenlabs.io), go to Profile > API Key
4. **Hume API Key** (optional): Sign up at [hume.ai](https://hume.ai), get API key from dashboard

### Step 5: Run the Bot

**Test run:**

```bash
cd ~/Wayabot-vz/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Production run with systemd:**

```bash
# Create service file
sudo nano /etc/systemd/system/wayabot.service
```

Paste this content:

```ini
[Unit]
Description=Waya Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/Wayabot-vz/backend
Environment=PATH=/root/Wayabot-vz/backend/venv/bin
EnvironmentFile=/root/Wayabot-vz/backend/.env
ExecStart=/root/Wayabot-vz/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable wayabot
sudo systemctl start wayabot

# Check status
sudo systemctl status wayabot

# View logs
sudo journalctl -u wayabot -f
```

### Step 6: Set Up Webhook (Required for Telegram)

**Option A: With domain (recommended)**

```bash
# Install Certbot for SSL
sudo apt install certbot python3-certbot-nginx -y

# Configure Nginx
sudo nano /etc/nginx/sites-available/wayabot
```

```nginx
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
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/wayabot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Set webhook
curl -X POST https://your-domain.com/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com"}'
```

**Option B: Without domain (using IP)**

Telegram requires HTTPS for webhooks. Without a domain, use a reverse proxy service or polling mode.

For testing, you can use ngrok:

```bash
# Install ngrok
snap install ngrok

# Run ngrok
ngrok http 8000

# Copy the https URL and set webhook
curl -X POST https://YOUR_NGROK_URL/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_NGROK_URL"}'
```

### Step 7: Test Your Bot

1. Open Telegram and search for your bot username
2. Send `/start` to begin
3. Try these commands:
   - `/help` - See all commands
   - `/build a coffee shop bot` - Create a custom bot
   - `/remind call mom in 2 hours` - Set a reminder
   - `/note Meeting ideas` - Create a note
   - `/task Buy groceries` - Add a task
   - Just chat naturally - The AI will respond

## Commands Reference

### Core Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message and quick actions |
| `/help` | Full command reference |
| `/menu` | Interactive menu |
| `/profile` | Your stats, level, and XP |
| `/settings` | Preferences |

### Bot Building
| Command | Description |
|---------|-------------|
| `/build <description>` | Create a custom bot with AI |
| `/templates` | Browse bot templates |
| `/mybots` | List your created bots |
| `/usebot <id>` | Activate a specific bot |

### Productivity
| Command | Description |
|---------|-------------|
| `/remind <text>` | Set a reminder (natural language) |
| `/reminders` | List pending reminders |
| `/note <title> \| <content>` | Create a note |
| `/notes` | List your notes |
| `/task <description>` | Create a task |
| `/tasks` | List your tasks |
| `/done <id>` | Complete a task |

### AI Features
| Command | Description |
|---------|-------------|
| `/chat` | Start AI chat mode |
| `/clear` | Clear conversation history |
| `/translate <lang> <text>` | Translate text |
| `/summarize <text>` | Summarize text |
| `/quiz <topic>` | Generate a quiz question |

### Voice (requires ElevenLabs API key)
| Command | Description |
|---------|-------------|
| `/voice <text>` | Convert text to speech |
| `/voices` | List available voices |
| `/setvoice <name>` | Set default voice |

## Troubleshooting

### Bot not responding

1. Check if service is running: `sudo systemctl status wayabot`
2. Check logs: `sudo journalctl -u wayabot -f`
3. Verify webhook: `curl https://your-domain.com/webhook-info`

### Database connection errors

1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Test connection: `psql -U wayabot -d wayabot -h localhost`
3. Verify DATABASE_URL in `.env`

### API errors

1. Verify your GROQ_API_KEY is valid at [console.groq.com](https://console.groq.com)
2. Check if you have API credits remaining
3. The model used is `llama-3.3-70b-versatile`

### Webhook errors

1. Ensure your domain has valid SSL (HTTPS required)
2. Check Nginx config: `sudo nginx -t`
3. Verify firewall allows ports 80 and 443: `sudo ufw status`

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `GROQ_API_KEY` | Yes | API key from console.groq.com |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ELEVENLABS_API_KEY` | No | For text-to-speech features |
| `HUME_API_KEY` | No | For emotion detection |

## Architecture

```
backend/
├── main.py          # FastAPI app, webhook handlers
├── handlers.py      # Telegram command/message handlers
├── ai_engine.py     # Groq AI integration
├── database.py      # PostgreSQL operations
├── voice_engine.py  # ElevenLabs TTS
├── emotion_engine.py# Hume AI emotions
├── scheduler.py     # Reminder scheduler
└── config.py        # Configuration
```

## Support

- Create an issue on GitHub
- Check logs: `sudo journalctl -u wayabot -f`

## License

MIT License
