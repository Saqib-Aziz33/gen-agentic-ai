from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from src.db.session import get_db
from src.db.models import Customer, Conversation, Message, User
from src.core.auth import get_current_user

router = APIRouter()

@router.get("/api/customers", response_model=List[dict])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all customers in the system"""
    result = await db.execute(select(Customer))
    return [
        {
            "id": c.id,
            "chatwoot_contact_id": c.chatwoot_contact_id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "created_at": c.created_at
        } for c in result.scalars().all()
    ]

@router.get("/api/customers/{contact_id}")
async def get_customer_info(
    contact_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all information about X customer"""
    result = await db.execute(select(Customer).where(Customer.chatwoot_contact_id == contact_id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    return {
        "id": customer.id,
        "chatwoot_contact_id": customer.chatwoot_contact_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "extracted_data": customer.extracted_data,
        "created_at": customer.created_at
    }

@router.get("/api/customers/{contact_id}/conversations")
async def get_customer_conversations(
    contact_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all conversations and messages for a specific customer"""
    result = await db.execute(
        select(Customer)
        .options(selectinload(Customer.conversations).selectinload(Conversation.messages))
        .where(Customer.chatwoot_contact_id == contact_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    conversations = []
    for conv in customer.conversations:
        messages = [{"sender": msg.sender_type, "content": msg.content, "time": msg.created_at} for msg in conv.messages]
        conversations.append({
            "conversation_id": conv.chatwoot_conversation_id,
            "status": conv.status,
            "created_at": conv.created_at,
            "messages": messages
        })
        
    return {"conversations": conversations}
