import asyncio
import argparse
import os
from typing import List, Optional

from examples.research_bot.enhanced_manager import EnhancedResearchManager


async def main() -> None:
    """Main entry point for the enhanced research bot."""
    
    parser = argparse.ArgumentParser(description="Enhanced Research Bot")
    parser.add_argument("--query", "-q", type=str, help="Research query")
    parser.add_argument("--files", "-f", nargs="*", help="Optional files to include in research")
    
    args = parser.parse_args()
    
    # If no query provided via arguments, prompt the user
    query = args.query
    if not query:
        query = input("What would you like to research? ")
    
    # Handle file paths
    file_paths: Optional[List[str]] = None
    if args.files:
        file_paths = [f for f in args.files if os.path.exists(f)]
        if not file_paths:
            print("Warning: None of the specified files were found.")
    
    # Run the research manager
    await EnhancedResearchManager().run(query, file_paths)


if __name__ == "__main__":
    asyncio.run(main())