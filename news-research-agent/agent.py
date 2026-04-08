"""
News & Research Agent — LangGraph Implementation
=================================================
A stateful agent that classifies user intent, fetches news/research,
ranks results, and formats output based on user preferences.
"""

from __future__ import annotations

import json
import os
from typing import Annotated, Any, Literal, Optional
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ──────────────────────────────────────────────
# 1. STATE DEFINITION
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    """Central state passed between all graph nodes."""
    # Input
    query: str

    # Classified intent fields
    intent: Optional[Literal["news", "research", "overview"]]
    entity: Optional[str]           # e.g. "Donald Trump", "Tesla"
    format_pref: Optional[Literal["table", "list", "prose"]]
    search_queries: list[str]       # Derived search queries

    # Data pipeline
    raw_results: list[dict]         # Raw Tavily results
    ranked_results: list[dict]      # After importance ranking
    research_summary: Optional[str] # For research intent

    # Output
    final_response: Optional[str]
    error: Optional[str]

    # LangGraph message history (optional, for debugging)
    messages: Annotated[list, add_messages]


# ──────────────────────────────────────────────
# 2. PYDANTIC SCHEMAS FOR STRUCTURED LLM OUTPUT
# ──────────────────────────────────────────────

class IntentClassification(BaseModel):
    """Structured output from the intent classifier node."""
    intent: Literal["news", "research", "overview"] = Field(
        description=(
            "news = user wants recent articles about a topic/person. "
            "research = user wants background, biography, or deep info. "
            "overview = broad world/current events summary."
        )
    )
    entity: Optional[str] = Field(
        default=None,
        description="Named entity the user is asking about (person, company, topic). Null if general."
    )
    format_pref: Literal["table", "list", "prose"] = Field(
        default="prose",
        description="Desired output format. 'table' if user says table/tabular, 'list' if they say list/bullet, else 'prose'."
    )
    search_queries: list[str] = Field(
        description="1-3 optimized Tavily search queries to satisfy this request.",
        min_length=1,
        max_length=3
    )


class RankedArticle(BaseModel):
    """A single ranked news article."""
    title: str
    url: str
    source: Optional[str]
    published_date: Optional[str]
    summary: str = Field(description="2-3 sentence summary of the article.")
    importance_score: int = Field(description="1-10, where 10 is globally critical.", ge=1, le=10)
    importance_reason: str = Field(description="One sentence explaining why this score.")
    category: str = Field(description="Category: Politics, Technology, Economy, Health, Science, Sports, Other")


class RankedResults(BaseModel):
    """Structured output from the ranking node."""
    articles: list[RankedArticle]


# ──────────────────────────────────────────────
# 3. LLM & TOOL INITIALIZATION
# ──────────────────────────────────────────────

def get_llm(structured_output_schema=None):
    """Return a Claude instance, optionally with structured output."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=os.environ["OPENAI_API_KEY"],
    )
    if structured_output_schema:
        return llm.with_structured_output(structured_output_schema)
    return llm


def get_search_tool(max_results: int = 8) -> TavilySearchResults:
    """Return a Tavily search tool configured for news."""
    return TavilySearchResults(
        max_results=max_results,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
        include_images=False,
        api_key=os.environ["TAVILY_API_KEY"],
    )


# ──────────────────────────────────────────────
# 4. NODE IMPLEMENTATIONS
# ──────────────────────────────────────────────

def classify_intent(state: AgentState) -> dict:
    """
    NODE: classify_intent
    Analyzes user query to extract intent, entity, format preference,
    and generates optimized search queries.
    """
    print(f"\n[classify_intent] Query: {state['query']}")

    llm = get_llm(structured_output_schema=IntentClassification)

    today = datetime.now().strftime("%B %d, %Y")
    system = f"""You are an intent classifier for a news and research agent.
Today's date: {today}

