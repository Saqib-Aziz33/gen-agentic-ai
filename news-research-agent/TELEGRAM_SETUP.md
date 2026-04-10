# Telegram Bot Setup for News & Research Agent

This guide will help you set up and run the Telegram bot for your News & Research Agent.

## 📦 Prerequisites

### 1. Install Dependencies

```bash
pip install python-telegram-bot
```

Or install all project dependencies:

```bash
pip install -r requirements.txt
```

## 🤖 Create Your Telegram Bot

### Step 1: Get Bot Token from @BotFather

1. Open Telegram and search for **@BotFather**
2. Send the command `/newbot`
3. Follow the prompts:
   - Choose a name for your bot (e.g., "News Research Assistant")
   - Choose a username for your bot (must end in 'bot', e.g., "my_news_bot")
4. **Copy the Bot Token** that @BotFather gives you (keep this secret!)

### Step 2: (Optional) Get Your User ID for Access Control

To restrict bot access to only yourself or specific users:

1. Search for **@userinfobot** on Telegram
2. Send it any message
3. It will reply with your User ID (a number like `123456789`)
4. Copy this ID if you want to restrict access

## 🔧 Configure Environment Variables

Add the following to your `.env` file:

```env
# Required - Your Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ

# Optional - Restrict access to specific users
# If not set, anyone can use the bot
ALLOWED_USER_IDS=your_user_id_here
```

**Example with restricted access:**

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
ALLOWED_USER_IDS=123456789,987654321
```

## 🚀 Run the Bot

### Start the bot:

```bash
python bot.py
```

You should see output like:

```
🚀 Starting News & Research Telegram Bot...
✅ Bot is running! Press Ctrl+C to stop.
📱 Bot username: @your_bot_username
```

### Stop the bot:

Press `Ctrl+C` in the terminal

## 📱 Using the Bot

Once running, open Telegram and search for your bot's username. Start a chat and use these commands:

### Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and see welcome message |
| `/help` | Show help with all available features |
| `/about` | Learn about the bot's technology |

### Example Queries

Just type your question in natural language:

- `What's happening in the world` - Get world news overview
- `Recent news about artificial intelligence` - Latest AI news
- `Who is Elon Musk` - Research about a person
- `Latest tech news in table format` - Tabular output
- `Climate change news as a list` - List format
- `What is happening with Donald Trump` - News about specific person

### Output Format Controls

You can request specific output formats:

- **Table format**: Add "table" or "tabular" to your query
  - Example: `Latest news in table format`
  
- **List format**: Add "list" or "bullets" to your query
  - Example: `Tech news as a bulleted list`
  
- **Prose format**: Default (paragraphs) - no special keyword needed

## 🔒 Security Best Practices

1. **Never share your bot token** - Keep it in `.env` and never commit to git
2. **Use ALLOWED_USER_IDS** in production to restrict access
3. **Rate limiting** - The bot handles Telegram's rate limits automatically
4. **Error handling** - All errors are logged and user-friendly messages are shown

## 🛠️ How It Works

The bot:

1. **Receives** your message on Telegram
2. **Sends** it to the News & Research Agent (LangGraph)
3. **Classifies** your intent (news, research, or overview)
4. **Fetches** relevant articles via Tavily Search
5. **Ranks** articles by importance
6. **Formats** the response based on your preferences
7. **Splits** long messages if needed (Telegram has 4096 char limit)
8. **Returns** the formatted response to you

## 🐛 Troubleshooting

### Bot doesn't respond

- Check that `TELEGRAM_BOT_TOKEN` is correctly set in `.env`
- Verify your `OPENAI_API_KEY` and `TAVILY_API_KEY` are set
- Check the terminal for error logs

### "Unauthorized" error

- If using `ALLOWED_USER_IDS`, make sure your user ID is in the list
- Get your user ID from @userinfobot

### Messages are split awkwardly

- The bot automatically splits at paragraph breaks when possible
- This is expected behavior for very long responses

### Bot crashes or stops

- Check terminal output for error details
- Restart with `python bot.py`
- Consider running with a process manager for production (see below)

## 🌐 Production Deployment (Optional)

For 24/7 operation, consider:

### Option 1: Use a process manager

```bash
# Install pm2
npm install -g pm2

# Run bot with pm2
pm2 start "python bot.py" --name news-bot

# View logs
pm2 logs news-bot

# Restart
pm2 restart news-bot
```

### Option 2: Use systemd (Linux)

Create a service file at `/etc/systemd/system/news-bot.service`:

```ini
[Unit]
Description=News Research Telegram Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/news-research-agent
ExecStart=/path/to/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable news-bot
sudo systemctl start news-bot
sudo systemctl status news-bot
```

### Option 3: Use Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

Build and run:

```bash
docker build -t news-bot .
docker run -d --env-file .env --name news-bot-container news-bot
```

## 📊 Bot Features

✅ Automatic intent classification (news/research/overview)  
✅ Smart article ranking by importance  
✅ Multiple output formats (table/list/prose)  
✅ Long message handling (auto-split)  
✅ User access control  
✅ Typing indicators while processing  
✅ Error handling and logging  
✅ Command help system  
✅ Works with multiple concurrent users  

## 📚 Additional Resources

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

**Need Help?** Check the bot logs or review the main files:

- `bot.py` - Telegram bot implementation
- `agent.py` - News & Research agent logic
- `run.py` - CLI runner
