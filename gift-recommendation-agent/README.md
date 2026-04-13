# 🎁 Gift Recommendation Agent

An intelligent, conversational gift recommendation agent that uses **human-in-the-loop** interaction to gather requirements through follow-up questions and provide personalized gift suggestions.

## ✨ Features

### 🧠 Smart Conversation Flow
- **Gathers information progressively** - Asks follow-up questions when details are missing
- **Understands context** - Extracts relationship, occasion, budget, and interests from natural language
- **Validates completeness** - Ensures all required info is collected before recommending
- **Multi-turn conversations** - Refines recommendations based on feedback

### 🎯 Personalized Recommendations
- Searches current gift trends via Tavily
- Ranks gifts by uniqueness and thoughtfulness
- Provides specific, actionable suggestions with price estimates
- Considers recipient's interests and special requirements

### 💬 Multiple Interfaces
- **CLI** - Interactive terminal-based conversation
- **Telegram Bot** - Chat with the agent on Telegram
- **Chatwoot** - Integrate as an agent bot in your helpdesk

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install python-telegram-bot langchain langchain-openai langchain-community langgraph python-dotenv
```

Or use the project's requirements.txt:

```bash
pip install -r ../requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here  # For Telegram bot
```

**Get API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Tavily**: https://app.tavily.com/
- **Telegram Bot**: Message @BotFather on Telegram

### 3. Run the Agent

#### CLI Mode

```bash
# Interactive conversation
python run.py

# Single query
python run.py --query "Birthday gift for my wife, $100, loves cooking"

# Run demo
python run.py --demo
```

#### Telegram Bot

```bash
python bot.py
```

Then search for your bot on Telegram and start chatting!

#### Chatwoot Integration

```bash
python chatwoot_bot.py
```

Then configure the webhook URL in your Chatwoot dashboard.

**See `CHATWOOT_SETUP.md` for complete setup instructions.**

## 📖 How It Works

### Conversation Flow

```
User: "Need a birthday gift"
 🤖 Who is this gift for? (e.g., spouse, friend, parent, colleague)

User: "For my spouse"
 🤖 What's your budget range? (e.g., under $50, $50-100, $100-200)

User: "Around $150"
 🤖 What are their hobbies or interests?

User: "They love photography"
 🤖 [Searching and generating recommendations...]

🎁 Here are your personalized gift recommendations:
  1. Professional Camera Lens...
  2. Photography Workshop...
  3. Custom Photo Book...
  ...