Classify the user query into:
- intent: news | research | overview
- entity: named entity if applicable
- format_pref: table | list | prose
- search_queries: 1-3 Tavily-optimized queries

Rules:
- "Who is X" → research intent (biography/background)
- "What is happening with X" → news intent with entity
- "What's happening in the world" → overview intent
- "recent news" / "latest news" → news intent
- Table/format requests → set format_pref accordingly
- For news: add "news today" or current date context to queries
- For research: generate broader background queries
"""
    result: IntentClassification = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=state["query"])
    ])

    print(f"[classify_intent] Intent={result.intent}, Entity={result.entity}, Format={result.format_pref}")
    print(f"[classify_intent] Queries: {result.search_queries}")

    return {
        "intent": result.intent,
        "entity": result.entity,
        "format_pref": result.format_pref,
        "search_queries": result.search_queries,
        "raw_results": [],
        "ranked_results": [],
        "research_summary": None,
        "error": None,
    }


def fetch_news(state: AgentState) -> dict:
    """
    NODE: fetch_news
    Executes search queries via Tavily and aggregates raw results.
    Deduplicates by URL.
    """
    print(f"\n[fetch_news] Running {len(state['search_queries'])} queries...")

    search_tool = get_search_tool(max_results=6)
    seen_urls: set[str] = set()
    all_results: list[dict] = []

    for query in state["search_queries"]:
        try:
            results = search_tool.invoke({"query": query})
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
        except Exception as e:
            print(f"[fetch_news] Search error for '{query}': {e}")

    print(f"[fetch_news] Fetched {len(all_results)} unique articles")
    return {"raw_results": all_results}


def rank_importance(state: AgentState) -> dict:
    """
    NODE: rank_importance
    Uses LLM to score and rank articles by global importance.
    Returns top N articles sorted by score.
    """
    print(f"\n[rank_importance] Ranking {len(state['raw_results'])} articles...")

    if not state["raw_results"]:
        return {"ranked_results": [], "error": "No articles found to rank."}

    llm = get_llm(structured_output_schema=RankedResults)

    # Prepare compact article list for LLM
    articles_text = "\n\n".join([
        f"[{i+1}] Title: {r.get('title', 'N/A')}\n"
        f"    URL: {r.get('url', '')}\n"
        f"    Content: {str(r.get('content', ''))[:400]}"
        for i, r in enumerate(state["raw_results"])
    ])

    entity_context = f" Focus especially on content related to: {state['entity']}." if state.get("entity") else ""

    system = """You are a senior news editor ranking articles by global importance.
Evaluate each article and provide:
- A 2-3 sentence summary
- Importance score 1-10 (10 = crisis/major global event)
- Brief reason for the score
- Category classification"""

    prompt = f"""Rank these articles by importance.{entity_context}

Articles:
{articles_text}

Return all {len(state['raw_results'])} articles ranked."""

    try:
        result: RankedResults = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=prompt)
        ])
        ranked = sorted(result.articles, key=lambda x: x.importance_score, reverse=True)
        ranked_dicts = [a.model_dump() for a in ranked]
        print(f"[rank_importance] Top article: {ranked_dicts[0]['title'][:60]}... (score={ranked_dicts[0]['importance_score']})")
        return {"ranked_results": ranked_dicts}
    except Exception as e:
        print(f"[rank_importance] Error: {e}")
        # Fallback: return raw results as-is
        return {"ranked_results": [
            {"title": r.get("title", ""), "url": r.get("url", ""),
             "summary": str(r.get("content", ""))[:200], "importance_score": 5,
             "category": "Other", "importance_reason": "N/A", "source": "", "published_date": ""}
            for r in state["raw_results"]
        ]}


def research_entity(state: AgentState) -> dict:
    """
    NODE: research_entity
    For research intent: fetches broad results and synthesizes
    a comprehensive summary about the entity.
    """
    print(f"\n[research_entity] Researching: {state.get('entity', 'topic')}")

    # First fetch results
    fetch_result = fetch_news(state)
    raw_results = fetch_result["raw_results"]

    if not raw_results:
        return {
            "raw_results": [],
            "ranked_results": [],
            "research_summary": f"No information found for '{state.get('entity')}'."
        }

    llm = get_llm()

    content_blocks = "\n\n".join([
        f"SOURCE: {r.get('url', '')}\n{str(r.get('content', ''))[:500]}"
        for r in raw_results[:8]
    ])

    entity = state.get("entity", "the topic")
    system = """You are a research analyst. Synthesize information from multiple sources
