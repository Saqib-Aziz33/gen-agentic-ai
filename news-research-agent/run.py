"""
CLI & Example Runner for News/Research Agent
=============================================
Run: python run.py
Or:  python run.py --query "Who is Sam Altman"
"""

import argparse
import os
import sys
from agent import run_agent

# ── Example queries matching all 5 requirement scenarios ──
EXAMPLE_QUERIES = [
    ("News Ranking",      "Check recent news and let me know which is most important"),
    ("Table Format",      "Check latest news and return in table format"),
    ("World Overview",    "What's happening in the world"),
    ("Person News",       "What is happening with Donald Trump"),
    ("Person Research",   "Who is Donald Trump"),
]


def check_env():
    """Validate required API keys are set."""
    missing = []
    for key in ["OPENAI_API_KEY", "TAVILY_API_KEY"]:
        if not os.environ.get(key):
            missing.append(key)
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nSet them with:")
        for key in missing:
            print(f"  export {key}=your_key_here")
        sys.exit(1)


def interactive_mode():
    """REPL-style interactive agent session."""
    print("\n🗞️  News & Research Agent")
    print("=" * 50)
    print("Type your query or 'demo' to run all examples.")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            query = input("Query> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() == "exit":
            break
        if query.lower() == "demo":
            run_demo()
            continue

        response = run_agent(query)
        print("\n" + response + "\n")


def run_demo():
    """Run all 5 example queries and print results."""
    print("\n🎬 Running Demo — All 5 Requirement Scenarios\n")
    for label, query in EXAMPLE_QUERIES:
        print(f"\n{'─'*60}")
        print(f"📌 Scenario: {label}")
        print(f"💬 Query: {query}")
        print('─'*60)
        response = run_agent(query, verbose=True)
        print(response)
        print()
        input("Press Enter for next scenario...")


def main():
    parser = argparse.ArgumentParser(description="News & Research LangGraph Agent")
    parser.add_argument("--query", "-q", type=str, help="Single query to run")
    parser.add_argument("--demo", "-d", action="store_true", help="Run all demo queries")
    parser.add_argument("--no-verbose", action="store_true", help="Suppress node logs")
    args = parser.parse_args()

    check_env()

    if args.demo:
        run_demo()
    elif args.query:
        response = run_agent(args.query, verbose=not args.no_verbose)
        print(response)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
