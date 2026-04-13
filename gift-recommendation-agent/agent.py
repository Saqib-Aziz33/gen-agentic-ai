"""
Gift Recommendation Agent — LangGraph Implementation
======================================================
A human-in-the-loop agent that gathers requirements through conversation,
asks follow-up questions when information is missing, and provides
personalized gift recommendations.
"""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal, Optional
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ──────────────────────────────────────────────
# 1. STATE DEFINITION
# ──────────────────────────────────────────────

class GiftState(TypedDict):
    """State for the gift recommendation agent."""
    # User input
    messages: Annotated[list, add_messages]

    # Required fields for gift recommendation
    recipient_relationship: Optional[str]  # e.g., spouse, friend, parent, colleague
    occasion: Optional[str]                # e.g., birthday, anniversary, wedding
    budget_range: Optional[str]            # e.g., $50-100, under $200
    recipient_interests: Optional[str]     # e.g., cooking, gaming, fitness

    # Optional fields that enhance recommendations
    recipient_age_group: Optional[Literal["child", "teen", "adult", "senior"]]
    recipient_gender: Optional[str]
    special_requirements: Optional[str]    # e.g., eco-friendly, handmade, tech

    # Conversation state
    missing_fields: list[str]              # Fields still needed
    current_question: Optional[str]        # What we're asking about
    conversation_complete: bool            # Whether we have enough info

    # Output
    recommendations: Optional[list[dict]]  # Final gift suggestions
    final_response: Optional[str]          # Formatted response to user


# ──────────────────────────────────────────────
# 2. PYDANTIC SCHEMAS FOR STRUCTURED OUTPUT
# ──────────────────────────────────────────────

class GiftRequirements(BaseModel):
    """Extract gift recommendation requirements from user message."""
    recipient_relationship: Optional[str] = Field(
        default=None,
        description="Relationship to recipient: spouse, husband, wife, partner, friend, mom, dad, mother, father, parent, brother, sister, sibling, colleague, boss, coworker, son, daughter, nephew, niece, uncle, aunt, grandparent, grandchild, cousin, neighbor, teacher, student, or any other family member or friend"
    )
    occasion: Optional[str] = Field(
        default=None,
        description="Gift occasion: birthday, anniversary, wedding, holiday, graduation, housewarming, Valentine's Day, Mother's Day, Father's Day, Christmas, baby shower, retirement, get well, thank you, or other special occasion"
    )
    budget_range: Optional[str] = Field(
        default=None,
        description="Budget range: under $25, $25-50, $50-100, $100-200, $200-500, over $500, no limit"
    )
    recipient_interests: Optional[str] = Field(
        default=None,
        description="Recipient's hobbies/interests: cooking, gaming, fitness, reading, music, travel, tech, art, fashion, gardening, sports, outdoors, photography, writing, dancing, singing, cycling, hiking, swimming, yoga, meditation, crafts, woodworking, DIY, or any other hobby or interest"
    )
    recipient_age_group: Optional[Literal["child", "teen", "adult", "senior"]] = Field(
        default=None,
        description="Age group if mentioned: child (0-12), teen (13-19), adult (20-64), senior (65+)"
    )
    special_requirements: Optional[str] = Field(
        default=None,
        description="Special requirements: eco-friendly, handmade, personalized, luxury, practical, experience-based, sustainable, organic, local, vintage, custom-made"
    )


class MissingFieldsAnalysis(BaseModel):
    """Analyze what information is missing."""
    missing_fields: list[str] = Field(
        description="List of missing required fields"
    )
    priority_field: str = Field(
        description="The most important field to ask next"
    )
    follow_up_question: str = Field(
        description="Natural language question to ask the user"
    )
    can_proceed: bool = Field(
        description="Whether we have enough info to make recommendations"
    )


class GiftRecommendation(BaseModel):
    """A single gift recommendation."""
    gift_name: str = Field(description="Name of the gift item")
    category: str = Field(description="Category: Tech, Home, Fashion, Experience, Personalized, Hobby, Food & Drink, Wellness")
    price_estimate: str = Field(description="Estimated price range")
    description: str = Field(description="Why this is a great gift for this recipient")
    why_it_fits: str = Field(description="How it matches the recipient's interests/needs")
    purchase_link_hint: str = Field(description="Where to find it (general, not specific URL)")
    uniqueness_score: int = Field(description="1-10 how unique/thoughtful this gift is", ge=1, le=10)


