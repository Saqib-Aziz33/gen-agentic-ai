# 🗞️ News & Research Agent — LangGraph

A stateful AI agent that intelligently handles news fetching, ranking, research, and flexible output formatting using LangGraph + Claude + Tavily.

## Architecture

```
User Query
    │
    ▼
[classify_intent]  ──── extracts: intent, entity, format_pref, search_queries
    │
    ├── research ──► [research_entity] ──► [format_output] ──► Response
    │
    └── news/overview ──► [fetch_news]
                              │
                              ├── has results ──► [rank_importance] ──► [format_output] ──► Response
                              └── no results  ──────────────────────► [format_output] ──► Response
```

### Nodes

| Node | Responsibility |
|------|---------------|
| `classify_intent` | Determines intent (news/research/overview), extracts entity, detects format preference, generates search queries |
| `fetch_news` | Executes Tavily searches, deduplicates by URL |
| `research_entity` | Deep multi-query research + LLM synthesis for "Who is X" queries |
| `rank_importance` | Scores articles 1-10 for global significance, returns sorted list |
| `format_output` | Renders markdown table / bullet list / prose based on format_pref |

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API keys
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export TAVILY_API_KEY=tvly-...
```

Get Tavily key free at: https://tavily.com

### 3. Run

**Interactive mode:**
```bash
python run.py
```

**Single query:**
```bash
python run.py --query "What is happening with AI regulation"
python run.py --query "Who is Sam Altman"
python run.py --query "Latest news in table format"
```

**Demo (all 5 scenarios):**
```bash
python run.py --demo
```

## Usage Examples

### From Python
```python
from agent import run_agent

# News ranking
response = run_agent("Check recent news and tell me which is most important")

# Table format
response = run_agent("Check latest news and return in table format")

# World overview
response = run_agent("What's happening in the world")

# Person news
response = run_agent("What is happening with Donald Trump")

# Research
response = run_agent("Who is Donald Trump")

print(response)
```

## Running Tests
```bash
pip install pytest
pytest tests.py -v
```

## Project Structure

```
news_research_agent/
├── agent.py          # Core LangGraph agent (nodes, graph, state)
├── run.py            # CLI interface & demo runner
├── tests.py          # Unit tests (mocked LLM/search)
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Design Decisions

- **Pydantic structured outputs** — Forces LLM to return typed, validated data at classification and ranking stages, eliminating fragile string parsing.
- **Conditional routing** — Graph branches at two points: intent type and result availability, avoiding wasted LLM calls on empty result sets.
- **Deduplication by URL** — Multiple search queries are merged with a seen-URL set to prevent redundant articles.
- **Format-aware rendering** — Table/list/prose are handled in a single `format_output` node using the classified `format_pref`, keeping formatting logic centralized.
- **Research vs News separation** — Research path skips ranking (not relevant for biographical queries) and instead uses synthesis LLM call.
