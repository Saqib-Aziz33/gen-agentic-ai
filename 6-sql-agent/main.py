from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from load_database import load_database
from langchain_community.utilities import SQLDatabase

load_dotenv()
load_database()


# 1. Select an LLM
model = init_chat_model("google_genai:gemini-3.1-flash-lite-preview")


# 2. Configure the database
db = SQLDatabase.from_uri("sqlite:///Chinook.db")

print(f"Dialect: {db.dialect}")
print(f"Available tables: {db.get_usable_table_names()}")
print(f'Sample output: {db.run("SELECT * FROM Artist LIMIT 5;")}')


# 3. Add tools for database interactions
from langchain_community.agent_toolkits import SQLDatabaseToolkit

toolkit = SQLDatabaseToolkit(db=db, llm=model)

tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}\n")


# 4. Use create_agent
system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect=db.dialect,
    top_k=5,
)

from langchain.agents import create_agent


agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
)


while True:
    user_input = input("Ask a question about the Chinook database (or enter 0 to stop): ")
    if user_input == "0":
        break

    # 5. Run the agent
    for step in agent.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()