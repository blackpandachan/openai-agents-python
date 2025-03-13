import asyncio
import argparse
import os
from typing import List, Optional

from rich.console import Console

from agents import trace
from examples.research_bot.enhanced_manager import EnhancedResearchManager
from examples.research_bot.printer import Printer


async def main() -> None:
    """Main entry point for the enhanced research bot."""
    
    parser = argparse.ArgumentParser(description="Enhanced Research Bot")
    parser.add_argument("--query", "-q", type=str, required=True, help="Research query to investigate")
    parser.add_argument("--search-type", type=str, default="web", choices=["web", "file", "web_and_file"],
                        help="Type of search to perform")
    parser.add_argument("--max-iterations", type=int, default=2, help="Maximum number of refinement iterations")
    parser.add_argument("--min-quality-score", type=float, default=8.5, help="Minimum quality score threshold")
    
    args = parser.parse_args()
    
    # If no query provided via arguments, prompt the user
    query = args.query
    
    # Setup printer
    console = Console()
    printer = Printer(console)
    
    # Create the research manager
    manager = EnhancedResearchManager(
        printer=printer,
        search_type=args.search_type,
        max_iterations=args.max_iterations,
        min_quality_score=args.min_quality_score
    )
    
    # Run the research with proper tracing
    with trace(f"Research Bot: {query}"):
        try:
            # Run the research
            await manager.run(query)
        except Exception as e:
            print(f"Error during research: {e}")
            # Ensure we save even if there was an error
            printer.research_query = query
            printer.force_save_to_markdown()
    
    # Force save whatever research data we have to a markdown file
    printer.research_query = query
    printer.force_save_to_markdown()
    
    # Cleanup
    printer.end()


if __name__ == "__main__":
    asyncio.run(main())