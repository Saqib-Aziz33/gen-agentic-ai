"""
Telegram Bot for Gift Recommendation Agent
============================================
Wraps the gift recommendation agent in a Telegram bot interface.
Supports conversation flow with follow-up questions.
Run: python bot.py
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction
from langchain_core.messages import HumanMessage, AIMessage
from agent import run_conversation_turn, REQUIRED_FIELDS

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

# Telegram Bot Token (required)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN not found in environment variables.\n"
        "Get one from @BotFather on Telegram and add it to your .env file."
    )

# Optional: Restrict bot to specific user IDs (comma-separated)
ALLOWED_USER_IDS = os.environ.get("ALLOWED_USER_IDS", "")
if ALLOWED_USER_IDS:
    ALLOWED_USER_IDS = [int(uid.strip()) for uid in ALLOWED_USER_IDS.split(",")]
else:
    ALLOWED_USER_IDS = None  # None means allow all users

# Max message length Telegram allows (4096 chars)
MAX_TELEGRAM_MESSAGE_LENGTH = 4096

# ──────────────────────────────────────────────
# Logging Setup
# ──────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Conversation State Management (In-Memory)
# ──────────────────────────────────────────────

# Store conversation state per user (in production, use Redis/DB)
user_conversations = {}


def get_user_conversation(user_id: int) -> dict:
    """Get or initialize user's conversation state."""
    if user_id not in user_conversations:
        user_conversations[user_id] = {
            "messages": [],
            "state": {
                "recipient_relationship": None,
                "occasion": None,
                "budget_range": None,
                "recipient_interests": None,
                "recipient_age_group": None,
                "special_requirements": None,
            }
        }
    return user_conversations[user_id]


def clear_user_conversation(user_id: int):
    """Clear user's conversation state (for /start or /reset)."""
    if user_id in user_conversations:
        del user_conversations[user_id]


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def is_user_allowed(user_id: int) -> bool:
    """Check if user is allowed to interact with the bot."""
    if ALLOWED_USER_IDS is None:
        return True
    return user_id in ALLOWED_USER_IDS


