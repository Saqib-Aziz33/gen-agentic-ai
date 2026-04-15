import json
import logging
import httpx
import asyncio
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config import config
from src.db.session import get_db, async_session
from src.db.models import Customer, Conversation, Message
from src.agents.graph import run_agent

router = APIRouter()
logger = logging.getLogger(__name__)

async def update_customer_info(customer_id: int, customer_info: dict, db: AsyncSession):
    """Update customer info in PostgreSQL if any fields were extracted."""
    if not customer_info:
        return
    
    customer = await db.get(Customer, customer_id)
    if not customer:
        return
    
    updated = False
    if customer_info.get('name') and not customer.name:
        customer.name = customer_info['name']
        updated = True
    if customer_info.get('email') and not customer.email:
        customer.email = customer_info['email']
        updated = True
    if customer_info.get('phone') and not customer.phone:
        customer.phone = customer_info['phone']
        updated = True
    
    if updated:
        await db.commit()
        await db.refresh(customer)
        logger.info(f"Updated customer {customer_id} info: {customer_info}")

async def send_chatwoot_message(account_id: int, conversation_id: int, content: str):
    """Send a message to a Chatwoot conversation."""
    url = f"{config.CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
    headers = {
        "api_access_token": config.CHATWOOT_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {
        "content": content,
        "message_type": "outgoing",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

async def process_message(account_id: int, conversation_id: int, contact_id: str, message_content: str):
    """Process message and send response to Chatwoot."""
    async with async_session() as db:
        try:
            logger.info(f"[Conversation {conversation_id}] Processing message: {message_content[:100]}")
            
            # 1. Get or create Customer
            logger.info(f"[Conversation {conversation_id}] Getting/creating customer with contact_id: {contact_id}")
            result = await db.execute(select(Customer).where(Customer.chatwoot_contact_id == str(contact_id)))
            customer = result.scalars().first()
            if not customer:
                logger.info(f"[Conversation {conversation_id}] Creating new customer")
                customer = Customer(chatwoot_contact_id=str(contact_id))
                db.add(customer)
                await db.commit()
                await db.refresh(customer)
                logger.info(f"[Conversation {conversation_id}] Customer created with id={customer.id}")
            else:
                logger.info(f"[Conversation {conversation_id}] Found existing customer: id={customer.id}, name={customer.name}")

            # 2. Get or create Conversation
            logger.info(f"[Conversation {conversation_id}] Getting/creating conversation")
            result = await db.execute(select(Conversation).where(Conversation.chatwoot_conversation_id == str(conversation_id)))
            conversation = result.scalars().first()
            if not conversation:
                logger.info(f"[Conversation {conversation_id}] Creating new conversation")
                conversation = Conversation(customer_id=customer.id, chatwoot_conversation_id=str(conversation_id))
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                logger.info(f"[Conversation {conversation_id}] Conversation created with id={conversation.id}")
            else:
                logger.info(f"[Conversation {conversation_id}] Found existing conversation: id={conversation.id}")

            # 3. Store User Message
            logger.info(f"[Conversation {conversation_id}] Storing user message")
            user_msg = Message(conversation_id=conversation.id, sender_type="user", content=message_content)
            db.add(user_msg)
            await db.commit()
            logger.info(f"[Conversation {conversation_id}] User message stored")

            # 4. Run LangGraph Agent
            logger.info(f"[Conversation {conversation_id}] Running LangGraph agent")
            agent_result = await run_agent(str(conversation.id), message_content)
            response_text = agent_result["response"]
            customer_info = agent_result.get("customer_info", {})
            logger.info(f"[Conversation {conversation_id}] Agent response received: {response_text[:100]}")

            # 5. Update customer info in PostgreSQL if any fields were extracted
            if customer_info:
                logger.info(f"[Conversation {conversation_id}] Customer info extracted: {customer_info}")
                await update_customer_info(customer.id, customer_info, db)

            # 6. Store Agent Message
            logger.info(f"[Conversation {conversation_id}] Storing agent response")
            agent_msg = Message(conversation_id=conversation.id, sender_type="agent", content=response_text)
            db.add(agent_msg)
            await db.commit()
            logger.info(f"[Conversation {conversation_id}] Agent message stored")

            # 7. Send Response to Chatwoot
            logger.info(f"[Conversation {conversation_id}] Sending response to Chatwoot")
            await send_chatwoot_message(account_id, conversation_id, response_text)
            logger.info(f"[Conversation {conversation_id}] ✅ Response sent successfully")
        except Exception as e:
            logger.error(f"[Conversation {conversation_id}] ❌ Error processing message: {e}", exc_info=True)
            # Try to send error message to Chatwoot
            try:
                await send_chatwoot_message(account_id, conversation_id, f"❌ Sorry, something went wrong. Please try again!\n\n_Error: {str(e)}_")
                logger.info(f"[Conversation {conversation_id}] Error message sent to Chatwoot")
            except Exception as send_error:
                logger.error(f"[Conversation {conversation_id}] Failed to send error message: {send_error}")

@router.post("/webhook")
async def chatwoot_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Main webhook handler for Chatwoot agent bot."""
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
        conversation = payload.get("conversation", {})
        account = payload.get("account", {})
        message_type = payload.get("message_type", "outgoing")

        # Normalize message_type to integer for consistent handling
        if isinstance(message_type, str):
            message_type = 0 if message_type == "incoming" else 1

        # Get sender info from conversation.meta.sender or root level
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
        if message_type != 0 or sender_type != "contact":
            logger.info(f"Skipping non-contact message - type: {message_type}, sender_type: {sender_type}")
            return JSONResponse(status_code=200, content={"status": "skipped"})

        if not message_content:
            logger.info("Empty message received")
            return JSONResponse(status_code=200, content={"status": "empty"})

        if not account_id or not conversation_id:
            logger.error(f"Missing account_id or conversation_id in payload")
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Process the message asynchronously in background
        asyncio.create_task(process_message(account_id, conversation_id, sender_id, message_content))

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

@router.post("/api/chat")
async def api_chat(contact_id: str, message: str, db: AsyncSession = Depends(get_db)):
    """API Endpoint to chat with the agent without chatwoot."""
    # Similar logic but just returns response instead of webhook send.
    result = await db.execute(select(Customer).where(Customer.chatwoot_contact_id == contact_id))
    customer = result.scalars().first()
    if not customer:
        customer = Customer(chatwoot_contact_id=contact_id)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)

    # Use a dummy conversation ID for api testing
    internal_conv_id = f"api_{customer.id}"
    result = await db.execute(select(Conversation).where(Conversation.chatwoot_conversation_id == internal_conv_id))
    conversation = result.scalars().first()
    if not conversation:
        conversation = Conversation(customer_id=customer.id, chatwoot_conversation_id=internal_conv_id)
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    user_msg = Message(conversation_id=conversation.id, sender_type="user", content=message)
    db.add(user_msg)
    await db.commit()

    agent_result = await run_agent(str(conversation.id), message)
    response_text = agent_result["response"]
    customer_info = agent_result.get("customer_info", {})

    # Update customer info in PostgreSQL if any fields were extracted
    await update_customer_info(customer.id, customer_info, db)

    agent_msg = Message(conversation_id=conversation.id, sender_type="agent", content=response_text)
    db.add(agent_msg)
    await db.commit()

    return {
        "response": response_text,
        "customer_info": customer_info
    }
