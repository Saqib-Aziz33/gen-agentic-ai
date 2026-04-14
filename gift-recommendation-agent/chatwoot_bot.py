"""
Chatwoot Agent Bot Webhook Handler for Gift Recommendation Agent
=================================================================
Integrates the gift recommendation agent with Chatwoot as an agent bot.
Receives webhook events from Chatwoot and sends responses back via the Chatwoot API.

Setup:
1. Create agent bot in Chatwoot: Settings -> Bots -> Add Bot
2. Set the webhook URL to point to this server
3. Copy the bot's access_token from Chatwoot
4. Run this server: python chatwoot_bot.py

Usage:
    python chatwoot_bot.py

Environment Variables:
    CHATWOOT_ACCESS_TOKEN - Your agent bot's access token from Chatwoot
    CHATWOOT_BASE_URL - Your Chatwoot instance URL (default: https://app.chatwoot.com)
    OPENAI_API_KEY - OpenAI API key
    TAVILY_API_KEY - Tavily API key
    PORT - Server port (default: 5000)
"""

# https://www.chatwoot.com/hc/user-guide/articles/1677497472-how-to-use-agent-bots

import os
import json
import logging
from typing import Dict, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from langchain_core.messages import HumanMessage
from agent import run_conversation_turn, REQUIRED_FIELDS

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

CHATWOOT_ACCESS_TOKEN = os.environ.get("CHATWOOT_ACCESS_TOKEN")
if not CHATWOOT_ACCESS_TOKEN:
    raise ValueError("CHATWOOT_ACCESS_TOKEN not found in environment variables")

CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL", "https://app.chatwoot.com")
PORT = int(os.environ.get("PORT", 5000))

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
# In production, use Redis or a database
# ──────────────────────────────────────────────

# Store conversation state per conversation ID
conversation_states: Dict[int, dict] = {}


def get_conversation_state(conversation_id: int) -> dict:
    """Get or initialize conversation state."""
    if conversation_id not in conversation_states:
        conversation_states[conversation_id] = {
            "messages": [],
            "recipient_relationship": None,
            "occasion": None,
            "budget_range": None,
            "recipient_interests": None,
            "recipient_age_group": None,
            "special_requirements": None,
        }
    return conversation_states[conversation_id]


def clear_conversation_state(conversation_id: int):
    """Clear conversation state (for new conversations)."""
    if conversation_id in conversation_states:
        del conversation_states[conversation_id]


# ──────────────────────────────────────────────
# Chatwoot API Helper Functions
# ──────────────────────────────────────────────


