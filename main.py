#!/usr/bin/env python3
"""CLI interface for the Browser Agent."""
import asyncio
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

from agent.browser_agent import create_agent_from_env


def print_banner():
    """Print welcome banner."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║         Browser Automation Agent - MVP                     ║
║         Powered by Semantic Kernel + Azure OpenAI          ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


async def run_agent(goal: str, headless: bool = False, use_mcp: bool = False):
    """Run the browser agent with a given goal.

    Args:
        goal: The task to accomplish
        headless: Whether to run in headless mode
        use_mcp: Whether to use Playwright MCP server
    """
    try:
        # Create agent from environment variables
        agent = await create_agent_from_env(headless=headless, use_mcp=use_mcp)

        # Run the agent
        result = await agent.run(goal)

        print(f"\n[Final Result]:\n{result}\n")

    except ValueError as e:
        print(f"\n[Configuration Error]: {str(e)}")
        print("\nPlease ensure you have:")
        print("1. Copied .env.template to .env")
        print("2. Filled in your Azure OpenAI credentials in .env")
        if use_mcp:
            print("3. Node.js 18+ is installed (required for MCP server)")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Error]: {str(e)}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    # Load environment variables from .env file
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("[Warning]: .env file not found. Using environment variables.")

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Browser Automation Agent - Control a browser using natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic mode
  python main.py "book me flights to seville leaving on tuesday"

  # Enhanced MCP mode (recommended)
  python main.py "search for python tutorials on youtube" --mcp

  # Headless mode
  python main.py "find the top 3 news articles about AI on BBC" --headless

  # MCP + headless
  python main.py "search for hotels in paris" --mcp --headless
        """
    )

    parser.add_argument(
        "goal",
        type=str,
        help="The task you want the agent to accomplish"
    )

    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Use Playwright MCP server (enhanced mode with accessibility tree, screenshots, JS execution)"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window, only for non-MCP mode)"
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=15,
        help="Maximum number of agent iterations (default: 15)"
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    print(f"Task: {args.goal}")
    mode_str = "MCP Enhanced" if args.mcp else ("Headless" if args.headless else "Visible browser")
    print(f"Mode: {mode_str}")
    print(f"Max iterations: {args.max_iterations}\n")

    # Run the agent
    asyncio.run(run_agent(args.goal, args.headless, args.mcp))


if __name__ == "__main__":
    main()
