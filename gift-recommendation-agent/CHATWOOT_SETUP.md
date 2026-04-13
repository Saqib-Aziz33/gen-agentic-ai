# 🔄 Chatwoot Integration Setup

This guide shows you how to integrate the Gift Recommendation Agent with Chatwoot as an agent bot.

## 📋 Prerequisites

- A Chatwoot account (self-hosted or cloud)
- Python 3.11+ with dependencies installed
- OpenAI and Tavily API keys

## 🚀 Setup Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Create Agent Bot in Chatwoot

1. Log in to your Chatwoot instance
2. Go to **Settings** → **Bots** (or **Agent Bots**)
3. Click **Add Bot** or **Create Agent Bot**
4. Fill in the details:
   - **Name**: `Gift Recommendation Assistant`
   - **Description**: `AI-powered gift recommendation agent`
   - **Outgoing URL**: Your webhook URL (see Step 3)
5. Click **Create**
6. **Copy the Access Token** shown after creation (you'll need this!)

### Step 3: Configure Webhook URL

Your webhook URL depends on your setup:

#### Local Development (Testing)

Use **ngrok** or **localtunnel** to expose your local server:

```bash
# Install ngrok: https://ngrok.com/download
# Start your bot server first
python chatwoot_bot.py

# In another terminal, expose port 5000
ngrok http 5000
```

Ngrok will give you a public URL like: `https://abc123.ngrok-free.app`

Set the **Outgoing URL** in Chatwoot to: `https://abc123.ngrok-free.app/webhook`

#### Production Deployment

Deploy to a server with a public IP/domain:

```
https://your-domain.com/webhook
```

### Step 4: Set Environment Variables

Create or update your `.env` file:

```env
# Required
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key

# Chatwoot Configuration
CHATWOOT_ACCESS_TOKEN=copy_from_step_2
CHATWOOT_BASE_URL=https://app.chatwoot.com  # or your self-hosted URL

# Optional
PORT=5000
```

### Step 5: Run the Chatwoot Bot

```bash
python chatwoot_bot.py
```

You should see:

```
🚀 Starting Gift Recommendation Chatwoot Agent Bot...
📡 Webhook URL: http://localhost:5000/webhook
💚 Health check: http://localhost:5000/
✅ Server is running! Press Ctrl+C to stop.
```

### Step 6: Test the Integration

1. Go to a Chatwoot inbox where the bot is enabled
2. Start a conversation or send a message
3. Type: `I need a birthday gift for my wife`
4. The bot should respond with a follow-up question or recommendations

## 🎯 How It Works

### Message Flow

```
Customer sends message
    ↓
Chatwoot webhook → /webhook endpoint
    ↓
Chatwoot Bot processes message
    ↓
Runs Gift Recommendation Agent
    ↓
Sends response back via Chatwoot API
    ↓
Customer sees bot's reply
```

### Webhook Events

The bot listens for these events:

| Event | Action |
|-------|--------|
| `message_created` | Process customer message and respond |
| Other events | Ignored |

### Message Types

- **Incoming (0)**: Customer messages - **processed**
- **Outgoing (1)**: Agent messages - **ignored**
- **Outgoing Bot (3)**: Bot messages - **ignored**

## 🔧 API Endpoints

### POST `/webhook` (Async)

Main webhook handler. Processes messages asynchronously to avoid timeouts.

**Request:**
```json
{
  "event": "message_created",
  "message": {
    "id": 123,
    "content": "I need a gift for my friend",
    "message_type": 0,
    "sender": {
      "id": 456,
      "name": "John Doe",
      "type": "contact"
    }
  },
  "conversation": {
    "id": 789,
    "inbox_id": 12,
    "status": "open"
  },
  "account": {
    "id": 1,
    "name": "My Account"
  }
}
```

**Response:** `200 OK` immediately, processes in background

### POST `/webhook/sync` (Sync)

Synchronous webhook handler. Waits for completion before responding.

Use this if you prefer synchronous processing.

### GET `/`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "bot": "Gift Recommendation Agent"
}
```

## 💬 Bot Commands in Chatwoot

Customers can use these commands in chat:

| Command | Action |
|---------|--------|
| `reset` or `/reset` | Clear conversation and start over |
| Any text message | Processed as gift query |

## 🏗️ Production Deployment

### Option 1: Deploy to VPS/Cloud Server

1. Deploy to a server (DigitalOcean, AWS, etc.)
2. Use a reverse proxy (nginx) with SSL
3. Use a process manager (systemd or PM2)

**systemd service file:**

```ini
[Unit]
Description=Gift Recommendation Chatwoot Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/gift-recommendation-agent
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/python chatwoot_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**nginx config:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 2: Deploy to Railway/Render/Heroku

Create a `Procfile`:

```
web: python chatwoot_bot.py
```

Deploy and set the provided URL as your webhook URL.

### Option 3: Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "chatwoot_bot.py"]
```

Build and run:

```bash
docker build -t gift-bot-chatwoot .
docker run -d -p 5000:5000 --env-file .env gift-bot-chatwoot
```

## 🔒 Security Best Practices

1. **Use HTTPS** - Always deploy with SSL in production
2. **Verify webhook signatures** - Chatwoot signs webhooks (implement if needed)
3. **Rate limiting** - Use nginx or a middleware to prevent abuse
4. **Access token security** - Never commit `CHATWOOT_ACCESS_TOKEN` to git
5. **Conversation isolation** - Each conversation has its own state

## 🐛 Troubleshooting

### Bot doesn't respond in Chatwoot

- Check that the webhook URL is correct and accessible
- Verify `CHATWOOT_ACCESS_TOKEN` is correct
- Check server logs: `python chatwoot_bot.py`
- Ensure the bot is attached to the inbox: Settings → Bots → Attach to Inbox

### Webhook timeout errors

- The async `/webhook` handler returns immediately
- If using `/webhook/sync`, ensure your server can process within timeout
- Increase timeout in Chatwoot settings if needed

### "401 Unauthorized" errors

- Your `CHATWOOT_ACCESS_TOKEN` is incorrect or expired
- Regenerate the token in Chatwoot Settings → Bots

### State not persisting

- In-memory state resets on server restart
- For production, implement Redis/DB storage (see code comments)

## 📊 Monitoring

Add logging and monitoring:

```python
# Logs show in console when running
# In production, send logs to:
# - CloudWatch (AWS)
# - Papertrail
# - LogDNA
# - Your preferred log aggregator
```

## 🎓 Advanced Customization

### Change Bot Behavior

Edit `agent.py` to:
- Add more required fields
- Change recommendation style
- Modify conversation flow

### Add Custom Commands

Edit `chatwoot_bot.py` webhook handler:

```python
if message_content.lower() == "help":
    await send_chatwoot_message(account_id, conversation_id, "Help text here")
    return
```

### Multi-Language Support

Add language detection and translate prompts before processing.

### Analytics

Track usage by logging to database:

```python
# In process_gift_query():
log_interaction(account_id, conversation_id, user_message, result)
```

## 📚 Additional Resources

- [Chatwoot Agent Bots Documentation](https://developers.chatwoot.com)
- [Chatwoot API Reference](https://www.chatwoot.com/developers/api/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

**Need Help?** Check the logs or review:

- `chatwoot_bot.py` - Chatwoot webhook handler
- `agent.py` - Gift recommendation agent logic
- `README.md` - General project documentation