into a comprehensive, well-structured overview. Include:
- Who/What they are (background)
- Key facts and history  
- Recent developments
- Notable controversies or achievements
- Current status/relevance

Be factual, balanced, and cite specific details."""

    prompt = f"""Research query: "{state['query']}"
Entity: {entity}

Sources:
{content_blocks}

Write a comprehensive research summary about {entity}."""

    try:
        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=prompt)
        ])
        summary = response.content
    except Exception as e:
        summary = f"Research synthesis failed: {e}"

    print(f"[research_entity] Summary length: {len(summary)} chars")
    return {
        "raw_results": raw_results,
        "ranked_results": [],
        "research_summary": summary
    }


def format_output(state: AgentState) -> dict:
    """
    NODE: format_output
    Generates the final response string based on intent + format_pref.
    Handles: table, list, prose for both news and research intents.
    """
    print(f"\n[format_output] Intent={state['intent']}, Format={state['format_pref']}")

    intent = state["intent"]
    format_pref = state["format_pref"]
    today = datetime.now().strftime("%B %d, %Y")

    # ── RESEARCH INTENT ──
    if intent == "research":
        response = f"## Research: {state.get('entity', 'Topic')}\n\n"
        response += f"*As of {today}*\n\n"
        response += state.get("research_summary", "No research data available.")
        return {"final_response": response}

    # ── NEWS / OVERVIEW INTENT ──
    ranked = state.get("ranked_results", [])
    if not ranked:
        return {"final_response": f"I couldn't find relevant news for: '{state['query']}'. Please try a more specific query."}

    entity_header = f" — {state['entity']}" if state.get("entity") else ""
    header = f"## {'Latest News' if intent == 'news' else 'World Overview'}{entity_header}\n*{today}*\n\n"

    # ── TABLE FORMAT ──
    if format_pref == "table":
        rows = ["| # | Title | Category | Score | Summary |",
                "|---|-------|----------|-------|---------|"]
        for i, a in enumerate(ranked, 1):
            title_link = f"[{a['title'][:50]}...]({a['url']})" if len(a['title']) > 50 else f"[{a['title']}]({a['url']})"
            summary_short = a['summary'][:80].replace("|", "—") + "..."
            rows.append(f"| {i} | {title_link} | {a.get('category','Other')} | {a['importance_score']}/10 | {summary_short} |")
        response = header + "\n".join(rows)

        # Add top story detail below table
        top = ranked[0]
        response += f"\n\n### 🔥 Top Story\n**{top['title']}**\n\n{top['summary']}\n\n*Importance: {top['importance_score']}/10 — {top['importance_reason']}*"

    # ── LIST FORMAT ──
    elif format_pref == "list":
        items = []
        for i, a in enumerate(ranked[:8], 1):
            score_bar = "🟥" * (a['importance_score'] // 3) + "🟧" * ((a['importance_score'] % 3) > 0)
            items.append(
                f"**{i}. [{a['title']}]({a['url']})**\n"
                f"   📁 {a.get('category','Other')} | ⚡ Importance: {a['importance_score']}/10 {score_bar}\n"
                f"   {a['summary']}\n"
                f"   *{a['importance_reason']}*"
            )
        response = header + "\n\n".join(items)

    # ── PROSE FORMAT (default) ──
    else:
        llm = get_llm()
        top_articles = ranked[:6]
        articles_json = json.dumps(top_articles, indent=2)

        if intent == "overview":
            style_instruction = "Write a cohesive world news briefing covering major themes. Group by category where natural."
        elif state.get("entity"):
            style_instruction = f"Write a focused news update about {state['entity']}. Highlight the most significant developments."
        else:
            style_instruction = "Write a clear news summary highlighting the most important story and supporting context."

        system = f"You are a professional news anchor writing for an informed audience. {style_instruction} Be concise, factual, and engaging. Use markdown formatting."
        prompt = f"User query: '{state['query']}'\n\nTop articles (ranked by importance):\n{articles_json}\n\nWrite the response now."

        try:
            llm_response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
            response = header + llm_response.content
        except Exception as e:
            # Fallback to simple list if prose generation fails
            response = header + "\n\n".join([
                f"**{a['title']}** ({a['importance_score']}/10)\n{a['summary']}"
                for a in ranked[:5]
            ])

    return {"final_response": response}


# ──────────────────────────────────────────────
# 5. ROUTING FUNCTIONS
# ──────────────────────────────────────────────

def route_by_intent(state: AgentState) -> Literal["fetch_news", "research_entity"]:
    """Router: after classification, decide which data fetching path to take."""
    if state["intent"] == "research":
        return "research_entity"
    return "fetch_news"


def check_for_error(state: AgentState) -> Literal["rank_importance", "format_output"]:
    """Router: skip ranking if we have an error or no results."""
    if state.get("error") or not state.get("raw_results"):
        return "format_output"
    return "rank_importance"


# ──────────────────────────────────────────────
# 6. GRAPH CONSTRUCTION
# ──────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Constructs and compiles the LangGraph state machine.

    Flow:
        START
          └─► classify_intent
                ├─► (research) research_entity ──────────► format_output ──► END
                └─► (news/overview) fetch_news
                      ├─► (has results) rank_importance ──► format_output ──► END
                      └─► (no results) format_output ──────────────────────► END
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("fetch_news", fetch_news)
    graph.add_node("research_entity", research_entity)
    graph.add_node("rank_importance", rank_importance)
    graph.add_node("format_output", format_output)

    # Edges
    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges("classify_intent", route_by_intent)
    graph.add_conditional_edges("fetch_news", check_for_error)
    graph.add_edge("rank_importance", "format_output")
    graph.add_edge("research_entity", "format_output")
    graph.add_edge("format_output", END)

    return graph.compile()


# ──────────────────────────────────────────────
# 7. PUBLIC API
# ──────────────────────────────────────────────

def run_agent(query: str, verbose: bool = True) -> str:
    """
    Main entry point. Takes a natural language query and returns
    a formatted markdown response string.

    Args:
        query: Natural language news/research query
        verbose: Print node execution logs

    Returns:
        Formatted markdown string response
    """
    agent = build_graph()

    initial_state: AgentState = {
        "query": query,
        "intent": None,
        "entity": None,
        "format_pref": None,
        "search_queries": [],
        "raw_results": [],
        "ranked_results": [],
        "research_summary": None,
        "final_response": None,
        "error": None,
        "messages": [],
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"AGENT QUERY: {query}")
        print('='*60)

    result = agent.invoke(initial_state)

    response = result.get("final_response") or result.get("error") or "No response generated."

    if verbose:
        print(f"\n{'='*60}")
        print("FINAL RESPONSE:")
        print('='*60)

    return response


if __name__ == "__main__":
    # Generate and save the agent graph visualization
    agent = build_graph()
    import os
    graph_image_path = os.path.join(os.path.dirname(__file__), "agent_graph.png")
    graph_png = agent.get_graph().draw_mermaid_png()
    with open(graph_image_path, "wb") as f:
        f.write(graph_png)
    print(f"\n📊 Agent graph saved to: {graph_image_path}")