class GiftRecommendations(BaseModel):
    """Complete gift recommendation response."""
    recommendations: list[GiftRecommendation] = Field(
        description="Top 5 gift recommendations",
        min_length=3,
        max_length=7
    )
    summary: str = Field(description="Brief summary explaining the recommendations")


# ──────────────────────────────────────────────
# 3. LLM & TOOL INITIALIZATION
# ──────────────────────────────────────────────

def get_llm(structured_output_schema=None, temperature=0.7):
    """Return an OpenAI instance, optionally with structured output."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        api_key=os.environ["OPENAI_API_KEY"],
    )
    if structured_output_schema:
        return llm.with_structured_output(structured_output_schema)
    return llm


def get_search_tool(max_results: int = 5) -> TavilySearchResults:
    """Return a Tavily search tool for finding gift ideas."""
    return TavilySearchResults(
        max_results=max_results,
        search_depth="advanced",
        include_answer=True,
        api_key=os.environ["TAVILY_API_KEY"],
    )


# ──────────────────────────────────────────────
# 4. HELPER FUNCTIONS
# ──────────────────────────────────────────────

REQUIRED_FIELDS = [
    "recipient_relationship",
    "occasion",
    "budget_range",
    "recipient_interests"
]

FIELD_QUESTIONS = {
    "recipient_relationship": "Who is this gift for? (e.g., spouse, friend, parent, colleague, sibling)",
    "occasion": "What's the occasion? (e.g., birthday, anniversary, wedding, holiday)",
    "budget_range": "What's your budget range? (e.g., under $50, $50-100, $100-200, no limit)",
    "recipient_interests": "What are their hobbies or interests? (e.g., cooking, gaming, fitness, reading)",
    "recipient_age_group": "What's their age group? (child, teen, adult, senior) - optional",
    "special_requirements": "Any special requirements? (e.g., eco-friendly, personalized, experience-based) - optional"
}


def extract_field_value(message_content: str, field_name: str) -> Optional[str]:
    """Try to extract a specific field value from user message."""
    # This is a simple heuristic - the LLM will do the heavy lifting
    message_lower = message_content.lower()

    if field_name == "recipient_relationship":
        relationships = ["spouse", "husband", "wife", "partner", "friend", "mom", "dad", "mother", "father",
                        "parent", "brother", "sister", "sibling", "colleague", "boss", "coworker",
                        "son", "daughter", "grandparent", "grandchild"]
        for rel in relationships:
            if rel in message_lower:
                return rel
    elif field_name == "budget_range":
        import re
        dollar_amounts = re.findall(r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?', message_content)
        if dollar_amounts:
            return dollar_amounts[0]
        if "no limit" in message_lower or "no budget" in message_lower:
            return "no limit"
        if "cheap" in message_lower or "inexpensive" in message_lower:
            return "under $25"
        if "affordable" in message_lower:
            return "$25-50"

    return None


# ──────────────────────────────────────────────
# 5. NODE IMPLEMENTATIONS
# ──────────────────────────────────────────────

def analyze_user_input(state: GiftState) -> dict:
    """
    NODE: analyze_user_input
    Extract gift requirements from user's latest message.
    """
    print(f"\n[analyze_user_input] Processing message...")

    llm = get_llm(structured_output_schema=GiftRequirements, temperature=0.3)

    # Get the latest user message
    latest_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage) or (hasattr(msg, 'type') and msg.type == "human"):
            latest_message = msg.content if hasattr(msg, 'content') else str(msg)
            break

    if not latest_message:
        return {"missing_fields": REQUIRED_FIELDS.copy()}

    try:
        # Build context about what we already know
        already_collected = {}
        for field in REQUIRED_FIELDS:
            if state.get(field):
                already_collected[field] = state[field]
        
        system_prompt = "Extract gift recommendation requirements from the user's message. Only extract fields that are explicitly mentioned or strongly implied."
        if already_collected:
            system_prompt += f"\n\nAlready collected information: {already_collected}"
            system_prompt += "\n\nIf the user mentions a field that's already collected, update it with the new value if it's different. If they confirm or reiterate something already collected, keep the existing value."

        result: GiftRequirements = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=latest_message)
        ])

        updates = {}
        for field in REQUIRED_FIELDS:
            value = getattr(result, field, None)
            if value and not state.get(field):
                updates[field] = value
                print(f"[analyze_user_input] Extracted {field}: {value}")
            elif value and state.get(field) and value.lower() != state.get(field, '').lower():
                # Update if the value is different from what we have
                updates[field] = value
                print(f"[analyze_user_input] Updated {field}: {state.get(field)} -> {value}")

        # Also check optional fields
        for field in ["recipient_age_group", "special_requirements"]:
            value = getattr(result, field, None)
            if value and not state.get(field):
                updates[field] = value
                print(f"[analyze_user_input] Extracted optional {field}: {value}")

        return updates

    except Exception as e:
        print(f"[analyze_user_input] Error: {e}")
        return {}


def identify_missing_fields(state: GiftState) -> dict:
    """
    NODE: identify_missing_fields
    Determine what information is still needed and generate a follow-up question.
    """
    print(f"\n[identify_missing_fields] Checking for missing info...")

    llm = get_llm(structured_output_schema=MissingFieldsAnalysis, temperature=0.3)

    # Build context from what we've collected
    current_info = {
        "recipient_relationship": state.get("recipient_relationship") or "NOT PROVIDED",
        "occasion": state.get("occasion") or "NOT PROVIDED",
        "budget_range": state.get("budget_range") or "NOT PROVIDED",
        "recipient_interests": state.get("recipient_interests") or "NOT PROVIDED",
        "recipient_age_group": state.get("recipient_age_group") or "NOT PROVIDED",
        "special_requirements": state.get("special_requirements") or "NOT PROVIDED"
    }

    # Determine which required fields are actually missing
    missing = [f for f in REQUIRED_FIELDS if not state.get(f)]
    optional_missing = [f for f in ["recipient_age_group", "special_requirements"] if not state.get(f)]

    try:
        result: MissingFieldsAnalysis = llm.invoke([
            SystemMessage(content=f"""You are analyzing what information is missing for gift recommendations.

