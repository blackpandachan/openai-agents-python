from pydantic import BaseModel
from typing import List

from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings

EVALUATOR_PROMPT = """
You are an expert research evaluator. You review research reports and evaluate how well they answer 
the original query. You provide constructive feedback and suggestions for improvement.

Your task is to:
1. Evaluate if the report fully addresses the original query
2. Check for comprehensiveness, accuracy, and clarity
3. Identify any gaps or areas that need further research
4. Suggest specific improvements
5. Assign a quality score from 1-10 based on how well it answers the original query
6. Ensure the report contains enough information for an effective write up on the topic or query

Be critical but fair in your assessment. Your goal is to help improve the research quality.
"""


class EvaluationResult(BaseModel):
    """Model for the evaluation result."""
    
    score: int
    """Quality score from 1-10, where 10 is excellent."""
    
    feedback: str
    """Detailed feedback on the report quality."""
    
    improvements: List[str]
    """List of specific improvements that could be made."""
    
    additional_queries: List[str]
    """Additional search queries that might improve the research."""


enhanced_evaluator_agent = Agent(
    name="EvaluatorAgent",
    instructions=EVALUATOR_PROMPT,
    tools=[WebSearchTool()],  # Allow evaluator to search for missing information
    model_settings=ModelSettings(tool_choice="auto"),
    output_type=EvaluationResult,
)