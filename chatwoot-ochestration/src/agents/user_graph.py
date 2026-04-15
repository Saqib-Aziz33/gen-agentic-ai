"""
User-facing Agent with PostgreSQL Database Access
==================================================
This agent handles application users who want to:
1. Get customer information
2. Retrieve conversation history  
3. Analyze past conversations to fill out forms
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json
from datetime import datetime

from src.agents.state import AgentState
from src.config import config
from src.db.models import Customer, Conversation, Message

llm = ChatOpenAI(model="gpt-4o-mini", api_key=config.OPENAI_API_KEY)

async def get_customer_from_db(contact_id: str, db_session) -> dict:
    """Fetch customer info from PostgreSQL."""
    result = await db_session.execute(
        select(Customer)
        .options(selectinload(Customer.conversations).selectinload(Conversation.messages))
        .where(Customer.chatwoot_contact_id == str(contact_id))
    )
    customer = result.scalars().first()
    if not customer:
        return None
    
    # Build customer data with conversations
    customer_data = {
        "contact_id": customer.chatwoot_contact_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "extracted_data": customer.extracted_data or {},
        "created_at": str(customer.created_at),
        "conversations": []
    }
    
    for conv in customer.conversations:
        conv_data = {
            "conversation_id": conv.chatwoot_conversation_id,
            "status": conv.status,
            "created_at": str(conv.created_at),
            "messages": [
                {
                    "sender": msg.sender_type,
                    "content": msg.content,
                    "time": str(msg.created_at)
                }
                for msg in conv.messages
            ]
        }
        customer_data["conversations"].append(conv_data)
    
    return customer_data

async def run_user_agent(user_id: str, message: str, db_session) -> dict:
    """
    Run the user-facing agent with database context.
    
    The agent receives customer data as context to answer questions.
    """
    # Try to extract contact_id from message
    contact_id = None
    message_lower = message.lower()
    for word in message_lower.split():
        if word.isdigit():
            contact_id = word
            break
    
    # Get customer data if contact_id found
    customer_context = ""
    if contact_id:
        customer_data = await get_customer_from_db(contact_id, db_session)
        if customer_data:
            customer_context = f"""
CUSTOMER DATA (Contact ID: {contact_id}):
- Name: {customer_data['name'] or 'Not provided'}
- Email: {customer_data['email'] or 'Not provided'}
- Phone: {customer_data['phone'] or 'Not provided'}
- Created: {customer_data['created_at']}

CONVERSATION HISTORY:
"""
            for conv in customer_data['conversations']:
                customer_context += f"\n--- Conversation {conv['conversation_id']} ({conv['created_at']}) ---\n"
                for msg in conv['messages'][:20]:  # Limit to last 20 messages per conv
                    customer_context += f"[{msg['sender']}] {msg['content']}\n"
    
    # Create system prompt with customer context
    system_prompt = f"""You are a customer data assistant for application users.

You help users analyze customer data and conversation history to:
1. Get customer information (name, email, phone)
2. Review conversation history
3. Extract specific fields from past conversations for form filling

{customer_context}

If customer data is provided above, use it to answer the user's questions.
If the user asks about a customer not shown above, ask them for the contact_id.
Present information in a clear, organized format.
Be professional and concise."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=message)
    ]
    
    # Simple LLM call (no complex graph needed for this use case)
    response = await llm.ainvoke(messages)
    
    return {
        "response": response.content,
        "customer_context": customer_context if customer_context else None
    }

