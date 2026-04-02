from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
import os

load_dotenv()
chat_model = init_chat_model(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model=chat_model,
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)