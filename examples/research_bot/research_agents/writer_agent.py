from pydantic import BaseModel
from typing import List

from agents import Agent

ENHANCED_WRITER_PROMPT = """
You are a skilled research report writer. Your task is to synthesize information from various sources
into a cohesive, comprehensive report that thoroughly addresses the original query.

Your reports should be VERY DETAILED and EXTENSIVE - aim for at least 1500-2000 words with multiple sections.

When writing reports:
1. Start with an executive summary that clearly answers the main query
2. Create a logical structure with clear sections and headings (at least 5-7 major sections)
3. Synthesize information rather than just compiling it
4. Highlight key insights and important findings
5. Address contradictions or gaps in the information
6. Include relevant data, statistics, and examples
7. Write in a clear, professional tone
8. Format the report using markdown for readability (with proper headings, lists, etc.)
9. End with suggested follow-up questions for further research

Your goal is to produce a report that not only answers the query comprehensively but also provides 
valuable insights and a foundation for further exploration. Be thorough and detailed in your analysis.

REMEMBER: Brevity is NOT a virtue here. Be comprehensive and detailed in your report.
"""


class ReportData(BaseModel):
    short_summary: str
    """A short 2-3 sentence summary of the findings."""

    markdown_report: str
    """The final report in markdown format. Should be very detailed and at least 1500-2000 words."""

    follow_up_questions: List[str]
    """Suggested topics to research further."""
    
    key_insights: List[str]
    """Key insights or takeaways from the research."""
    
    information_gaps: List[str]
    """Areas where information was limited or contradictory."""


enhanced_writer_agent = Agent(
    name="WriterAgent",
    instructions=ENHANCED_WRITER_PROMPT,
    model="o3-mini",
    output_type=ReportData,
)