def split_message(message: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> list[str]:
    """Split a long message into chunks that fit within Telegram's message limit."""
    if len(message) <= max_length:
        return [message]

    chunks = []
    while len(message) > max_length:
        split_point = message.rfind("\n\n", 0, max_length)
        if split_point == -1:
            split_point = message.rfind("\n", 0, max_length)
        if split_point == -1:
            split_point = message.rfind(". ", 0, max_length)
            if split_point != -1:
                split_point += 2
        if split_point == -1:
            split_point = max_length

        chunks.append(message[:split_point].strip())
        message = message[split_point:].strip()

    if message:
        chunks.append(message)

    return chunks


async def send_long_message(update: Update, text: str) -> None:
    """Send a message, splitting it into multiple parts if necessary."""
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1 and i < len(chunks) - 1:
            chunk += "\n\n_(continued...)_ "
        elif len(chunks) > 1 and i == 0:
            chunk = "_(part 1 of {})_\n\n".format(len(chunks)) + chunk

        await update.message.reply_text(chunk, parse_mode="Markdown", disable_web_page_preview=True)


def format_collected_info(state: dict) -> str:
    """Format collected information for display."""
    display_names = {
        "recipient_relationship": "👤 For",
        "occasion": "🎉 Occasion",
        "budget_range": "💰 Budget",
        "recipient_interests": "❤️ Interests",
        "recipient_age_group": "🎂 Age group",
        "special_requirements": "✨ Special"
    }

    info_lines = []
    for field in REQUIRED_FIELDS + ["recipient_age_group", "special_requirements"]:
        value = state.get(field)
        if value:
            icon = display_names.get(field, "•")
            info_lines.append(f"{icon} {value}")

    return "\n".join(info_lines) if info_lines else ""


# ──────────────────────────────────────────────
# Command Handlers
# ──────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user_id = update.effective_user.id
    clear_user_conversation(user_id)

    welcome_message = (
        f"🎁 **Welcome, {update.effective_user.first_name}!**\n\n"
        "I'm your **Gift Recommendation Assistant**!\n\n"
        "I'll help you find the perfect gift by asking a few questions:\n\n"
        "• 👤 **Who** the gift is for\n"
        "• 🎉 **What** occasion\n"
        "• 💰 **Budget** range\n"
        "• ❤️ **Interests** of the recipient\n\n"
        "Just tell me about the gift you're looking for!\n\n"
        "_Example: \"Need a birthday gift for my wife, around $100, she loves cooking\"_\n\n"
        "Use /help for more commands."
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📖 **Available Commands:**\n\n"
        "/start - Start over with a fresh conversation\n"
        "/help - Show this help message\n"
        "/status - See what info I've collected so far\n"
        "/reset - Clear all collected info and start over\n"
        "/about - About this bot\n\n"
        "💬 **Just describe what you need!**\n\n"
        "I'll ask follow-up questions if I need more details.\n\n"
        "**Examples:**\n"
        "• _Need a birthday gift for my mom_\n"
        "• _Wedding gift for a colleague_\n"
        "• _Christmas present for my teenage son_\n"
        "• _Housewarming gift, budget $75_"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show collected information."""
    user_id = update.effective_user.id
    conv = get_user_conversation(user_id)
    state = conv["state"]

    info = format_collected_info(state)

    if not info:
        status_text = "📋 **No information collected yet.**\n\nTell me about the gift you're looking for!"
    else:
        status_text = f"📋 **Collected Information:**\n\n{info}\n\n"

        missing = [f for f in REQUIRED_FIELDS if not state.get(f)]
        if missing:
            status_text += f"⚠️ Still need: {', '.join(missing[:2])}"
        else:
            status_text += "✅ I have all the info needed! Send any message to get recommendations."

    await update.message.reply_text(status_text, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset command."""
    user_id = update.effective_user.id
    clear_user_conversation(user_id)

    await update.message.reply_text(
        "🔄 **Conversation reset!**\n\nTell me about the gift you're looking for, and I'll help you find the perfect gift! 🎁",
        parse_mode="Markdown"
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    about_text = (
        "🎁 **Gift Recommendation Bot**\n\n"
        "An intelligent gift finder that:\n\n"
        "• 🧠 **Understands** your needs through conversation\n"
        "• ❓ **Asks** follow-up questions when details are missing\n"
        "• 🔍 **Searches** for current gift trends\n"
        "• 💡 **Recommends** personalized gift ideas\n\n"
        "Powered by:\n"
        "• 🤖 **LangGraph** - Stateful AI agent framework\n"
        "• 🔍 **Tavily Search** - Gift trends research\n"
        "• 💬 **OpenAI GPT-4** - Natural language understanding\n\n"
        "Built with ❤️ for thoughtful gifting"
    )
    await update.message.reply_text(about_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages and process them through the agent."""
    # Check if user is allowed
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Sorry, you don't have permission to use this bot."
        )
        return

    user_query = update.message.text.strip()

    if not user_query:
        return

    # Show typing indicator
    await update.message.chat.send_action(action=ChatAction.TYPING)

    # Get user's conversation state
    user_id = update.effective_user.id
    conv = get_user_conversation(user_id)
    messages = conv["messages"]
    state = conv["state"]

    try:
        logger.info(f"Processing query from {update.effective_user.first_name}: {user_query}")

        # Run the agent with user's message
        result = run_conversation_turn(user_query, state)

        # Update the stored state with any new values
        for field in REQUIRED_FIELDS + ["recipient_age_group", "special_requirements"]:
            if result.get(field):
                state[field] = result[field]

        # Check what the agent returned
        if result.get("current_question") and not result.get("conversation_complete"):
            # Agent needs more information - ask follow-up question
            question = result["current_question"]

            # Show typing indicator before sending question
            await update.message.chat.send_action(action=ChatAction.TYPING)

            # Show progress
            collected_count = sum(1 for f in REQUIRED_FIELDS if state.get(f))
            progress = f"\n\n📊 Progress: {collected_count}/{len(REQUIRED_FIELDS)} details collected"
            
            response = f"❓ {question}{progress}"

            await update.message.reply_text(response, parse_mode="Markdown")

        elif result.get("final_response"):
            # Agent has recommendations - send them
            # Show typing indicator before sending recommendations
            await update.message.chat.send_action(action=ChatAction.TYPING)

            await send_long_message(update, result["final_response"])

            # Send a follow-up message
            await update.message.reply_text(
                "💡 **Need different recommendations?**\n\n"
                "Just tell me what to adjust! For example:\n"
                "• _Something more unique_\n"
                "• _Lower budget options_\n"
                "• _More practical gifts_\n"
                "• _Experience-based gifts_\n\n"
                "Or start fresh with /reset",
                parse_mode="Markdown"
            )

            logger.info(f"Recommendations sent to {update.effective_user.first_name}")

        else:
            # Fallback response
            await update.message.reply_text(
                "🤔 Hmm, I'm processing your request. Could you provide a bit more detail about:\n\n"
                "• Who the gift is for\n"
                "• The occasion\n"
                "• Your budget\n"
                "• Their interests\n\n"
                "This helps me give you better recommendations!"
            )

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)

        error_message = (
            f"❌ **Error Processing Request**\n\n"
            f"Sorry, something went wrong. Please try again!\n\n"
            f"_Technical details: {str(e)}_"
        )
        await update.message.reply_text(error_message, parse_mode="Markdown")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors and send appropriate error messages."""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

    if update and update.message:
        await update.message.reply_text(
            "⚠️ An unexpected error occurred. Please try again later.\n"
            "Use /reset to start fresh."
        )


# ──────────────────────────────────────────────
# Main Bot Setup
# ──────────────────────────────────────────────


def main():
    """Start the bot and keep it running."""
    logger.info("🚀 Starting Gift Recommendation Telegram Bot...")

    # Create the Application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("about", about_command))

    # Register message handler for all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("✅ Bot is running! Press Ctrl+C to stop.")
    logger.info("📱 Open Telegram and search for your bot's username to start chatting!")

    # Run the bot until interrupted
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