Required fields for good recommendations: {', '.join(REQUIRED_FIELDS)}
Optional fields (nice to have): recipient_age_group, special_requirements

Current state:
- Relationship: {current_info['recipient_relationship']}
- Occasion: {current_info['occasion']}
- Budget: {current_info['budget_range']}
- Interests: {current_info['recipient_interests']}
- Age group: {current_info['recipient_age_group']}
- Special requirements: {current_info['special_requirements']}

Fields still MISSING: {missing if missing else 'None - all required fields collected'}

Your task:
1. List which required fields are still missing (use exact field names from the required list)
2. Pick the MOST IMPORTANT field to ask next (prioritize: relationship > occasion > budget > interests)
3. Generate a NATURAL, friendly follow-up question that sounds conversational
4. Set can_proceed to True ONLY if all 4 required fields are collected"""),
            HumanMessage(content="Analyze what's missing and generate a follow-up question if needed.")
        ])

        # Validate that missing_fields only contains actual missing fields
        validated_missing = [f for f in result.missing_fields if f in REQUIRED_FIELDS and not state.get(f)]
        
        updates = {
            "missing_fields": validated_missing,
            "current_question": result.follow_up_question,
            "conversation_complete": result.can_proceed and len(validated_missing) == 0
        }

        print(f"[identify_missing_fields] Missing: {validated_missing}")
        print(f"[identify_missing_fields] Can proceed: {updates['conversation_complete']}")
        print(f"[identify_missing_fields] Question: {result.follow_up_question}")

        return updates

    except Exception as e:
        print(f"[identify_missing_fields] Error: {e}")
        # Fallback to simple logic
        return {
            "missing_fields": missing,
            "current_question": FIELD_QUESTIONS.get(missing[0], "Can you tell me more?") if missing else "",
            "conversation_complete": len(missing) == 0
        }


def handle_human_input(state: GiftState) -> dict:
    """
    NODE: handle_human_input
    Returns the follow-up question to ask the user.
    The actual waiting for user input happens in the CLI/Telegram handlers.
    """
    print(f"\n[handle_human_input] Checking if we need to ask user...")

    if state.get("conversation_complete"):
        print(f"[handle_human_input] Have all info, proceeding to recommendations")
        return {"current_question": None, "conversation_complete": True}

    missing = state.get("missing_fields", [])
    if not missing:
        return {"conversation_complete": True, "current_question": None}

    # Return the follow-up question for the caller to ask the user
    question = state.get("current_question", FIELD_QUESTIONS.get(missing[0], "Tell me more"))

    print(f"[handle_human_input] Asking: {question}")

    # Return state with question - execution will continue after user responds
    return {"current_question": question}


def search_gift_ideas(state: GiftState) -> dict:
    """
    NODE: search_gift_ideas
    Search for current gift trends and popular ideas based on collected requirements.
    """
    print(f"\n[search_gift_ideas] Searching for gift ideas...")

    try:
        search_tool = get_search_tool(max_results=5)

        # Build search query from collected info
        interests = state.get("recipient_interests", "popular gifts")
        occasion = state.get("occasion", "gift")
        budget = state.get("budget_range", "")

        search_query = f"best {occasion} gifts for {interests} {budget} 2024 2025"

        print(f"[search_gift_ideas] Searching: {search_query}")
        results = search_tool.invoke({"query": search_query})

        if results:
            print(f"[search_gift_ideas] Found {len(results)} results")
            return {"messages": [AIMessage(content=f"Searched and found {len(results)} gift ideas")]}

    except Exception as e:
        print(f"[search_gift_ideas] Search error: {e}")

    return {}


def generate_recommendations(state: GiftState) -> dict:
    """
    NODE: generate_recommendations
    Generate personalized gift recommendations based on all collected information.
    """
    print(f"\n[generate_recommendations] Creating recommendations...")

    llm = get_llm(structured_output_schema=GiftRecommendations, temperature=0.8)

    # Build comprehensive context
    context = f"""Generate gift recommendations based on:

