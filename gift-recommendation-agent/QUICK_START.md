# 🚀 Quick Start - Gift Recommendation Agent

## Get Started in 3 Steps

### 1️⃣ Install Dependencies

```bash
pip install langchain langchain-openai langchain-community langgraph python-telegram-bot fastapi uvicorn httpx python-dotenv pydantic
```

**Or** use the requirements file:

```bash
pip install -r requirements.txt
```

### 2️⃣ Set Up Environment Variables

Create a `.env` file in this folder:

```env
OPENAI_API_KEY=your_openai_key_here
TAVILY_API_KEY=your_tavily_key_here

# Optional - for Telegram bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Optional - for Chatwoot integration
CHATWOOT_ACCESS_TOKEN=your_chatwoot_agent_bot_token
CHATWOOT_BASE_URL=https://app.chatwoot.com
```

**Get API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Tavily**: https://app.tavily.com/
- **Telegram Bot Token**: Message @BotFather on Telegram
- **Chatwoot Access Token**: Create Agent Bot in Chatwoot (see CHATWOOT_SETUP.md)

### 3️⃣ Run the Agent

#### Option A: CLI Mode (Terminal)

```bash
# Interactive conversation
python run.py

# Single query
python run.py --query "Birthday gift for wife, $100, loves cooking"

# See demo
python run.py --demo
```

**Or** on Windows, just double-click: `start_cli.bat`

#### Option B: Telegram Bot

```bash
python bot.py
```

**Or** on Windows, just double-click: `start_bot.bat`

Then search for your bot on Telegram and start chatting!

#### Option C: Chatwoot Integration

```bash
python chatwoot_bot.py
```

**Or** on Windows, just double-click: `start_chatwoot.bat`

Then configure the webhook URL in Chatwoot Settings → Bots.

**See `CHATWOOT_SETUP.md` for complete setup instructions.**

---

## 💬 Example Conversations

### Example 1: All Info at Once

```
You: Need a birthday gift for my wife, budget $100, she loves cooking

🤖 [Generates 5-7 personalized recommendations]
```

### Example 2: Progressive Information Gathering

```
You: Looking for a wedding gift

🤖 Who is this gift for? (e.g., friend, colleague, family member)

You: My colleague

🤖 What's your budget range?

You: Around $75

🤖 What are their hobbies or interests?

You: Photography and hiking

🤖 [Generates recommendations]
```

---

## 📋 Telegram Commands

| Command | What it does |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show all features |
| `/status` | See collected info |
| `/reset` | Start fresh |
| `/about` | About this bot |

## 💬 Chatwoot Commands

In Chatwoot chat, customers can use:

| Command | What it does |
|---------|-------------|
| `reset` or `/reset` | Clear conversation |
| Any text | Processed as gift query |

---

## 🎯 What the Agent Collects

Before making recommendations, it gathers:

1. **Who** - Relationship to recipient (spouse, friend, parent, etc.)
2. **Occasion** - Birthday, wedding, holiday, etc.
3. **Budget** - Price range
4. **Interests** - Hobbies and passions

Optional: Age group, special requirements (eco-friendly, personalized, etc.)

---

## 🐛 Troubleshooting

**"Missing environment variables" error:**
- Create `.env` file with your API keys
- See `.env.example` for format

**Agent doesn't ask follow-up questions:**
- Make sure your first message doesn't already include all required info
- Try: "Need a gift" (vague) vs "Gift for wife, $100, cooking" (complete)

**Telegram bot won't start:**
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify you got the token from @BotFather

**Chatwoot bot doesn't respond:**
- Check `CHATWOOT_ACCESS_TOKEN` is correct
- Verify webhook URL is accessible (use ngrok for local testing)
- Check server logs for errors

---

**That's it! Start finding perfect gifts! 🎁**
