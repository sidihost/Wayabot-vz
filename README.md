# Waya - AI-Powered Telegram Bot Builder

An intelligent Telegram bot that helps users create custom bots, set reminders, take notes, manage tasks, and chat with AI. Powered by Groq AI for lightning-fast responses with real-time streaming.

## What Makes Waya Special

Waya is a **SaaS AI Bot Builder** that runs like an autonomous agent:

- **Zero Code Required** - Users describe what they want in natural language, Waya builds it
- **Instant Deployment** - Bots go live immediately after creation (no manual setup)
- **Fully Autonomous** - Bots run 24/7 on our infrastructure, users never see code
- **AI Agent Features** - Auto-reactions, smart suggestions, auto-moderation, optimal scheduling
- **Celebration Animations** - Confetti, rockets, and checkmarks when bots are created

## Core Features

### AI Bot Builder (Autonomous)
- **Natural Language Creation** - "Build me a coffee shop assistant bot"
- **Auto-Deploy** - Bot starts running instantly on our servers
- **Hot-Reload** - Edit bot behavior and changes apply immediately
- **No BotFather Needed** - Bots run through Waya (users can export code later if they want their own)

### AI Agent Capabilities
| Feature | Description |
|---------|-------------|
| **Auto-React** | Analyzes messages and adds relevant emoji reactions automatically |
| **Auto-Moderate** | Detects spam, floods, inappropriate content and takes action |
| **Smart Suggestions** | AI generates reply buttons based on conversation context |
| **Optimal Scheduling** | Learns best posting times from engagement analytics |

### Voice AI (ElevenLabs)
- Text-to-speech with 12+ premium voices
- Voice cloning capabilities
- Voice style customization

### Emotion AI (Hume)
- Real-time emotion detection from text
- Empathic response mode
- Mood tracking and wellbeing insights

### Productivity Tools
- **Smart Reminders** - Natural language ("remind me to call mom in 2 hours")
- **Notes** - Quick note-taking with full-text search
- **Tasks** - Task management with priorities

### Gamification
- XP, levels, and streaks
- Achievements and leaderboards
- Profile stats

## How Bot Creation Works

```
User: "Build me a customer support bot for my coffee shop"

Waya: 
1. AI generates bot configuration (personality, commands, responses)
2. Bot is automatically deployed to our runtime engine
3. Celebration animation plays (confetti + rocket + checkmark!)
4. User gets a shareable link - bot is immediately live
5. All AI agent features are enabled by default
```

**The user never:**
- Sees any code
- Needs to set up webhooks
- Needs to go to BotFather
- Needs to deploy anything

**Everything is automatic.**

## Bot Builder Commands

### Create Bots
```
/build a coffee shop assistant bot
/build a fitness coach that motivates users
/build a coding tutor for Python
```

Or just type naturally:
```
I need a bot for my restaurant
create a meditation guide bot
make me a quiz bot about history
```

### Manage Bots
- `/mybots` - View all your bots
- Tap "Edit" to change name, personality, commands
- Changes apply instantly (hot-reload)

### Edit via Prompt
```
make my coffee bot more friendly
add a pricing command to my support bot
change the greeting to be more professional
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Waya Platform                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌──────────────────┐                 │
│   │   Telegram  │────▶│   Main Webhook   │                 │
│   │   Messages  │     │   (main.py)      │                 │
│   └─────────────┘     └────────┬─────────┘                 │
│                                │                            │
│                    ┌───────────┴───────────┐               │
│                    ▼                       ▼               │
│         ┌─────────────────┐    ┌─────────────────┐        │
│         │  Bot Builder    │    │  Bot Runtime    │        │
│         │  (bot_builder)  │    │  (bot_runtime)  │        │
│         │                 │    │                 │        │
│         │ - AI Generation │    │ - Auto-Deploy   │        │
│         │ - Config Parse  │    │ - Hot-Reload    │        │
│         │ - Celebrations  │    │ - Health Check  │        │
│         └────────┬────────┘    └────────┬────────┘        │
│                  │                      │                  │
│                  └──────────┬───────────┘                  │
│                             ▼                              │
│         ┌─────────────────────────────────────┐           │
│         │         AI Agent Engine             │           │
│         │                                     │           │
│         │  ┌───────────┐ ┌───────────────┐   │           │
│         │  │ Auto-React│ │ Auto-Moderate │   │           │
│         │  └───────────┘ └───────────────┘   │           │
│         │  ┌───────────┐ ┌───────────────┐   │           │
│         │  │Suggestions│ │ Scheduler     │   │           │
│         │  └───────────┘ └───────────────┘   │           │
│         └─────────────────────────────────────┘           │
│                                                            │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│   │ PostgreSQL │  │  Groq AI   │  │ ElevenLabs │         │
│   │  Database  │  │  (LLama)   │  │   (Voice)  │         │
│   └────────────┘  └────────────┘  └────────────┘         │
│                                                            │
└─────────────────────────────────────────────────────────────┘
```

