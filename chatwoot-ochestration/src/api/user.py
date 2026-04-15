from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.agents.user_graph import run_user_agent

router = APIRouter()

@router.post("/api/user/chat")
async def user_chat(user_id: str, message: str, db: AsyncSession = Depends(get_db)):
    """
    Conversational API for application users to interact with customer data.
    
    Users can:
    - Ask about customer information: "Tell me about customer 123"
    - Get conversation history: "Show me conversations for customer 123"
    - Extract form data: "Fill out a form for customer 123, I need name, email, phone"
    
    Args:
        user_id: Application user identifier
        message: User's natural language query
        db: Database session
    """
    try:
        result = await run_user_agent(user_id, message, db)
        return {
            "user_id": user_id,
            "response": result["response"],
            "customer_provided": result["customer_context"] is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
