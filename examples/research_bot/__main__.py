"""
Main entry point for running the research bot package as a module.
This allows running the script with `python -m examples.research_bot`
"""

import asyncio
from examples.research_bot.main import main

# Run the main function when the module is executed
if __name__ == "__main__":
    asyncio.run(main())