## New Backend Modules

| Module | Purpose |
|--------|---------|
| `bot_runtime.py` | Autonomous bot execution engine - deploys and runs all user bots |
| `agent_engine.py` | AI agent features - auto-reactions with emotion analysis |
| `moderation.py` | Auto-moderation - spam detection, flood control, content filtering |
| `suggestions.py` | Smart reply suggestions with AI |
| `content_scheduler.py` | Optimal posting time analysis and scheduling |
| `animations.py` | Celebration effects - confetti, rockets, checkmarks |
| `telegram_api.py` | Advanced Telegram Bot API wrapper |

## API Endpoints

### Health & Status
```
GET /              - Root info
GET /health        - Health check with bot runtime status
GET /runtime/bots  - List all running user bots
GET /runtime/bots/{id} - Status of specific bot
```

### Webhooks
```
POST /webhook      - Telegram webhook endpoint
POST /set-webhook  - Configure webhook URL
GET  /webhook-info - Current webhook configuration
```

---

## Deploy to DigitalOcean

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

### Option 2: Docker Compose

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

# Check logs
docker compose logs -f wayabot
```

---

## Getting Your API Keys

### 1. Telegram Bot Token (Required)

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow the prompts to name your bot
4. Copy the token

**Note:** This is for the main Waya bot. User-created bots run through Waya's infrastructure and don't need separate tokens.

### 2. Groq API Key (Required)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / Log in
3. Go to **API Keys** in the sidebar
4. Click **Create API Key**

### 3. ElevenLabs API Key (Optional - Voice)

1. Go to [elevenlabs.io](https://elevenlabs.io)
2. Sign up and copy your API key

### 4. Hume AI API Key (Optional - Emotions)

1. Go to [hume.ai](https://hume.ai)
2. Sign up and get API key

---

## Environment Variables

```env
# REQUIRED
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://waya:wayabot123@postgres:5432/wayabot

# For auto-webhook setup
BOT_DOMAIN=your-domain.com

# OPTIONAL
ELEVENLABS_API_KEY=your_elevenlabs_key
HUME_API_KEY=your_hume_key
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
| `/note <text>` | Save a note |
| `/task <text>` | Create a task |
| `/voice` | Toggle voice mode |
| `/profile` | Your stats |

### Natural Language (No Commands Needed)

Just type naturally:
- `"remind me to call mom tomorrow at 3pm"`
- `"note: meeting ideas for the project"`
- `"create a customer support bot for my coffee shop"`

---

## Project Structure

```
Wayabot-vz/
├── backend/
│   ├── main.py              # FastAPI app & webhooks
│   ├── handlers.py          # Telegram handlers
│   ├── bot_builder.py       # Bot creation engine
│   ├── bot_runtime.py       # Autonomous bot execution
│   ├── agent_engine.py      # Auto-reactions & AI agent
│   ├── moderation.py        # Auto-moderation system
│   ├── suggestions.py       # Smart reply suggestions
│   ├── content_scheduler.py # Optimal posting times
│   ├── animations.py        # Celebration effects
│   ├── telegram_api.py      # Advanced Telegram API
│   ├── ai_engine.py         # Groq AI (Llama 3.3)
│   ├── voice_engine.py      # ElevenLabs TTS
│   ├── emotion_engine.py    # Hume AI emotions
│   ├── database.py          # PostgreSQL
│   ├── scheduler.py         # Reminders
│   └── config.py            # Settings
├── docker-compose.yml       # Docker setup
├── Dockerfile               # Bot container
├── setup.sh                 # One-click setup
└── README.md                # This file
```

---

## Database Schema (New Agent Tables)

```sql
-- Bot agent settings
bot_agent_settings (bot_id, auto_react_enabled, auto_moderate_enabled, ...)

-- Scheduled content queue
scheduled_content (id, bot_id, content, scheduled_at, optimal_score, ...)

-- Moderation logs
moderation_logs (id, bot_id, action_type, reason, confidence_score, ...)

-- Engagement analytics
engagement_analytics (bot_id, hour_of_day, day_of_week, engagement_score, ...)

-- Auto-reaction history
auto_reactions (id, bot_id, reaction_emoji, detected_emotion, ...)

-- Smart suggestion tracking
suggestion_usage (id, bot_id, suggestion_text, was_used, ...)
```

---

## Troubleshooting

### Bot not responding?
```bash
# Check if running
docker compose ps

# Check logs
docker compose logs -f wayabot

# Check bot runtime status
curl http://localhost:8000/runtime/bots
```

### User bots not working?
```bash
# Check runtime engine status
curl http://localhost:8000/health

# Should show:
# "bot_runtime": "running"
# "active_bots": <number>
```

---

## License

MIT License - feel free to use and modify!