async def send_chatwoot_message(
    account_id: int,
    conversation_id: int,
    content: str,
    message_type: str = "outgoing"
) -> dict:
    """
    Send a message to a Chatwoot conversation.

    Args:
        account_id: Chatwoot account ID
        conversation_id: Conversation ID to send message to
        content: Message content (supports markdown)
        message_type: Message type (outgoing, outgoing_bot)

    Returns:
        Response JSON from Chatwoot API
    """
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"

    headers = {
        "api_access_token": CHATWOOT_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    payload = {
        "content": content,
        "message_type": message_type,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


async def update_conversation_status(
    account_id: int,
    conversation_id: int,
    status: str = "open"
) -> dict:
    """
    Update conversation status in Chatwoot.

    Args:
        account_id: Chatwoot account ID
        conversation_id: Conversation ID
        status: Status (open, pending, resolved)

    Returns:
        Response JSON from Chatwoot API
    """
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/conversations/{conversation_id}"

    headers = {
        "api_access_token": CHATWOOT_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    payload = {"status": status}

    async with httpx.AsyncClient() as client:
        response = await client.patch(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


# ──────────────────────────────────────────────
# Message Processing
# ──────────────────────────────────────────────


def split_message(message: str, max_length: int = 10000) -> list[str]:
    """Split long messages for Chatwoot (has higher limit than Telegram)."""
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


async def process_gift_query(
    account_id: int,
    conversation_id: int,
    user_message: str
) -> None:
    """
    Process a gift recommendation query and send response to Chatwoot.

    Args:
        account_id: Chatwoot account ID
        conversation_id: Chatwoot conversation ID
        user_message: User's message content
    """
    try:
        logger.info(f"Processing message for conversation {conversation_id}: {user_message}")

        # Get or create conversation state
        state = get_conversation_state(conversation_id)

        # Run the agent
        result = run_conversation_turn(user_message, state)

        # Check if agent has a follow-up question
        if result.get("current_question") and not result.get("conversation_complete"):
            question = result["current_question"]

            # Format with collected info if available
            info_lines = []
            for field in REQUIRED_FIELDS + ["recipient_age_group", "special_requirements"]:
                value = state.get(field)
                if value:
                    info_lines.append(f"✅ {value}")

            if info_lines:
                response = f"📋 **Collected:**\n" + "\n".join(info_lines) + f"\n\n❓ {question}"
            else:
                response = f"❓ {question}"

            # Send the question back
            await send_chatwoot_message(account_id, conversation_id, response)

        # Check if agent has final recommendations
        elif result.get("final_response"):
            response = result["final_response"]

            # Split if too long
            chunks = split_message(response)
            for i, chunk in enumerate(chunks):
                await send_chatwoot_message(account_id, conversation_id, chunk)

                # Small delay between chunks
                if len(chunks) > 1 and i < len(chunks) - 1:
                    import asyncio
                    await asyncio.sleep(0.5)

            # Send follow-up message
            await send_chatwoot_message(
                account_id,
                conversation_id,
                "💡 **Need different recommendations?**\n\n"
                "Just tell me what to adjust! For example:\n"
                "• Something more unique\n"
                "• Lower budget options\n"
                "• More practical gifts\n"
                "• Experience-based gifts\n\n"
                "Or type 'reset' to start fresh.",
            )

            # Optionally resolve the conversation
            # await update_conversation_status(account_id, conversation_id, "resolved")

            logger.info(f"Recommendations sent for conversation {conversation_id}")

        else:
            # Fallback
            await send_chatwoot_message(
                account_id,
                conversation_id,
                "🤔 Hmm, I need a bit more information. Could you tell me:\n\n"
                "• Who the gift is for\n"
                "• The occasion\n"
                "• Your budget\n"
                "• Their interests/hobbies\n\n"
                "This helps me give you better recommendations!",
            )

    except Exception as e:
        logger.error(f"Error processing message for conversation {conversation_id}: {e}", exc_info=True)

        await send_chatwoot_message(
            account_id,
            conversation_id,
            f"❌ Sorry, something went wrong. Please try again!\n\n_Error: {str(e)}_",
        )


# ──────────────────────────────────────────────
# FastAPI Application
# ──────────────────────────────────────────────

app = FastAPI(title="Gift Recommendation Agent Bot")


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "bot": "Gift Recommendation Agent"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Main webhook handler for Chatwoot agent bot.
    Receives webhook events and processes messages.
    """
    try:
        # Parse webhook payload
        payload = await request.json()
        event = payload.get("event")

        logger.info(f"Received webhook event: {event}")
        logger.info(f"Full payload: {json.dumps(payload, indent=2)}")

        # Only process message_created events
        if event != "message_created":
            logger.info(f"Ignoring event: {event}")
            return JSONResponse(status_code=200, content={"status": "ignored"})

        # Extract message and conversation data
        # Chatwoot payload structure: fields are at ROOT level, not nested under "message"
        conversation = payload.get("conversation", {})
        account = payload.get("account", {})

        # message_type can be: "incoming" (string) or 0 (int) for customer messages
        message_type = payload.get("message_type", "outgoing")
        
        # Normalize message_type to integer for consistent handling
        if isinstance(message_type, str):
            message_type = 0 if message_type == "incoming" else 1
        
        # Sender type is in conversation.meta.sender or in the first message's sender
        meta = conversation.get("meta", {})
        meta_sender = meta.get("sender", {})
        sender_type = meta_sender.get("type", "unknown").lower()
        sender_id = meta_sender.get("id", "unknown")
        
        # Also try root-level sender if meta doesn't have type
        if sender_type == "unknown":
            root_sender = payload.get("sender", {})
            sender_type = root_sender.get("type", "unknown").lower()
            sender_id = root_sender.get("id", "unknown")
        
        # Content is at root level
        message_content = payload.get("content", "").strip()
        
        account_id = account.get("id")
        conversation_id = conversation.get("id")

        logger.info(f"Message type: {message_type}, Sender type: {sender_type}, Sender ID: {sender_id}")
        logger.info(f"Account ID: {account_id}, Conversation ID: {conversation_id}")
        logger.info(f"Message content: {message_content[:100]}...")

        # Skip bot messages (only process customer messages)
        # message_type: 0 = incoming (from contact), 1 = outgoing (from agent/bot)
        # sender_type: "contact" = customer, "agent" = human agent, "agent_bot" = bot
        if message_type != 0 or sender_type != "contact":
            logger.info(f"Skipping non-contact message - type: {message_type}, sender_type: {sender_type}")
            return JSONResponse(status_code=200, content={"status": "skipped"})

        if not message_content:
            logger.info("Empty message received")
            return JSONResponse(status_code=200, content={"status": "empty"})

        if not account_id or not conversation_id:
            logger.error(f"Missing account_id or conversation_id in payload")
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Handle reset command
        if message_content.lower() in ["reset", "/reset", "start over"]:
            clear_conversation_state(conversation_id)
            await send_chatwoot_message(
                account_id,
                conversation_id,
                "🔄 **Conversation reset!**\n\nTell me about the gift you're looking for, and I'll help you find the perfect gift! 🎁",
            )
            return JSONResponse(status_code=200, content={"status": "reset"})

        # Process the message asynchronously
        # Run in background to avoid timeout
        import asyncio
        asyncio.create_task(
            process_gift_query(account_id, conversation_id, message_content)
        )

        # Return immediately
        return JSONResponse(status_code=200, content={"status": "processing"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook handler error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.post("/webhook/sync")
async def webhook_handler_sync(request: Request):
    """
    Synchronous webhook handler (use if you prefer waiting for response).
    Alternative to /webhook endpoint.
    """
    try:
        payload = await request.json()
        event = payload.get("event")

        if event != "message_created":
            return JSONResponse(status_code=200, content={"status": "ignored"})

        # Extract with correct payload structure
        conversation = payload.get("conversation", {})
        account = payload.get("account", {})

        message_type = payload.get("message_type", "outgoing")
        if isinstance(message_type, str):
            message_type = 0 if message_type == "incoming" else 1

        meta = conversation.get("meta", {})
        meta_sender = meta.get("sender", {})
        sender_type = meta_sender.get("type", "unknown").lower()

        if sender_type == "unknown":
            root_sender = payload.get("sender", {})
            sender_type = root_sender.get("type", "unknown").lower()

        message_content = payload.get("content", "").strip()
        if message_type != 0 or sender_type != "contact":
            return JSONResponse(status_code=200, content={"status": "skipped"})
        if not message_content:
            return JSONResponse(status_code=200, content={"status": "empty"})

        account_id = account.get("id")
        conversation_id = conversation.get("id")

        if not account_id or not conversation_id:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Process synchronously (will wait for completion)
        state = get_conversation_state(conversation_id)
        result = run_conversation_turn(message_content, state)

        # Send response
        if result.get("current_question") and not result.get("conversation_complete"):
            response_text = result["current_question"]
        elif result.get("final_response"):
            response_text = result["final_response"]
        else:
            response_text = "Could you provide more details about the gift?"

        await send_chatwoot_message(account_id, conversation_id, response_text)

        return JSONResponse(status_code=200, content={"status": "ok", "response": response_text})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync webhook handler error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────


def main():
    """Start the Chatwoot agent bot server."""
    import uvicorn

    logger.info("🚀 Starting Gift Recommendation Chatwoot Agent Bot...")
    logger.info(f"📡 Webhook URL: http://localhost:{PORT}/webhook")
    logger.info(f"💚 Health check: http://localhost:{PORT}/")
    logger.info("✅ Server is running! Press Ctrl+C to stop.")

    uvicorn.run(
        "chatwoot_bot:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
