from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
import json

from src.agents.state import AgentState
from src.config import config
from langchain_tavily import TavilySearch

llm = ChatOpenAI(model="gpt-4o-mini", api_key=config.OPENAI_API_KEY)

# 1. Research Agent (Search)
search_tool = TavilySearch(max_results=3, tavily_api_key=config.TAVILY_API_KEY)

def research_prompt(state):
    messages = state["messages"]
    return [SystemMessage(content="You are a research agent. Use the search tool to find information related to user queries. Summarize your findings clearly.")] + messages

research_agent = create_react_agent(llm, tools=[search_tool], prompt=research_prompt)

async def research_node(state: AgentState):
    # Pass messages to research agent
    result = await research_agent.ainvoke({"messages": state["messages"]})
    # Wrap agent's final response
    last_message = result["messages"][-1]
    return {"messages": [AIMessage(content=last_message.content, name="ResearchAgent")]}

# 2. Support Agent (Customer Queries & Form filling)
# Tool that returns customer info as JSON for the API layer to save
@tool
def update_customer_form(name: str = None, email: str = None, phone: str = None):
    """Update the specific form for the customer. Call this when you identify their name, email or phone."""
    return json.dumps({
        "action": "update_customer_form",
        "name": name,
        "email": email,
        "phone": phone
    })

def support_prompt(state):
    messages = state["messages"]
    return [SystemMessage(content="""You are a customer support agent.
Your job is to assist the user. If they want to perform research or request recent web information, you should let the supervisor know to route to ResearchAgent.
If you are dealing with a user, politely ask for their name, email, and phone number if not provided, and use the update_customer_form tool to save it.
Be friendly and helpful.""")] + messages

support_agent = create_react_agent(llm, tools=[update_customer_form], prompt=support_prompt)

async def support_node(state: AgentState):
    result = await support_agent.ainvoke({"messages": state["messages"]})
    last_message = result["messages"][-1]
    
    # Extract customer info from tool calls if present
    customer_info = state.get("customer_info", {}) or {}
    
    # Check if there were tool calls that updated customer form
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.get('name') == 'update_customer_form':
                args = tool_call.get('args', {})
                if args.get('name'):
                    customer_info['name'] = args['name']
                if args.get('email'):
                    customer_info['email'] = args['email']
                if args.get('phone'):
                    customer_info['phone'] = args['phone']

    return {"messages": [AIMessage(content=last_message.content, name="SupportAgent")], "customer_info": customer_info}

# 3. Supervisor Node
options = ["ResearchAgent", "SupportAgent", "FINISH"]
system_prompt = (
    "You are a supervisor tasked with managing a conversation between the following workers: "
    "ResearchAgent, SupportAgent. Given the following user request and conversation history, "
    "respond with the worker to act next. Each worker will perform a task and respond with "
    "their results and status. When the response to the user is fully answered, or you need "
    "to ask the user a follow-up question directly, respond with FINISH."
)

from pydantic import BaseModel
class Router(BaseModel):
    next: Literal["ResearchAgent", "SupportAgent", "FINISH"]

supervisor_chain = llm.with_structured_output(Router)

async def supervisor_node(state: AgentState):
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = supervisor_chain.invoke(messages)
    return {"next": response.next}

# 4. Build Graph
workflow = StateGraph(AgentState)
workflow.add_node("ResearchAgent", research_node)
workflow.add_node("SupportAgent", support_node)
workflow.add_node("Supervisor", supervisor_node)

workflow.add_edge("ResearchAgent", "Supervisor")
workflow.add_edge("SupportAgent", "Supervisor")
workflow.add_conditional_edges(
    "Supervisor",
    lambda x: x["next"],
    {
        "ResearchAgent": "ResearchAgent",
        "SupportAgent": "SupportAgent",
        "FINISH": END
    }
)
workflow.add_edge(START, "Supervisor")

# Use MemorySaver for conversation memory (async-compatible)
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

async def run_agent(conversation_id: str, message: str) -> dict:
    config = {"configurable": {"thread_id": conversation_id}}

    # Check if there's any state (to get existing messages)
    # We will just append the new message
    inputs = {"messages": [HumanMessage(content=message)]}

    final_state = await graph.ainvoke(inputs, config=config)

    # The final message sent to user
    last_message = final_state["messages"][-1]
    return {
        "response": last_message.content,
        "customer_info": final_state.get("customer_info", {}),
        "state": final_state
    }
