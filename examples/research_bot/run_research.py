#!/usr/bin/env python
"""
Run the Enhanced Research Manager with proper imports and API configuration.
This script sets up the environment correctly and uses the responses API.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from rich.console import Console

# Add the project root to Python path to enable imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Agent SDK components
from agents import (
    Agent, 
    Runner, 
    setup_tracing, 
    WebSearchTool,
    set_default_openai_api
)

# Set the API to use the responses API as recommended in the sample code
set_default_openai_api("responses")

# Import local modules using module imports
from examples.research_bot.enhanced_manager import EnhancedResearchManager
from examples.research_bot.printer import Printer

async def run_research(query, search_type="web", max_iterations=2, min_quality_score=8.5):
    """
    Run the research process using the Enhanced Research Manager.
    
    Args:
        query: The research query to investigate
        search_type: Type of search to perform (web, file, or web_and_file)
        max_iterations: Maximum number of refinement iterations
        min_quality_score: Minimum quality score threshold
    """
    # Setup console and printer
    console = Console()
    printer = Printer(console)
    
    # Setup tracing
    setup_tracing(console_log_level="INFO", file_log_level="DEBUG")
    
    # Create the manager
    manager = EnhancedResearchManager(
        printer=printer,
        search_type=search_type,
        max_iterations=max_iterations,
        min_quality_score=min_quality_score
    )
    
    # Run the research
    await manager.run(query)
    
    # Cleanup
    printer.end()

def main():
    """Main entry point for the research script."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it in the .env file.")
        sys.exit(1)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run the Enhanced Research Manager")
    parser.add_argument(
        "--query", "-q", 
        type=str, 
        default="What are the recent advancements in quantum computing?",
        help="Research query to investigate"
    )
    parser.add_argument(
        "--search-type", "-s", 
        type=str, 
        choices=["web", "file", "web_and_file"],
        default="web",
        help="Type of search to perform"
    )
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=2,
        help="Maximum number of refinement iterations"
    )
    parser.add_argument(
        "--quality-threshold", "-t",
        type=float,
        default=8.5,
        help="Minimum quality score threshold"
    )
    
    args = parser.parse_args()
    
    # Run the research
    asyncio.run(run_research(
        query=args.query,
        search_type=args.search_type,
        max_iterations=args.iterations,
        min_quality_score=args.quality_threshold
    ))

if __name__ == "__main__":
    main()
