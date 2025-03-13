"""
Research agents initialization module to make specialized research agents available.
"""

# Re-export our specialized agents
from .scientific_research_agent import (
    scientific_research_agent,
    technical_research_agent,
    humanities_research_agent,
    interdisciplinary_research_agent,
    ScientificReportData
)

from .scientific_standards_evaluator import (
    scientific_standards_evaluator,
    StandardsEvaluationResult
)