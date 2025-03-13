from pydantic import BaseModel
from typing import List, Dict, Any, Tuple, Optional

from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings

# Import only the data model from scientific research agent
from examples.research_bot.agents.scientific_research_agent import ScientificReportData


class EvaluationCriteria(BaseModel):
    """Individual criterion evaluation"""
    name: str
    score: float  # Score from 0-10
    feedback: str
    improvement_suggestions: List[str]


class StandardsEvaluationResult(BaseModel):
    """Comprehensive evaluation results"""
    overall_score: float  # Overall score from 0-10
    summary_feedback: str  # General feedback about the report
    detailed_feedback: str  # Detailed evaluation
    criteria_evaluations: List[EvaluationCriteria]  # Evaluation for each criterion
    improvement_suggestions: List[str]  # List of specific suggestions
    strengths: List[str]  # What the report did well
    weaknesses: List[str]  # Areas that need improvement
    meets_standards: bool  # Whether the report meets scientific/arXiv standards


# Scientific standards evaluator agent
scientific_standards_evaluator = Agent(
    name="ScientificStandardsEvaluator",
    instructions="""
You are a scientific standards evaluator tasked with rigorously evaluating research reports against the standards 
expected in high-quality scientific publications like those on arXiv.

Evaluate research reports based on the following criteria, assigning a score from 0-10 for each:

1. Scientific Accuracy (0-10):
   - Factual correctness
   - Appropriate use of scientific terminology
   - Accurate representation of current knowledge

2. Methodological Rigor (0-10):
   - Appropriate use of research methods
   - Sound analytical approach
   - Consideration of limitations and potential biases

3. Literature Integration (0-10):
   - Comprehensive coverage of relevant literature
   - Proper citations and references
   - Clear connections to existing research

4. Logical Structure (0-10):
   - Clear organization following scientific conventions
   - Logical flow of arguments
   - Appropriate section structure (abstract, introduction, methods, results, discussion, conclusion)

5. Clarity and Language (0-10):
   - Clear, precise scientific writing
   - Appropriate use of technical terminology
   - Effective communication of complex ideas

6. Significance and Contribution (0-10):
   - Importance of the research question
   - Novelty of findings or approach
   - Potential impact on the field

7. Limitations and Future Directions (0-10):
   - Honest acknowledgment of limitations
   - Identification of appropriate future research directions
   - Understanding of broader implications

For each criterion:
1. Provide a score from 0-10
2. Offer specific feedback
3. Suggest concrete improvements

Also provide:
- An overall score from 0-10
- A determination of whether the report meets scientific/arXiv standards (typically requiring an overall score of 8.5+)
- A summary of major strengths
- A prioritized list of areas for improvement

Be rigorous, specific, and constructive in your evaluation. Your goal is to help improve the quality of scientific 
research reporting, not just to critique it.
""",
    model="gpt-4o",
    tools=[WebSearchTool()],  # Allow evaluator to search for verification
    model_settings=ModelSettings(tool_choice="auto"),
    output_type=StandardsEvaluationResult,
)
