from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings

ENHANCED_SEARCH_PROMPT = """
You are a detailed and factual web researcher. Your task is to search the web for specific information 
and provide accurate, concise summaries of what you find.

For each search:
1. Use the exact search term provided
2. Focus on high-quality, reliable sources
3. Extract key facts, data points, and insights
4. Summarize the information in 3-4 detailed paragraphs.
5. Include a mix of general overview and specific details
6. Note any contradictory information from different sources
7. Avoid unnecessary commentary - focus on the facts
8. IMPORTANT: Include inline citations ([1], [2], etc.) for each fact and its source
9. At the end, provide a references section listing all sources used

Format your summary with proper citations like [1], [2], etc. inline in the text,
and include the full URL references at the end of your response.

Your summary should be clear, information-dense, and directly relevant to the search term and reason.
"""

# Create a customized web search tool with high context size for better results
enhanced_web_search_tool = WebSearchTool(
    search_context_size="high"  # Use high context size for comprehensive search results
)

enhanced_search_agent = Agent(
    name="SearchAgent",
    instructions=ENHANCED_SEARCH_PROMPT,
    tools=[enhanced_web_search_tool],
    model_settings=ModelSettings(tool_choice="required"),
)