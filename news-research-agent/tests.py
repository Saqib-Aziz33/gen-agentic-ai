"""
Unit Tests for News & Research Agent
=====================================
Tests node logic with mocked LLM/search calls.
Run: pytest tests.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from agent import (
    AgentState,
    classify_intent,
    rank_importance,
    format_output,
    route_by_intent,
    check_for_error,
    build_graph,
)


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

def make_state(**overrides) -> AgentState:
    base: AgentState = {
        "query": "test query",
        "intent": None,
        "entity": None,
        "format_pref": "prose",
        "search_queries": [],
        "raw_results": [],
        "ranked_results": [],
        "research_summary": None,
        "final_response": None,
        "error": None,
        "messages": [],
    }
    base.update(overrides)
    return base


MOCK_RANKED_ARTICLES = [
    {
        "title": "Breaking: Major Summit Begins",
        "url": "https://example.com/1",
        "source": "Reuters",
        "published_date": "2025-01-01",
        "summary": "World leaders gather for climate summit in Geneva.",
        "importance_score": 9,
        "importance_reason": "Affects global climate policy.",
        "category": "Politics",
    },
    {
        "title": "Tech Company Reports Record Earnings",
        "url": "https://example.com/2",
        "source": "Bloomberg",
        "published_date": "2025-01-01",
        "summary": "Major tech firm exceeds expectations in Q4 results.",
        "importance_score": 6,
        "importance_reason": "Significant market impact.",
        "category": "Technology",
    },
]


# ──────────────────────────────────────────────
# ROUTING TESTS
# ──────────────────────────────────────────────

class TestRouting:
    def test_research_intent_routes_to_research_entity(self):
        state = make_state(intent="research")
        assert route_by_intent(state) == "research_entity"

    def test_news_intent_routes_to_fetch_news(self):
        state = make_state(intent="news")
        assert route_by_intent(state) == "fetch_news"

    def test_overview_intent_routes_to_fetch_news(self):
        state = make_state(intent="overview")
        assert route_by_intent(state) == "fetch_news"

    def test_no_results_skips_ranking(self):
        state = make_state(raw_results=[])
        assert check_for_error(state) == "format_output"

    def test_with_results_goes_to_rank(self):
        state = make_state(raw_results=[{"title": "Test", "url": "http://x.com"}])
        assert check_for_error(state) == "rank_importance"

    def test_error_skips_ranking(self):
        state = make_state(raw_results=[{"title": "x"}], error="Search failed")
        assert check_for_error(state) == "format_output"


# ──────────────────────────────────────────────
# FORMAT OUTPUT TESTS
# ──────────────────────────────────────────────

class TestFormatOutput:
    def test_table_format_contains_markdown_table(self):
        state = make_state(
            intent="news",
            format_pref="table",
            ranked_results=MOCK_RANKED_ARTICLES,
        )
        result = format_output(state)
        response = result["final_response"]
        assert "|" in response  # Markdown table syntax
        assert "Breaking: Major Summit Begins" in response
        assert "9/10" in response

    def test_list_format_contains_numbered_items(self):
        state = make_state(
            intent="news",
            format_pref="list",
            ranked_results=MOCK_RANKED_ARTICLES,
        )
        result = format_output(state)
        response = result["final_response"]
        assert "**1." in response
        assert "**2." in response

    def test_research_intent_uses_research_summary(self):
        state = make_state(
            intent="research",
            entity="Elon Musk",
            research_summary="Elon Musk is a tech entrepreneur...",
        )
        result = format_output(state)
        response = result["final_response"]
        assert "Elon Musk is a tech entrepreneur" in response
        assert "Research" in response

    def test_empty_results_returns_fallback_message(self):
        state = make_state(
            intent="news",
            format_pref="prose",
            ranked_results=[],
        )
        result = format_output(state)
        assert result["final_response"] is not None
        assert len(result["final_response"]) > 0

    def test_table_includes_top_story_section(self):
        state = make_state(
            intent="news",
            format_pref="table",
            ranked_results=MOCK_RANKED_ARTICLES,
        )
        result = format_output(state)
        assert "Top Story" in result["final_response"]

    @patch("agent.get_llm")
    def test_prose_format_calls_llm(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Here is the news summary.")
        mock_get_llm.return_value = mock_llm

        state = make_state(
            intent="news",
            format_pref="prose",
            ranked_results=MOCK_RANKED_ARTICLES,
        )
        result = format_output(state)
        assert mock_llm.invoke.called
        assert "Here is the news summary." in result["final_response"]


# ──────────────────────────────────────────────
# INTENT CLASSIFICATION TESTS (mocked)
# ──────────────────────────────────────────────

class TestClassifyIntent:
    @patch("agent.get_llm")
    def test_classify_news_intent(self, mock_get_llm):
        from agent import IntentClassification
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = IntentClassification(
            intent="news",
            entity=None,
            format_pref="list",
            search_queries=["latest news today"],
        )
        mock_get_llm.return_value = mock_llm

        state = make_state(query="Check recent news")
        result = classify_intent(state)
        assert result["intent"] == "news"
        assert result["format_pref"] == "list"

    @patch("agent.get_llm")
    def test_classify_research_intent(self, mock_get_llm):
        from agent import IntentClassification
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = IntentClassification(
            intent="research",
            entity="Donald Trump",
            format_pref="prose",
            search_queries=["Donald Trump biography", "Donald Trump political career"],
        )
        mock_get_llm.return_value = mock_llm

        state = make_state(query="Who is Donald Trump")
        result = classify_intent(state)
        assert result["intent"] == "research"
        assert result["entity"] == "Donald Trump"

    @patch("agent.get_llm")
    def test_classify_table_format(self, mock_get_llm):
        from agent import IntentClassification
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = IntentClassification(
            intent="news",
            entity=None,
            format_pref="table",
            search_queries=["latest news 2025"],
        )
        mock_get_llm.return_value = mock_llm

        state = make_state(query="Show me latest news in table format")
        result = classify_intent(state)
        assert result["format_pref"] == "table"


# ──────────────────────────────────────────────
# RANK IMPORTANCE TESTS (mocked)
# ──────────────────────────────────────────────

class TestRankImportance:
    def test_empty_raw_results_returns_error(self):
        state = make_state(raw_results=[])
        result = rank_importance(state)
        assert result.get("error") is not None

    @patch("agent.get_llm")
    def test_ranking_sorts_by_score_descending(self, mock_get_llm):
        from agent import RankedResults, RankedArticle
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = RankedResults(articles=[
            RankedArticle(title="Low Importance", url="http://a.com", source=None,
                          published_date=None, summary="Minor story.", importance_score=3,
                          importance_reason="Local news.", category="Other"),
            RankedArticle(title="High Importance", url="http://b.com", source=None,
                          published_date=None, summary="Major event.", importance_score=9,
                          importance_reason="Global impact.", category="Politics"),
        ])
        mock_get_llm.return_value = mock_llm

        state = make_state(raw_results=[
            {"title": "A", "url": "http://a.com", "content": "text"},
            {"title": "B", "url": "http://b.com", "content": "text"},
        ])
        result = rank_importance(state)
        ranked = result["ranked_results"]
        assert ranked[0]["importance_score"] > ranked[1]["importance_score"]
        assert ranked[0]["title"] == "High Importance"


# ──────────────────────────────────────────────
# GRAPH STRUCTURE TEST
# ──────────────────────────────────────────────

class TestGraphStructure:
    def test_graph_compiles_without_error(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"classify_intent", "fetch_news", "research_entity", "rank_importance", "format_output"}
        assert expected.issubset(node_names)
