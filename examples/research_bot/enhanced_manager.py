from __future__ import annotations

import asyncio
import os
import time
import json
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel
from rich.console import Console

from agents import Runner, custom_span, trace, ItemHelpers, Agent
from examples.research_bot.agents.planner_agent import WebSearchItem, WebSearchPlan, enhanced_planner_agent
from examples.research_bot.agents.search_agent import enhanced_search_agent
from examples.research_bot.agents.writer_agent import enhanced_writer_agent, ReportData
from examples.research_bot.agents.evaluator_agent import enhanced_evaluator_agent, EvaluationResult
from examples.research_bot.agents.file_search_agent import enhanced_file_search_agent
# Import each agent individually to avoid parentheses parsing issues
from examples.research_bot.agents.scientific_research_agent import scientific_research_agent
from examples.research_bot.agents.scientific_research_agent import technical_research_agent
from examples.research_bot.agents.scientific_research_agent import humanities_research_agent
from examples.research_bot.agents.scientific_research_agent import interdisciplinary_research_agent
from examples.research_bot.agents.scientific_research_agent import ScientificReportData
from examples.research_bot.agents.scientific_standards_evaluator import (
    scientific_standards_evaluator,
    StandardsEvaluationResult
)
from examples.research_bot.printer import Printer
import re


# Router agent to determine the type of research needed
research_router_agent = Agent(
    name="research_router_agent",
    instructions="""You are a research router agent.
    Your task is to analyze research queries and determine which specialized research approach would be most appropriate.
    
    Categories to choose from:
    1. Scientific - for queries related to natural sciences, medicine, biology, physics, chemistry, etc.
    2. Technical - for queries related to computing, engineering, technology, programming, etc.
    3. Humanities - for queries related to history, philosophy, literature, arts, social sciences, etc.
    4. Interdisciplinary - for queries that clearly span multiple domains above
    
    Provide your routing decision and a brief explanation of why you chose that category."""
)


async def evaluate_and_refine(
    query: str, 
    current_report: Any,
    research_type: str,
    max_iterations: int = 3,
    min_quality_score: float = 8.5
) -> Tuple[Any, float, str, bool]:
    """
    Evaluate a research report and refine it if needed.
    
    Args:
        query: The original research query
        current_report: The current report (ScientificReportData or ReportData)
        research_type: The type of research ("Scientific", "Technical", etc.)
        max_iterations: Maximum number of refinement iterations
        min_quality_score: Minimum score to consider the report satisfactory
        
    Returns:
        Tuple containing:
        - refined_report: The improved report
        - score: The final quality score
        - evaluation: The evaluation feedback
        - meets_standards: Whether the report meets scientific standards
    """
    
    # Get the appropriate specialized agent based on research type
    specialized_agent = None
    if research_type == "Scientific":
        specialized_agent = scientific_research_agent
    elif research_type == "Technical":
        specialized_agent = technical_research_agent
    elif research_type == "Humanities":
        specialized_agent = humanities_research_agent
    elif research_type == "Interdisciplinary":
        specialized_agent = interdisciplinary_research_agent
    
    # Extract report content
    markdown_report = getattr(current_report, "markdown_report", str(current_report))
    short_summary = getattr(current_report, "short_summary", "")
    
    # Create evaluation input
    eval_input = (
        f"Query: {query}\n\n"
        f"Research Type: {research_type}\n\n"
        f"Report summary: {short_summary}\n\n"
        f"Full report: {markdown_report}\n\n"
        f"Evaluate if this report meets the standards expected in high-quality {research_type.lower()} "
        f"publications like those on arXiv. Provide a detailed evaluation with specific "
        f"suggestions for improvement."
    )
    
    # Run the scientific standards evaluator
    eval_result = await Runner.run(
        scientific_standards_evaluator,
        eval_input,
    )
    
    # Extract evaluation results
    evaluation = eval_result.final_output_as(StandardsEvaluationResult)
    
    # If the report meets standards or no specialized agent is available, return as is
    if evaluation.meets_standards or specialized_agent is None:
        return current_report, evaluation.overall_score, evaluation.detailed_feedback, evaluation.meets_standards
    
    # Otherwise, refine the report
    improve_input = (
        f"Original query: {query}\n\n"
        f"Research Type: {research_type}\n\n"
        f"Please improve this {research_type.lower()} research report based on the following evaluation feedback:\n\n"
        f"EVALUATION FEEDBACK:\n{evaluation.detailed_feedback}\n\n"
        f"Overall Score: {evaluation.overall_score}/10\n\n"
        f"IMPROVEMENT SUGGESTIONS:\n{', '.join(evaluation.improvement_suggestions)}\n\n"
        f"WEAKNESSES TO ADDRESS:\n{', '.join(evaluation.weaknesses)}\n\n"
        f"CURRENT REPORT:\n{markdown_report}\n\n"
        f"Create an improved version that better meets scientific/arXiv standards. "
        f"Focus on addressing the specific issues mentioned in the evaluation."
    )
    
    # Run the specialized research agent to refine the report
    improved_result = await Runner.run(
        specialized_agent,
        improve_input,
    )
    
    # Attempt to extract the improved report
    try:
        # Try to extract as ScientificReportData
        refined_report = improved_result.final_output_as(ScientificReportData)
    except Exception:
        # If parsing fails, create object from text
        improved_text = improved_result.final_output
        if not improved_text:
            improved_text = ItemHelpers.text_message_outputs(improved_result.new_items)
            
        # Keep original fields if possible
        refined_report = ReportData(
            short_summary=short_summary,  # Keep original summary
            markdown_report=improved_text,
            follow_up_questions=getattr(current_report, "follow_up_questions", ["What follow-up research would be valuable?"]),
            key_insights=getattr(current_report, "key_insights", ["Report refined based on evaluation"]),
            information_gaps=getattr(current_report, "information_gaps", ["Additional refinement may be needed"])
        )
    
    return refined_report, evaluation.overall_score, evaluation.detailed_feedback, evaluation.meets_standards