- Relationship: {state.get('recipient_relationship', 'not specified')}
- Occasion: {state.get('occasion', 'not specified')}
- Budget: {state.get('budget_range', 'not specified')}
- Interests: {state.get('recipient_interests', 'not specified')}"""

    if state.get("recipient_age_group"):
        context += f"\n- Age group: {state['recipient_age_group']}"
    if state.get("special_requirements"):
        context += f"\n- Special requirements: {state['special_requirements']}"

    try:
        result: GiftRecommendations = llm.invoke([
            SystemMessage(content=f"""You are an expert gift consultant with deep knowledge of trending gifts, unique finds, and what makes gifts truly special.

Generate 5 thoughtful, creative, and practical gift recommendations.
Consider:
- Personalization and thoughtfulness
- Practical utility
- Uniqueness (avoid generic gifts)
- Current trends and popularity
- Value for money

Make recommendations specific and actionable."""),
            HumanMessage(content=context)
        ])

        # Format recommendations
        recommendations = []
        for rec in result.recommendations:
            recommendations.append(rec.model_dump())

        # Format the final response
        response_text = f"## 🎁 Gift Recommendations for Your {state.get('recipient_relationship', 'Special Someone')}\n\n"
        response_text += f"**Occasion:** {state.get('occasion', 'Special Occasion')}\n"
        response_text += f"**Budget:** {state.get('budget_range', 'Flexible')}\n\n"
        response_text += "---\n\n"

        for i, rec in enumerate(recommendations, 1):
            uniqueness = "🌟" * (rec["uniqueness_score"] // 2)
            response_text += f"### {i}. {rec['gift_name']} {uniqueness}\n\n"
            response_text += f"**Category:** {rec['category']}\n"
            response_text += f"**Estimated Price:** {rec['price_estimate']}\n\n"
            response_text += f"{rec['description']}\n\n"
            response_text += f"**Why it's perfect:** {rec['why_it_fits']}\n\n"
            response_text += f"**Where to find:** {rec['purchase_link_hint']}\n\n"
            response_text += "---\n\n"

        response_text += f"### 💡 {result.summary}\n\n"
        response_text += f"*Need more specific recommendations or have questions? Just ask!*"

        return {
            "recommendations": recommendations,
            "final_response": response_text
        }

    except Exception as e:
        print(f"[generate_recommendations] Error: {e}")
        return {
            "final_response": f"Sorry, I encountered an error generating recommendations. Please try again with more details.\n\nError: {e}"
        }


# ──────────────────────────────────────────────
# 6. ROUTING FUNCTIONS
# ──────────────────────────────────────────────

def route_after_analysis(state: GiftState) -> Literal["identify_missing_fields"]:
    """Always check what's missing after analyzing input."""
    return "identify_missing_fields"


def route_after_identification(state: GiftState) -> Literal["search_gift_ideas", "handle_human_input", END]:
    """If we have all info, proceed to recommendations. If missing info, exit to ask user."""
    if state.get("conversation_complete"):
        return "search_gift_ideas"
    # Exit to let CLI/bot ask the user and continue conversation
    return "handle_human_input"


