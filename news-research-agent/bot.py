"""
Telegram Bot for News & Research Agent
=======================================
Wraps the news research agent in a Telegram bot interface.
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
from agent import run_agent

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
# Set ALLOWED_USER_IDS in .env to restrict access (e.g., "123456789,987654321")
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
# Helper Functions
# ──────────────────────────────────────────────


def is_user_allowed(user_id: int) -> bool:
    """Check if user is allowed to interact with the bot."""
    if ALLOWED_USER_IDS is None:
        return True
    return user_id in ALLOWED_USER_IDS


def split_message(message: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> list[str]:
    """
    Split a long message into chunks that fit within Telegram's message limit.
    Tries to split at paragraph breaks or sentence boundaries when possible.
    """
    if len(message) <= max_length:
        return [message]

    chunks = []
    while len(message) > max_length:
        # Try to split at newline first
        split_point = message.rfind("\n\n", 0, max_length)
        if split_point == -1:
            # Try to split at single newline
            split_point = message.rfind("\n", 0, max_length)
        if split_point == -1:
            # Try to split at sentence boundary
            split_point = message.rfind(". ", 0, max_length)
            if split_point != -1:
                split_point += 2  # Include the period and space
        if split_point == -1:
            # Hard split if no good break point found
            split_point = max_length

        chunks.append(message[:split_point].strip())
        message = message[split_point:].strip()

    # Add remaining message
    if message:
        chunks.append(message)

    return chunks


async def send_long_message(
    update: Update, text: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message, splitting it into multiple parts if necessary."""
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        # Optionally add continuation indicator
        if len(chunks) > 1 and i < len(chunks) - 1:
            chunk += "\n\n_(continued...)_ "
        elif len(chunks) > 1 and i == 0:
            chunk = "_(part 1 of {})_\n\n".format(len(chunks)) + chunk

        await update.message.reply_text(chunk, parse_mode="Markdown", disable_web_page_preview=True)
        # Small delay to avoid rate limiting
        if len(chunks) > 1:
            import asyncio
            await asyncio.sleep(0.5)


# ──────────────────────────────────────────────
# Command Handlers
# ──────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_message = (
        f"👋 Hello {user.first_name}! I'm your **News & Research Assistant**.\n\n"
        "I can help you with:\n"
        "• 📰 **Latest news** on any topic or person\n"
        "• 🔍 **In-depth research** about people, companies, or topics\n"
        "• 🌍 **World overview** of current events\n\n"
        "Just type your query, for example:\n"
        "• _What's happening in the world_\n"
        "• _Recent news about AI_\n"
        "• _Who is Elon Musk_\n"
        "• _Latest tech news in table format_\n\n"
        "Use /help for more commands."
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📖 **Available Commands:**\n\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n"
        "/about - About this bot\n\n"
        "💬 **Just type your query!** Examples:\n\n"
        "• `What's happening in the world` - Get world overview\n"
        "• `Recent news about climate change` - Latest news\n"
        "• `Who is Donald Trump` - Research about a person\n"
        "• `Latest news in table format` - Tabular output\n"
        "• `Tech news as a list` - List format\n\n"
        "📝 **Output Formats:**\n"
        "• Add _table_ or _tabular_ for table format\n"
        "• Add _list_ or _bullets_ for list format\n"
        "• Default is prose (paragraph) format\n\n"
        "⚙️ **Tips:**\n"
        "• Be specific for better results\n"
        "• Include date/time preferences if needed\n"
        "• I'll show typing indicator while processing"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    about_text = (
        "🤖 **News & Research Assistant Bot**\n\n"
        "Powered by:\n"
        "• 🧠 **LangGraph** - Stateful AI agent framework\n"
        "• 🔍 **Tavily Search** - News and research search engine\n"
        "• 💬 **OpenAI GPT-4** - Natural language processing\n\n"
        "This bot classifies your intent, fetches relevant articles,\n"
        "ranks them by importance, and formats the output based on your preferences.\n\n"
        "Built with ❤️ for staying informed."
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
    await update.message.chat.send_action(action="typing")

    try:
        logger.info(f"Processing query from {update.effective_user.first_name}: {user_query}")

        # Run the agent with the user's query
        response = run_agent(user_query, verbose=False)

        # Send the response (splitting if necessary)
        await send_long_message(update, response, context)

        logger.info(f"Response sent to {update.effective_user.first_name}")

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        error_message = (
            f"❌ **Error Processing Request**\n\n"
            f"Sorry, something went wrong while processing your query.\n"
            f"Please try again in a moment.\n\n"
            f"_Technical details: {str(e)}_"
        )
        await update.message.reply_text(error_message, parse_mode="Markdown")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors and send appropriate error messages."""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

    if update and update.message:
        await update.message.reply_text(
            "⚠️ An unexpected error occurred. Please try again later."
        )


# ──────────────────────────────────────────────
# Main Bot Setup
# ──────────────────────────────────────────────


def main():
    """Start the bot and keep it running."""
    logger.info("🚀 Starting News & Research Telegram Bot...")

    # Create the Application (using async builder)
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
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