async def iterative_refinement(
    query: str, 
    initial_report: Any,
    research_type: str,
    max_iterations: int = 3,
    min_quality_score: float = 8.5,
    progress_callback=None
) -> Tuple[Any, float, List[Tuple[float, str]]]:
    """
    Iteratively evaluate and refine a research report until it meets quality standards.
    
    Args:
        query: The original research query
        initial_report: The initial report object
        research_type: The type of research
        max_iterations: Maximum number of refinement iterations
        min_quality_score: Minimum score to consider the report satisfactory
        progress_callback: Optional callback function to report progress
        
    Returns:
        Tuple containing:
        - final_report: The final refined report
        - highest_score: The highest score achieved
        - evaluation_history: List of (score, feedback) tuples for each iteration
    """
    current_report = initial_report
    iteration = 0
    highest_score = 0
    best_report = initial_report
    evaluation_history = []
    
    while iteration < max_iterations:
        iteration += 1
        
        if progress_callback:
            progress_callback(f"Refinement iteration {iteration}/{max_iterations}...", False)
        
        # Evaluate and refine the current report
        refined_report, score, feedback, meets_standards = await evaluate_and_refine(
            query,
            current_report,
            research_type,
            max_iterations=1,  # Single refinement per iteration
            min_quality_score=min_quality_score
        )
        
        # Record evaluation
        evaluation_history.append((score, feedback))
        
        # Keep track of the best report so far
        if score > highest_score:
            highest_score = score
            best_report = refined_report
        
        # Update current report for next iteration
        current_report = refined_report
        
        # If the report meets our quality threshold, we're done
        if meets_standards or score >= min_quality_score:
            if progress_callback:
                progress_callback(f"Report meets scientific/arXiv standards with score {score:.1f}/10", True)
            return current_report, score, evaluation_history
        
        if progress_callback:
            progress_callback(f"Current quality score: {score:.1f}/10. Continuing refinement...", False)
    
    # If we've reached max iterations, return the best report we found
    if progress_callback:
        progress_callback(f"Reached maximum iterations. Using best report with score {highest_score:.1f}/10", True)
    
    return best_report, highest_score, evaluation_history