```

### Agent Architecture

```
START
  └─► analyze_user_input
        └─► identify_missing_fields
              ├─► (has all info) search_gift_ideas ──► generate_recommendations ──► END
              └─► (missing info) handle_human_input
                    └─► analyze_user_input (loop back with user's answer)
```

### Required Information

The agent collects these fields before making recommendations:

| Field | Example | Why It Matters |
|-------|---------|----------------|
| **recipient_relationship** | spouse, friend, parent | Determines gift intimacy level |
| **occasion** | birthday, wedding, holiday | Influences gift type and formality |
| **budget_range** | $50-100, under $200 | Filters by price appropriateness |
| **recipient_interests** | cooking, gaming, fitness | Ensures gift relevance |

**Optional fields** (enhances recommendations):
- `recipient_age_group` - child, teen, adult, senior
- `special_requirements` - eco-friendly, personalized, experience-based

## 🎮 Usage Examples

### Example 1: Complete in One Message

```
You: Need a birthday gift for my wife, budget $100, she loves cooking

🤖 [Generates recommendations immediately]
```

### Example 2: Progressive Information Gathering

```
You: Looking for a wedding gift

🤖 Who is this gift for? (e.g., friend, colleague, family member)

You: My colleague

🤖 What's your budget range for the gift?

You: Around $75

🤖 What are their hobbies or interests?

You: They're into photography and hiking

🤖 [Generates recommendations]
```

### Example 3: Refining Recommendations

```
[After receiving initial recommendations]

You: Can you suggest something more unique?

🤖 [Generates more creative/unique options]
```

## 🤖 Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start fresh conversation |
| `/help` | Show help and examples |
| `/status` | See collected information |
| `/reset` | Clear and start over |
| `/about` | About this bot |

### Telegram Features
- ✅ **Typing indicator** while processing
- ✅ **Conversation state** per user
- ✅ **Auto-split** long messages
- ✅ **User access control** (optional)
- ✅ **Follow-up questions** with context

### Chatwoot Features
- ✅ **Webhook-based** integration
- ✅ **Async processing** to avoid timeouts
- ✅ **Conversation state** per Chatwoot conversation
- ✅ **Auto-split** long messages
- ✅ **Commands** support (reset, help)
- ✅ **Production-ready** with FastAPI

## 🏗️ Project Structure

```
gift-recommendation-agent/
├── agent.py              # Core LangGraph agent with conversational flow
├── run.py                # CLI app (interactive + single query + demo modes)
├── bot.py                # Telegram bot wrapper
├── chatwoot_bot.py       # Chatwoot webhook handler (FastAPI server)
├── requirements.txt      # Project dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
├── CHATWOOT_SETUP.md     # Chatwoot integration guide
├── QUICK_START.md        # Quick reference guide
├── start_cli.bat         # Windows CLI launcher
├── start_bot.bat         # Windows Telegram bot launcher
└── start_chatwoot.bat    # Windows Chatwoot server launcher
```

## 🔧 Advanced Usage

### Programmatic Usage

```python
from agent import run_agent_conversation
from langchain_core.messages import HumanMessage

# Initial query
messages = [HumanMessage(content="Need a birthday gift for my friend")]
state = {}

result = run_agent_conversation(messages, state)

# If agent asks a question
if result.get("current_question"):
    print(result["current_question"])
    # Get user's answer and continue
    messages.append(HumanMessage(content="Budget is $50"))
    result = run_agent_conversation(messages, state)

# When recommendations are ready
if result.get("final_response"):
    print(result["final_response"])
```

### Customizing the Agent

Edit `agent.py` to:
- **Add more required fields** - Update `REQUIRED_FIELDS` list
- **Change question templates** - Modify `FIELD_QUESTIONS` dict
- **Adjust recommendation style** - Edit the prompt in `generate_recommendations()`
- **Change number of recommendations** - Modify `min_length`/`max_length` in schema

## 🎓 Key Concepts

### Human-in-the-Loop

The agent uses LangGraph's `interrupt()` mechanism to pause execution and wait for user input when information is missing. This creates a natural conversation flow:

1. **Analyze** user input for information
2. **Identify** what's missing
3. **Interrupt** and ask a follow-up question
4. **Loop back** with user's answer
5. **Proceed** when all info is collected

### State Management

- **CLI**: State is maintained in memory during the session
- **Telegram**: Per-user state in memory (use Redis/DB for production)
- **State persists** across multiple messages in the same conversation

### Error Handling

- Graceful fallbacks for API errors
- User-friendly error messages
- Conversation can continue after errors

## 🐛 Troubleshooting

**Agent doesn't ask follow-up questions:**
- Make sure required fields are missing in your first message
- Check that OpenAI and Tavily API keys are set correctly

**Recommendations seem generic:**
- Provide more specific interests/hobbies
- Add special requirements (eco-friendly, personalized, etc.)

**Telegram bot errors:**
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check that you messaged @BotFather and got the token properly

**Import errors:**
- Ensure all dependencies are installed
- Check you're in the correct virtual environment

## 📝 Future Enhancements

- [ ] Save conversation history to database
- [ ] Add gift purchase links
- [ ] Price tracking and alerts
- [ ] Gift list saving/sharing
- [ ] Image-based recommendations
- [ ] Multi-language support
- [ ] Seasonal gift trends
- [ ] Gift wrapping/presentation suggestions

## 📚 Technologies

- **LangGraph** - Stateful agent orchestration
- **LangChain** - LLM abstractions
- **OpenAI GPT-4** - Natural language understanding
- **Tavily Search** - Gift trends research
- **python-telegram-bot** - Telegram integration

## 📄 License

MIT

---

**Happy Gift Giving! 🎁**
