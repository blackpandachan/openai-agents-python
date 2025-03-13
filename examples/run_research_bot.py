#!/usr/bin/env python
"""
Script to run the research bot from the correct directory level
to avoid import conflicts between the local agents directory and the installed agents package.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from rich.console import Console

# Set the OpenAI API key directly

# Ensure the installed agents package is used by manipulating the import path
# Get the site-packages directory where agents is installed
import site
site_packages = site.getsitepackages()[0]

# Move site-packages to the beginning of sys.path to prioritize installed packages
if site_packages in sys.path:
    sys.path.remove(site_packages)
sys.path.insert(0, site_packages)

# Now import agents from the installed package
from agents import Agent, Runner, setup_tracing, WebSearchTool, set_default_openai_api, ModelSettings

# Set the API to use the responses API as recommended
set_default_openai_api("responses")

# Now we can import our local modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from research_bot.enhanced_manager import EnhancedResearchManager
from research_bot.printer import Printer

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

async def main():
    """Main entry point for running the research."""
    # Test query
    query = "Tell me about the progression of lunar landing equipment since the 1960s"
    
    print(f"Starting research on: {query}")
    print("-" * 80)
    
    # Run the research
    await run_research(
        query=query,
        search_type="web",
        max_iterations=2
    )
    
    print("-" * 80)
    print("Research completed!")

if __name__ == "__main__":
    asyncio.run(main())