class EnhancedResearchManager:
    """Enhanced research manager using the Agents SDK."""
    
    def __init__(
        self, 
        printer: Printer,
        search_type: str = "web_and_file",
        max_iterations: int = 3,
        min_quality_score: float = 8.5,
        research_router: Agent = research_router_agent
    ):
        """Initialize the enhanced research manager."""
        self.printer = printer
        self.search_type = search_type
        self.max_iterations = max_iterations
        self.min_quality_score = min_quality_score
        self.research_router = research_router
    
    async def run(self, query: str) -> None:
        """
        Run the enhanced research process.
        
        Args:
            query: The user's research query.
        """
        self.query = query
        
        with custom_span("research_process", {"query": query}):
            # Display start message
            self.printer.update_item("context", f"Researching: {query}")
            
            # 1. Determine research type using the router agent
            with custom_span("determine_research_type"):
                research_type = await self._determine_research_type(query)
            
            # 2. Get specialized search plan
            with custom_span("create_search_plan", {"research_type": research_type}):
                search_plan = await self._create_search_plan(query, research_type)
            
            # 3. Execute web searches
            with custom_span("execute_web_searches"):
                web_search_results = await self._execute_web_searches(search_plan)
            
            # 4. Execute file searches if requested
            file_search_results = []
            if self.search_type in ["file", "web_and_file"]:
                with custom_span("execute_file_searches"):
                    file_search_results = await self._execute_file_searches(query)
            
            # Get the appropriate specialized agent based on research type
            specialized_agent = None
            if research_type == "Scientific":
                specialized_agent = scientific_research_agent
            elif research_type == "Technical":
                specialized_agent = technical_research_agent
            elif research_type == "Humanities":
                specialized_agent = humanities_research_agent
            elif research_type == "Interdisciplinary":
                specialized_agent = interdisciplinary_research_agent
            else:
                specialized_agent = enhanced_writer_agent
            
            # 5. Write initial report using specialized agent
            with custom_span("write_specialized_report", {"research_type": research_type}):
                report = await self._write_specialized_report(query, web_search_results, file_search_results, specialized_agent, research_type)
            
            # 6. Iteratively evaluate and refine the report to meet scientific/arXiv standards
            # Use the modularized iterative_refinement function
            self.printer.update_item("refining", "Starting iterative refinement process...", is_done=False)
            
            # Create progress callback function to update the printer
            def progress_callback(message, is_done=False):
                self.printer.update_item("refining", message, is_done=is_done)
            
            # Call the modularized iterative_refinement function
            with custom_span("iterative_refinement", {"max_iterations": self.max_iterations}):
                final_report, highest_score, evaluation_history = await iterative_refinement(
                    query, 
                    report, 
                    research_type,
                    max_iterations=self.max_iterations,
                    min_quality_score=self.min_quality_score,
                    progress_callback=progress_callback
                )
            
            # Store the final report content for saving to markdown
            if hasattr(final_report, 'text') and final_report.text:
                self.printer.research_result = final_report.text
            
            # 7. Display final report
            self._display_final_report(final_report)
            
            # Display completion message
            self.printer.update_item(
                "context",
                f"Research completed: {query} (Score: {highest_score:.1f}/10)",
                is_done=True
            )
            
            return None

    async def _create_search_plan(self, query: str, research_type: str) -> WebSearchPlan:
        """Create a specialized search plan for the query based on research type."""
        with custom_span("Create search plan"):
            self.printer.update_item("planning", f"Creating {research_type.lower()} search plan...")
            
            input_content = (
                f"Original query: {query}\n\n"
                f"Research type: {research_type}\n\n"
                f"Create a specialized search plan for conducting {research_type.lower()} "
                f"research on this topic. Include at least 3-5 targeted web searches."
            )
            
            result = await Runner.run(
                enhanced_planner_agent,
                input_content,
            )
            
            plan = result.final_output_as(WebSearchPlan)
            
            self.printer.update_item(
                "planning",
                f"Created {research_type.lower()} search plan with {len(plan.searches)} searches",
                is_done=True
            )
            
            return plan

    async def _determine_research_type(self, query: str) -> str:
        """Determine the research type using the router agent."""
        with custom_span("Determine research type"):
            self.printer.update_item("routing", "Determining research type...")
            
            try:
                result = await Runner.run(
                    self.research_router,
                    f"Query: {query}\n\nDetermine the most appropriate research category for this query."
                )
                
                routing_decision = result.final_output.strip().lower()
                
                if "scientific" in routing_decision:
                    research_type = "Scientific"
                elif "technical" in routing_decision:
                    research_type = "Technical"
                elif "humanities" in routing_decision:
                    research_type = "Humanities"
                elif "interdisciplinary" in routing_decision:
                    research_type = "Interdisciplinary"
                else:
                    # Default to interdisciplinary if unclear
                    research_type = "Interdisciplinary"
                
                self.printer.update_item(
                    "routing",
                    f"Query routed to {research_type} research specialist",
                    is_done=True,
                )
                
                return research_type
                
            except Exception as e:
                self.printer.update_item(
                    "routing_error",
                    f"Error during routing: {str(e)}. Using interdisciplinary approach.",
                    is_done=True,
                )
                # Default to interdisciplinary if there's an error
                return "Interdisciplinary"

    async def _execute_web_searches(self, search_plan: WebSearchPlan) -> List[Dict[str, Any]]:
        """Execute web searches based on the search plan."""
        with custom_span("Execute web searches"):
            self.printer.update_item("searching", "Executing web searches...")
            
            results = []
            
            async def search(item: WebSearchItem) -> Dict[str, Any]:
                search_item_query = item.query  # Store the query from the WebSearchItem
                search_item_reason = item.reason  # Store the reason from the WebSearchItem
                
                try:
                    input_text = f"Search term: {search_item_query}\nReason for searching: {search_item_reason}"
                    self.printer.update_item("searching", f"Searching for: {search_item_query}")
                    
                    # Run the search with a timeout
                    try:
                        # Adding a timeout to prevent indefinite hanging
                        result = await asyncio.wait_for(
                            Runner.run(
                                enhanced_search_agent,
                                input_text,
                            ),
                            timeout=120  # 2 minute timeout
                        )
                    except asyncio.TimeoutError:
                        print(f"TIMEOUT: Search for '{search_item_query}' timed out after 120 seconds")
                        return {
                            "query": search_item_query,
                            "reason": search_item_reason,
                            "error": "Search timed out after 120 seconds",
                            "success": False
                        }
                    
                    # Debug information
                    self.printer.update_item("searching", f"Got response for: {search_item_query}")
                    
                    # Extract text content from search results
                    summary = ItemHelpers.text_message_outputs(result.new_items)
                    
                    # Debug the structure of result items
                    if not result.new_items:
                        print(f"WARNING: No new items in search result for '{search_item_query}'")
                    
                    # Extract citations from search results - more robust approach
                    citations = []
                    try:
                        for item_idx, message_item in enumerate(result.new_items):
                            # First, try to extract citations from annotations if they exist
                            try:
                                if hasattr(message_item, "type") and message_item.type == "message":
                                    # Handle different content structures
                                    if hasattr(message_item, "content"):
                                        if isinstance(message_item.content, str):
                                            # No annotations in string content
                                            pass
                                        elif isinstance(message_item.content, list):
                                            # Process list of content items
                                            for content_item in message_item.content:
                                                if hasattr(content_item, "text") and hasattr(content_item, "annotations"):
                                                    for annotation in content_item.annotations or []:
                                                        if getattr(annotation, "type", "") == "url_citation":
                                                            url = getattr(annotation, "url", "")
                                                            if url:
                                                                citations.append({
                                                                    "url": url,
                                                                    "title": getattr(annotation, "title", "Web Source"),
                                                                    "start_index": getattr(annotation, "start_index", 0),
                                                                    "end_index": getattr(annotation, "end_index", 0),
                                                                })
                                        elif hasattr(message_item.content, "annotations"):
                                            # Direct annotations on content
                                            for annotation in message_item.content.annotations or []:
                                                if getattr(annotation, "type", "") == "url_citation":
                                                    url = getattr(annotation, "url", "")
                                                    if url:
                                                        citations.append({
                                                            "url": url,
                                                            "title": getattr(annotation, "title", "Web Source"),
                                                            "start_index": getattr(annotation, "start_index", 0),
                                                            "end_index": getattr(annotation, "end_index", 0),
                                                        })
                            except Exception as inner_error:
                                print(f"WARNING: Error processing item {item_idx} annotations: {str(inner_error)}")
                            
                        # If no citations were found via annotations, try to extract them from the text
                        if not citations and summary:
                            # Look for reference patterns like [1]: http://... or References: 1. Title (http://...)
                            import re
                            # Try to find URLs in the summary text
                            urls = re.findall(r'https?://\S+', summary)
                            for i, url in enumerate(urls):
                                # Clean up URL - remove trailing punctuation
                                url = re.sub(r'[.,)]$', '', url)
                                citations.append({
                                    "url": url,
                                    "title": f"Reference {i+1}",
                                    "start_index": 0,
                                    "end_index": 0,
                                })
                    except Exception as extraction_error:
                        print(f"ERROR extracting citations: {str(extraction_error)}")
                        # Continue even if citation extraction fails
                    
                    # Report citation count
                    print(f"Extracted {len(citations)} citations for query '{search_item_query}'")
                    
                    return {
                        "query": search_item_query,
                        "reason": search_item_reason,
                        "summary": summary,
                        "citations": citations,  # Include the extracted citations
                        "success": True
                    }
                except Exception as e:
                    print(f"ERROR in search '{search_item_query}': {str(e)}")
                    return {
                        "query": search_item_query,
                        "reason": search_item_reason,
                        "error": str(e),
                        "success": False
                    }
            
            # Update progress display format
            total_searches = len(search_plan.searches)
            completed = 0
            
            # Process the searches in chunks of 3 to avoid rate limiting
            for i in range(0, len(search_plan.searches), 3):
                try:
                    chunk = search_plan.searches[i:i + 3]
                    # Add timeout to gather operation as well
                    chunk_results = await asyncio.wait_for(
                        asyncio.gather(*[search(item) for item in chunk]),
                        timeout=180  # 3 minutes per chunk
                    )
                    results.extend(chunk_results)
                    
                    # Update progress
                    completed += len(chunk)
                    self.printer.update_item(
                        "searching", 
                        f"Searching... {completed}/{total_searches} completed",
                        is_done=(completed >= total_searches)
                    )
                    
                    # Small delay to avoid rate limiting
                    if i + 3 < len(search_plan.searches):
                        await asyncio.sleep(1)
                except asyncio.TimeoutError:
                    print(f"TIMEOUT: Chunk {i//3 + 1} timed out after 180 seconds")
                    # Add partial failures for the timed-out items
                    for j in range(i, min(i + 3, len(search_plan.searches))):
                        item = search_plan.searches[j]
                        results.append({
                            "query": item.query,
                            "reason": item.reason,
                            "error": "Search chunk timed out",
                            "success": False
                        })
                    # Update progress
                    completed += len(chunk)
                    self.printer.update_item(
                        "searching", 
                        f"Searching... {completed}/{total_searches} completed (with timeouts)",
                        is_done=(completed >= total_searches)
                    )
                except Exception as e:
                    print(f"ERROR processing chunk {i//3 + 1}: {str(e)}")
                    # Continue with the next chunk
            
            # Mark searching as done even if there were errors
            self.printer.mark_item_done("searching")
            
            return results

    async def _execute_file_searches(self, query: str) -> List[Dict[str, Any]]:
        """Search through project files for relevant information."""
        with custom_span("Search files"):
            self.printer.update_item("file_search", "Searching through project files...")
            
            file_results = []
            
            # Get a list of relevant files in the current directory and subdirectories
            try:
                # Start with the current working directory
                base_dir = os.getcwd()
                relevant_files = []
                
                # Build a list of relevant file extensions to search
                relevant_extensions = ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.csv']
                
                # Walk through directories to find relevant files
                for root, _, files in os.walk(base_dir):
                    for file in files:
                        # Check if the file has a relevant extension
                        if any(file.endswith(ext) for ext in relevant_extensions):
                            file_path = os.path.join(root, file)
                            relevant_files.append(file_path)
                
                # Limit to a reasonable number of files
                max_files = 10
                if len(relevant_files) > max_files:
                    self.printer.update_item(
                        "file_search", 
                        f"Found {len(relevant_files)} files, limiting to {max_files} for search efficiency"
                    )
                    relevant_files = relevant_files[:max_files]
                
                # Search through each file
                for file_path in relevant_files:
                    try:
                        # Use the file search agent to get relevant content
                        result = await Runner.run(
                            enhanced_file_search_agent,
                            f"File to search: {file_path}\nQuery: {query}\n\nExtract the most relevant information."
                        )
                        
                        content = ItemHelpers.text_message_outputs(result.new_items)
                        
                        # Only include if we got meaningful content
                        if content and len(content) > 10:
                            file_results.append({
                                "file": file_path,
                                "content": content,
                                "success": True
                            })
                    except Exception as e:
                        self.printer.update_item(
                            "file_search",
                            f"Error searching file {file_path}: {str(e)}"
                        )
            except Exception as e:
                self.printer.update_item(
                    "file_search",
                    f"Error during file search: {str(e)}",
                    is_done=True
                )
            
            self.printer.update_item(
                "file_search",
                f"File search completed, found {len(file_results)} relevant sections",
                is_done=True
            )
            
            return file_results

    async def _write_specialized_report(
        self, 
        query: str, 
        web_search_results: List[Dict[str, Any]], 
        file_search_results: List[Dict[str, Any]],
        specialized_agent: Agent,
        research_type: str
    ) -> ReportData:
        """Write a specialized report based on search results using the appropriate research agent."""
        with custom_span(f"Write {research_type.lower()} report"):
            # Prepare search results for the report
            successful_web_searches = [r for r in web_search_results if r.get("success", False)]
            
            # Format search results as markdown
            search_results_md = "# Search Results\n\n"
            
            # Collect all citations to include in the report
            all_citations = []
            
            # Add web search results with citations - limit number to avoid token limits
            if successful_web_searches:
                # Limit to most relevant searches if we have too many
                max_searches = 5 if "o3-mini" in str(specialized_agent.model) else 8
                if len(successful_web_searches) > max_searches:
                    print(f"Limiting web search results from {len(successful_web_searches)} to {max_searches} to avoid token limits")
                    successful_web_searches = successful_web_searches[:max_searches]
                
                search_results_md += "## Web Search Results\n\n"
                for i, result in enumerate(successful_web_searches):
                    search_results_md += f"### Search {i+1}: {result['query']}\n\n"
                    search_results_md += f"**Reason**: {result['reason']}\n\n"
                    
                    # Limit the size of each summary to avoid token overflow
                    summary_limit = 800 if "o3-mini" in str(specialized_agent.model) else 1500
                    summary = result['summary']
                    if len(summary) > summary_limit:
                        summary = summary[:summary_limit] + "... (truncated for token management)"
                    
                    search_results_md += f"{summary}\n\n"
                    
                    # Add citations information if available
                    if "citations" in result and result["citations"]:
                        search_results_md += "**Sources**:\n\n"
                        for j, citation in enumerate(result["citations"]):
                            source_title = citation.get("title", "Web Source")
                            source_url = citation.get("url", "")
                            search_results_md += f"- [{source_title}]({source_url})\n"
                        search_results_md += "\n"
                        
                        # Collect all citations for later reference
                        all_citations.extend(result["citations"])
            
            # Add file search results - limit number to avoid token limits
            successful_file_searches = [r for r in file_search_results if r.get("success", False)]
            if successful_file_searches:
                # Limit to most relevant file searches if we have too many
                max_files = 3 if "o3-mini" in str(specialized_agent.model) else 6
                if len(successful_file_searches) > max_files:
                    print(f"Limiting file search results from {len(successful_file_searches)} to {max_files} to avoid token limits")
                    successful_file_searches = successful_file_searches[:max_files]
                    
                search_results_md += "## File Search Results\n\n"
                for i, result in enumerate(successful_file_searches):
                    search_results_md += f"### File {i+1}: {result['file']}\n\n"
                    search_results_md += f"**Relevance**: {result['relevance_score']}/10\n\n"
                    search_results_md += "```\n"
                    
                    # Limit content length based on model
                    content_limit = 600 if "o3-mini" in str(specialized_agent.model) else 1500
                    result_content = result['content'][:content_limit]
                    if len(result['content']) > content_limit:
                        result_content += "\n... (content truncated for token management)"
                    
                    search_results_md += result_content
                    search_results_md += "\n```\n\n"
            
            # Create a citation appendix
            if all_citations:
                search_results_md += "\n## References and Citations\n\n"
                unique_citations = {}
                for citation in all_citations:
                    url = citation.get("url", "")
                    if url and url not in unique_citations:
                        title = citation.get("title", "Web Source")
                        unique_citations[url] = title
                
                for i, (url, title) in enumerate(unique_citations.items()):
                    search_results_md += f"[{i+1}] {title}\n{url}\n\n"
            
            # Prepare the prompt for the research agent
            prompt = f"""
Research Query: {query}

Research Type: {research_type}

Based on the following search results, create a comprehensive research report.
Ensure you cite sources where appropriate, especially for factual claims.

{search_results_md}

Your task is to synthesize this information into a cohesive, well-structured report that answers the original query.
Include proper citations and references to the sources provided.
"""
            
            # Calculate token size estimate (rough approximation: 1 token ≈ 4 chars)
            estimated_tokens = len(prompt) / 4
            token_limit_warning = ""
            
            # Add token management warnings if necessary
            if "o3-mini" in str(specialized_agent.model) and estimated_tokens > 6000:
                token_limit_warning = "CAUTION: Input is potentially large. Focus on extracting key information and being concise in your report."
                prompt = f"""
Research Query: {query}

Research Type: {research_type}

{token_limit_warning}

Based on the search results (which may be extensive), create a focused research report.
Prioritize quality over quantity - extract the most important information and insights.
Ensure you cite sources where appropriate, especially for factual claims.

{search_results_md}

Your task is to synthesize this information into a concise, well-structured report that answers the original query.
Include proper citations and references to the sources provided.
"""
            
            # Display writing status
            self.printer.update_item("writing", f"Generating {research_type.lower()} research report...", is_done=False)
            if token_limit_warning:
                self.printer.update_item("token_management", f"Token management active: {estimated_tokens:.0f} estimated tokens", is_done=False)
            
            # Generate the report using the specialized agent
            try:
                # Use a timeout to prevent indefinite hanging
                try:
                    result = await asyncio.wait_for(
                        Runner.run(
                            specialized_agent,
                            prompt,
                        ),
                        timeout=300  # 5 minute timeout
                    )
                except asyncio.TimeoutError:
                    self.printer.update_item(
                        "writing",
                        f"Report generation timed out after 5 minutes. Attempting to continue with partial results.",
                        is_done=False
                    )
                    # Return a timeout error report
                    return {
                        "short_summary": "Error: Report generation timed out",
                        "markdown_report": "# Error: Report Generation Timeout\n\nThe report generation process took too long and timed out. This may be due to the complexity of the query or the amount of information to process.",
                        "follow_up_questions": [],
                        "key_insights": [],
                        "information_gaps": ["Complete information could not be retrieved due to timeout."],
                        "methodological_approach": "Timeout occurred",
                        "citation_count": len(all_citations)
                    }
                
                # Save the raw output to a debug file for investigation
                output_dir = os.path.join(os.path.dirname(__file__), "research_output")
                os.makedirs(output_dir, exist_ok=True)
                
                if result.new_items:
                    # Get the text content first
                    content = ItemHelpers.text_message_outputs(result.new_items)
                    
                    # Save raw output to debug file
                    debug_timestamp = time.strftime("%Y%m%d_%H%M%S")
                    debug_filename = f"raw_agent_output_{debug_timestamp}.txt"
                    debug_path = os.path.join(output_dir, debug_filename)
                    try:
                        with open(debug_path, 'w', encoding='utf-8') as f:
                            f.write(f"Query: {query}\n\n")
                            f.write(f"Research Type: {research_type}\n\n")
                            f.write(f"Model: {specialized_agent.model}\n\n")
                            f.write("Raw output:\n\n")
                            f.write(str(content))
                            
                            # Also write the final_output if available
                            if result.final_output:
                                f.write("\n\nFinal Output:\n\n")
                                import json
                                try:
                                    f.write(json.dumps(result.final_output, indent=2, cls=PydanticJSONEncoder))
                                except Exception as json_err:
                                    f.write(f"Error serializing final_output to JSON: {str(json_err)}\n")
                                    f.write(str(result.final_output))
                    except Exception as debug_error:
                        print(f"Error saving debug output: {str(debug_error)}")
                    
                    # Extract the report data from the agent's output
                    # CRITICAL SECTION: Preserve the original high-quality report
                    if result.final_output:
                        # Handle the final output data more robustly
                        try:
                            # Check if we already have a report-like dictionary structure
                            if isinstance(result.final_output, dict) and ("markdown_report" in result.final_output or "short_summary" in result.final_output):
                                # Use the original report directly to preserve all details
                                report_data = dict(result.final_output)
                                
                                # Ensure we have required fields for proper display but DON'T modify the report content
                                report_data.setdefault("follow_up_questions", [])
                                report_data.setdefault("key_insights", [])
                                report_data.setdefault("information_gaps", [])
                                report_data.setdefault("methodological_approach", "Direct expert analysis")
                                report_data.setdefault("citation_count", len(all_citations))
                                
                                # Ensure the raw output is preserved in the printer
                                if "markdown_report" in report_data:
                                    self.printer.research_result = report_data["markdown_report"]
                                
                                # Normalize reference numbers for consistency
                                report_data = self._normalize_reference_numbers(report_data)
                                
                                self.printer.update_item("writing", "High-quality research report preserved", is_done=True)
                                return report_data
                            else:
                                # If not a report structure, analyze text content for report format
                                report_content = ItemHelpers.text_message_outputs(result.new_items)
                                
                                # Check if it contains a JSON-like structure with report data
                                import re
                                if "markdown_report" in report_content:
                                    report_pattern = r'"markdown_report"\s*:\s*"((?:\\.|[^"\\])*)"'
                                    report_match = re.search(report_pattern, report_content)
                                    
                                    if report_match:
                                        report_text = report_match.group(1)
                                        report_text = report_text.replace("\\n", "\n").replace('\\"', '"')
                                        
                                        # Extract short summary too if available
                                        summary = ""
                                        summary_pattern = r'"short_summary"\s*:\s*"((?:\\.|[^"\\])*)"'
                                        summary_match = re.search(summary_pattern, report_content)
                                        if summary_match:
                                            summary = summary_match.group(1).replace("\\n", "\n").replace('\\"', '"')
                                        else:
                                            # Create a brief summary if none exists
                                            summary = report_text[:150] + "..." if len(report_text) > 150 else report_text
                                            
                                        # Preserve the full report content
                                        self.printer.research_result = report_text
                                        
                                        # Normalize reference numbers for consistency
                                        report_data = {
                                            "short_summary": summary,
                                            "markdown_report": report_text,
                                            "follow_up_questions": [],
                                            "key_insights": [],
                                            "information_gaps": [],
                                            "methodological_approach": "Extracted from agent output",
                                            "citation_count": len(all_citations)
                                        }
                                        report_data = self._normalize_reference_numbers(report_data)
                                        
                                        self.printer.update_item(
                                            "writing",
                                            "Extracted complete report from text content",
                                            is_done=True
                                        )
                                        
                                        return report_data
                                
                                # Look for structured report with header markers
                                if "# " in report_content and "## " in report_content:
                                    # This looks like a well-formatted markdown report
                                    self.printer.research_result = report_content
                                    self.printer.update_item(
                                        "writing",
                                        "Using agent's formatted markdown report directly",
                                        is_done=True
                                    )
                                    # Normalize reference numbers for consistency
                                    report_data = {
                                        "short_summary": report_content[:150] + "..." if len(report_content) > 150 else report_content,
                                        "markdown_report": report_content,
                                        "follow_up_questions": [],
                                        "key_insights": [],
                                        "information_gaps": [],
                                        "methodological_approach": "Direct expert analysis",
                                        "citation_count": len(all_citations)
                                    }
                                    report_data = self._normalize_reference_numbers(report_data)
                                    return report_data
                                
                                # Fall back to using the text content as is
                                self.printer.update_item(
                                    "writing",
                                    "Converting agent output to report format...",
                                    is_done=True
                                )
                                self.printer.research_result = report_content
                                # Normalize reference numbers for consistency
                                report_data = {
                                    "short_summary": report_content[:150] + "..." if len(report_content) > 150 else report_content,
                                    "markdown_report": report_content,
                                    "follow_up_questions": [],
                                    "key_insights": [],
                                    "information_gaps": [],
                                    "methodological_approach": "Direct response",
                                    "citation_count": len(all_citations)
                                }
                                report_data = self._normalize_reference_numbers(report_data)
                                return report_data
                        except Exception as extract_error:
                            # Print detailed error for debugging but continue processing
                            print(f"Error extracting report data: {str(extract_error)}")
                            self.printer.update_item(
                                "writing",
                                f"Error extracting report data: {str(extract_error)}. Using text content directly.",
                                is_done=True
                            )
                            # Fall back to using raw text content without modifications
                            text_content = ItemHelpers.text_message_outputs(result.new_items)
                            self.printer.research_result = text_content
                            # Normalize reference numbers for consistency
                            report_data = {
                                "short_summary": text_content[:150] + "..." if len(text_content) > 150 else text_content,
                                "markdown_report": text_content,
                                "follow_up_questions": [],
                                "key_insights": [],
                                "information_gaps": [],
                                "methodological_approach": "Direct response",
                                "citation_count": len(all_citations)
                            }
                            report_data = self._normalize_reference_numbers(report_data)
                            return report_data
                    
                    # If we reach here, we have no final_output to use - fall back to text output
                    text_content = ItemHelpers.text_message_outputs(result.new_items)
                    if not text_content:
                        self.printer.update_item(
                            "writing",
                            "No report content generated. Please try again.",
                            is_done=True
                        )
                        return {
                            "short_summary": "Error: No content was generated.",
                            "markdown_report": "# Error: No Report Generated\n\nThe research agent did not produce any content. This could be due to a timeout, an error in processing, or limitations in the available data. Please try again with a more specific query or contact support if this issue persists.",
                            "follow_up_questions": [],
                            "key_insights": [],
                            "information_gaps": ["Complete report could not be generated"],
                            "methodological_approach": "Error occurred",
                            "citation_count": 0
                        }
                    
                    # If we have text but it's not formatted, use it directly
                    self.printer.research_result = text_content
                    self.printer.update_item(
                        "writing",
                        "Using unformatted agent output as report",
                        is_done=True
                    )
                    # Normalize reference numbers for consistency
                    report_data = {
                        "short_summary": text_content[:150] + "..." if len(text_content) > 150 else text_content,
                        "markdown_report": text_content,
                        "follow_up_questions": [],
                        "key_insights": [],
                        "information_gaps": [],
                        "methodological_approach": "Direct response",
                        "citation_count": len(all_citations)
                    }
                    report_data = self._normalize_reference_numbers(report_data)
                    return report_data
                    
            except Exception as e:
                self.printer.update_item(
                    "writing",
                    f"Error generating report: {str(e)}",
                    is_done=True
                )
                # Return error report
                return {
                    "short_summary": f"Error: {str(e)}",
                    "markdown_report": f"# Error Generating Report\n\nAn error occurred while generating the research report: \n\n```\n{str(e)}\n```\n\nPlease try again with a different query or research type.",
                    "follow_up_questions": [],
                    "key_insights": [],
                    "information_gaps": ["Complete information could not be retrieved due to an error."],
                    "methodological_approach": "Error occurred",
                    "citation_count": 0
                }
    
    def _normalize_reference_numbers(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure references are consistently numbered throughout the report."""
        if "markdown_report" in report_data:
            # Extract all references from the markdown
            ref_pattern = r'\(\[Reference (\d+)\]'
            refs = re.findall(ref_pattern, report_data["markdown_report"])
            
            if refs:
                # Create mapping from old to new reference numbers
                ref_map = {old: i+1 for i, old in enumerate(sorted(set(refs), key=lambda x: int(x)))}
                
                # Replace all references with normalized numbers
                for old, new in ref_map.items():
                    report_data["markdown_report"] = report_data["markdown_report"].replace(
                        f'[Reference {old}]', f'[Reference {new}]'
                    )
                
                # Also update any reference links in the References section
                ref_link_pattern = r'(\d+)\. \[(.*?)\]'
                ref_section = re.search(r'## References\s+([\s\S]+?)(?=##|$)', report_data["markdown_report"])
                
                if ref_section:
                    ref_section_text = ref_section.group(1)
                    ref_links = re.findall(ref_link_pattern, ref_section_text)
                    
                    if ref_links:
                        # Create replacement for each reference in the References section
                        for old_num, link_text in ref_links:
                            if old_num in ref_map:
                                new_num = str(ref_map[old_num])
                                report_data["markdown_report"] = report_data["markdown_report"].replace(
                                    f'{old_num}. [{link_text}]', f'{new_num}. [{link_text}]'
                                )
        
        return report_data
    
    def _display_final_report(self, report: ReportData) -> None:
        """Display the final report to the user."""
        final_report = f"Report summary\n\n{report.short_summary}"
        self.printer.update_item("final_report", final_report, is_done=True)
        
        print("\n\n=====REPORT=====\n\n")
        print(report.markdown_report)
        
        print("\n\n=====FOLLOW UP QUESTIONS=====\n\n")
        follow_up_questions = "\n".join(report.follow_up_questions)
        print(follow_up_questions)
        
        if hasattr(report, 'key_insights') and report.key_insights:
            print("\n\n=====KEY INSIGHTS=====\n\n")
            key_insights = "\n".join(report.key_insights)
            print(key_insights)
            
        if hasattr(report, 'information_gaps') and report.information_gaps:
            print("\n\n=====INFORMATION GAPS=====\n\n")
            information_gaps = "\n".join(report.information_gaps)
            print(information_gaps)


# Add a custom JSON encoder that can handle Pydantic models
class PydanticJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle Pydantic models and other complex types."""
    def default(self, obj):
        # Handle Pydantic models
        if isinstance(obj, BaseModel):
            return obj.dict()
        # Handle sets by converting to lists
        if isinstance(obj, set):
            return list(obj)
        # Let the base class handle everything else
        return super().default(obj)