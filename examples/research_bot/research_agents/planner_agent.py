from pydantic import BaseModel
from typing import List

from agents import Agent

ENHANCED_PLANNER_PROMPT = """
You are a strategic and highly performant research assistant and planner. Your job is to analyze a 
research query and develop a comprehensive search plan that will yield the most relevant
and complete information. Given a query, come up with a set of web searches to perform to best answer the query.
Output between 5 and 20 terms to query for.

When planning searches:
1. Break down complex queries into specific sub-topics
2. Consider different perspectives and angles on the topic
3. Include both broad and specific search terms
4. Prioritize searches that will yield the most valuable information
5. Output between 5 and 20 terms to query for.

Your goal is to create a search plan that will lead to a comprehensive, well-rounded research report.
"""


class WebSearchItem(BaseModel):
    reason: str
    """Your reasoning for why this search is important to the query."""

    query: str
    """The search term to use for the web search."""


class WebSearchPlan(BaseModel):
    searches: List[WebSearchItem]
    """A list of web searches to perform to best answer the query."""
    
    priority_searches: List[int]
    """Indices of the most important searches that should be performed first."""
    
    areas_covered: List[str]
    """List of topic areas that these searches will cover."""


enhanced_planner_agent = Agent(
    name="PlannerAgent",
    instructions=ENHANCED_PLANNER_PROMPT,
    model="gpt-4o",
    output_type=WebSearchPlan
)