def route_after_human_input(state: GiftState) -> Literal[END]:
    """After setting the question, exit so CLI/bot can ask user."""
    return END


def route_after_search(state: GiftState) -> Literal["generate_recommendations"]:
    """After searching, generate recommendations."""
    return "generate_recommendations"


# ──────────────────────────────────────────────
# 7. GRAPH CONSTRUCTION
# ──────────────────────────────────────────────

def build_graph():
    """
    Constructs and compiles the LangGraph state machine.

    Flow with Human-in-the-Loop:
        START
          └─► analyze_user_input
                └─► identify_missing_fields
                      ├─► (has info) search_gift_ideas ──► generate_recommendations ──► END
                      └─► (missing info) handle_human_input
                            └─► analyze_user_input (loop back)
    """
    graph = StateGraph(GiftState)

    # Register nodes
    graph.add_node("analyze_user_input", analyze_user_input)
    graph.add_node("identify_missing_fields", identify_missing_fields)
    graph.add_node("handle_human_input", handle_human_input)
    graph.add_node("search_gift_ideas", search_gift_ideas)
    graph.add_node("generate_recommendations", generate_recommendations)

    # Edges
    graph.add_edge(START, "analyze_user_input")
    graph.add_conditional_edges("analyze_user_input", route_after_analysis)
    graph.add_conditional_edges("identify_missing_fields", route_after_identification)
    graph.add_conditional_edges("handle_human_input", route_after_human_input)
    graph.add_edge("search_gift_ideas", "generate_recommendations")
    graph.add_edge("generate_recommendations", END)

    return graph.compile()


# ──────────────────────────────────────────────
# 8. PUBLIC API
# ──────────────────────────────────────────────

def run_agent_conversation(messages: list, state: dict = None) -> dict:
    """
    Run the agent with a conversation history.
    Returns either a follow-up question or final recommendations.

    Args:
        messages: List of messages (HumanMessage, AIMessage)
        state: Optional initial state with pre-filled fields

    Returns:
        dict with either current_question (needs more input) or final_response (ready)
    """
    agent = build_graph()

    initial_state: GiftState = {
        "messages": messages,
        "recipient_relationship": state.get("recipient_relationship") if state else None,
        "occasion": state.get("occasion") if state else None,
        "budget_range": state.get("budget_range") if state else None,
        "recipient_interests": state.get("recipient_interests") if state else None,
        "recipient_age_group": state.get("recipient_age_group") if state else None,
        "special_requirements": state.get("special_requirements") if state else None,
        "missing_fields": REQUIRED_FIELDS.copy(),
        "current_question": None,
        "conversation_complete": False,
        "recommendations": None,
        "final_response": None,
    }

    try:
        result = agent.invoke(initial_state)
        return result
    except Exception as e:
        print(f"[run_agent] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"final_response": f"Error: {str(e)}"}


def run_conversation_turn(user_message: str, state: dict) -> dict:
    """
    Run a single conversation turn - analyze user input and either
    return a follow-up question or generate recommendations.
    
    This is the main orchestrator function that handles the conversation loop.

    Args:
        user_message: User's latest message
        state: Current conversation state with collected fields

    Returns:
        Updated state with either current_question or final_response
    """
    # Add user message to state
    messages = state.get("messages", [])
    messages.append(HumanMessage(content=user_message))

    # Run the agent
    result = run_agent_conversation(messages, state)

    # Update state with any extracted fields
    for field in REQUIRED_FIELDS + ["recipient_age_group", "special_requirements"]:
        if result.get(field):
            state[field] = result[field]

    # Update messages
    state["messages"] = messages

    return result


def run_single_query(query: str, state: dict = None) -> dict:
    """
    Run the agent with a single query (simplified mode).

    Args:
        query: User's natural language query
        state: Optional pre-filled state

    Returns:
        dict with final_response or current_question
    """
    messages = [HumanMessage(content=query)]
    return run_agent_conversation(messages, state)


if __name__ == "__main__":
    # Generate and save the agent graph visualization
    agent = build_graph()
    import os
    graph_image_path = os.path.join(os.path.dirname(__file__), "agent_graph.png")
    try:
        graph_png = agent.get_graph().draw_mermaid_png()
        with open(graph_image_path, "wb") as f:
            f.write(graph_png)
        print(f"\n📊 Agent graph saved to: {graph_image_path}")
    except Exception as e:
        print(f"Could not generate graph: {e}")
