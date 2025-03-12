from __future__ import annotations

import asyncio
import os
import time
from typing import List, Optional, Dict, Any

from rich.console import Console

from agents import Runner, custom_span, trace, ItemHelpers

from examples.research_bot.agents.planner_agent import WebSearchItem, WebSearchPlan, enhanced_planner_agent
from examples.research_bot.agents.search_agent import enhanced_search_agent
from examples.research_bot.agents.writer_agent import ReportData, enhanced_writer_agent
from examples.research_bot.agents.evaluator_agent import EvaluationResult, enhanced_evaluator_agent
from examples.research_bot.agents.file_search_agent import enhanced_file_search_agent
from examples.research_bot.printer import Printer


class EnhancedResearchManager:
    """Enhanced research manager using the Agents SDK."""
    
    def __init__(self):
        self.console = Console()
        self.printer = Printer(self.console)
        self.trace_id = None

    async def run(self, query: str, file_paths: Optional[List[str]] = None) -> None:
        """Run the full research process."""
        with trace("Research trace") as current_trace:
            self.trace_id = current_trace.trace_id
            
            self.printer.update_item(
                "trace_id",
                f"View trace: https://platform.openai.com/traces/{self.trace_id}",
                is_done=True,
                hide_checkmark=True,
            )
            
            self.printer.update_item(
                "starting",
                "Starting enhanced research...",
                is_done=True,
                hide_checkmark=True,
            )
            
            # 1. Generate search plan
            search_plan = await self._plan_searches(query)
            
            # 2. Perform file search if files are provided
            file_search_results = []
            if file_paths and len(file_paths) > 0:
                file_search_results = await self._search_files(query, file_paths)
                self.printer.update_item(
                    "file_search", 
                    f"File search completed, found {len(file_search_results)} relevant sections", 
                    is_done=True
                )
            
            # 3. Perform web searches
            web_search_results = await self._perform_searches(search_plan)
            
            # 4. Write initial report
            report = await self._write_report(query, web_search_results, file_search_results)
            
            # 5. Evaluate report and improve if needed
            final_report = await self._evaluate_and_improve(query, report, search_plan)
            
            # 6. Display final report
            self._display_final_report(final_report)
            
            self.printer.end()

    async def _plan_searches(self, query: str) -> WebSearchPlan:
        """Plan web searches based on the query."""
        with custom_span("Planning searches"):
            self.printer.update_item("planning", "Planning searches...")
            
            try:
                result = await Runner.run(
                    enhanced_planner_agent,
                    f"Query: {query}",
                )
                
                search_plan = result.final_output_as(WebSearchPlan)
                self.printer.update_item(
                    "planning",
                    f"Will perform {len(search_plan.searches)} searches",
                    is_done=True,
                )
                
                return search_plan
                
            except Exception as e:
                self.printer.update_item(
                    "planning_error",
                    f"Error during planning: {str(e)}",
                    is_done=True,
                )
                # Return a minimal plan if there's an error
                return WebSearchPlan(
                    searches=[WebSearchItem(reason="Main query search", query=query)],
                    priority_searches=[0],  # The first search is the priority
                    areas_covered=["General overview"]  # Basic coverage area
                )

    async def _search_files(self, query: str, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Search through provided files for relevant information."""
        with custom_span("Searching files"):
            self.printer.update_item("file_search", "Searching through files...")
            
            file_results = []
            for file_path in file_paths:
                if os.path.exists(file_path):
                    try:
                        # We're now using our custom file search function tool
                        # which takes both query and file_path
                        file_input = f"""
                        I need to search the following file for information:
                        File path: {file_path}
                        Search query: {query}
                        
                        Please use the file_search function to extract relevant information.
                        """
                        
                        result = await Runner.run(
                            enhanced_file_search_agent,
                            file_input
                        )
                        
                        file_content = ItemHelpers.text_message_outputs(result.new_items)
                        
                        file_results.append({
                            "file": file_path,
                            "content": file_content
                        })
                        
                    except Exception as e:
                        self.printer.update_item(
                            "file_search",
                            f"Error searching file {file_path}: {str(e)}",
                            is_done=False,
                        )
            
            return file_results

    async def _perform_searches(self, search_plan: WebSearchPlan) -> List[Dict[str, Any]]:
        """Perform web searches based on the search plan."""
        with custom_span("Searching the web"):
            self.printer.update_item("searching", "Searching the web...")
            
            # Prioritize searches if priority_searches is available
            ordered_searches = []
            if hasattr(search_plan, 'priority_searches') and search_plan.priority_searches:
                # First add priority searches
                for idx in search_plan.priority_searches:
                    if 0 <= idx < len(search_plan.searches):
                        ordered_searches.append(search_plan.searches[idx])
                
                # Then add remaining searches
                for i, item in enumerate(search_plan.searches):
                    if i not in search_plan.priority_searches:
                        ordered_searches.append(item)
            else:
                # If no priority searches defined, use all searches in order
                ordered_searches = search_plan.searches
            
            async def search(item: WebSearchItem) -> Dict[str, Any]:
                try:
                    input_text = f"Search term: {item.query}\nReason for searching: {item.reason}"
                    result = await Runner.run(
                        enhanced_search_agent,
                        input_text,
                    )
                    
                    summary = ItemHelpers.text_message_outputs(result.new_items)
                    
                    return {
                        "query": item.query,
                        "reason": item.reason,
                        "summary": summary,
                        "success": True
                    }
                except Exception as e:
                    return {
                        "query": item.query,
                        "reason": item.reason,
                        "error": str(e),
                        "success": False
                    }
            
            tasks = [asyncio.create_task(search(item)) for item in ordered_searches]
            num_completed = 0
            
            results = []
            for task in asyncio.as_completed(tasks):
                result = await task
                if result.get("success", False):
                    results.append(result)
                
                num_completed += 1
                self.printer.update_item(
                    "searching",
                    f"Searching... {num_completed}/{len(tasks)} completed"
                )
            
            self.printer.mark_item_done("searching")
            
            return results

    async def _write_report(
        self, 
        query: str, 
        web_search_results: List[Dict[str, Any]], 
        file_search_results: List[Dict[str, Any]]
    ) -> ReportData:
        """Write a report based on search results."""
        with custom_span("Writing report"):
            self.printer.update_item("writing", "Thinking about report...")
            
            web_results_summary = "\n".join([
                f"Web search for '{r['query']}': {r['summary']}" 
                for r in web_search_results if r.get("success", False)
            ])
            
            file_results_summary = "\n".join([
                f"File search in '{r['file']}': {r['content']}" 
                for r in file_search_results
            ])
            
            input_content = (
                f"Original query: {query}\n\n"
                f"Web search results:\n{web_results_summary}\n\n"
            )
            
            if file_results_summary:
                input_content += f"File search results:\n{file_results_summary}\n\n"
            
            # Use sequential progress updates
            update_messages = [
                "Thinking about report...",
                "Planning report structure...",
                "Creating sections...",
                "Finalizing report...",
            ]
            
            # Show progress messages sequentially
            for message in update_messages:
                self.printer.update_item("writing", message)
                await asyncio.sleep(3)  # Wait a bit before showing next message
            
            # Run the writer agent without streaming
            result = await Runner.run(
                enhanced_writer_agent,
                input_content,
            )
            
            # Extract the full report text from the result
            # This uses a more thorough approach to extract all text content
            full_report = None
            
            try:
                # First try to extract the report as a structured object
                full_report = result.final_output_as(ReportData)
            except Exception as e:
                # If that fails, try to extract text directly from items
                self.printer.update_item(
                    "writing",
                    "Extracting report content...",
                    is_done=False
                )
                
                # Get all text content from the result
                all_text = ""
                
                # Extract text from all message items
                for item in result.new_items:
                    if hasattr(item, "content"):
                        all_text += item.content + "\n\n"
                
                # If we got text but couldn't parse it as ReportData,
                # create a basic ReportData object with the text
                if all_text:
                    full_report = ReportData(
                        short_summary=f"Research on: {query}",
                        markdown_report=all_text,
                        follow_up_questions=["What follow-up research would be valuable?"],
                        key_insights=["Extracted from raw response"],
                        information_gaps=["Structured parsing failed"]
                    )
                else:
                    # If all else fails, create a minimal report
                    full_report = ReportData(
                        short_summary=f"Research on: {query}",
                        markdown_report=f"# Research Report on {query}\n\nUnable to extract full report content.",
                        follow_up_questions=["How can we improve this research?"],
                        key_insights=["Error occurred during report extraction"],
                        information_gaps=["Complete report could not be extracted"]
                    )
            
            self.printer.mark_item_done("writing")
            
            return full_report

    async def _evaluate_and_improve(
        self, 
        query: str, 
        initial_report: ReportData,
        search_plan: WebSearchPlan
    ) -> ReportData:
        """Evaluate the report and suggest improvements."""
        with custom_span("Evaluating report"):
            self.printer.update_item("evaluating", "Evaluating report quality...")
            
            try:
                # Submit for evaluation
                eval_input = (
                    f"Query: {query}\n\n"
                    f"Report summary: {initial_report.short_summary}\n\n"
                    f"Full report: {initial_report.markdown_report}\n\n"
                    f"Evaluate if this report adequately answers the query keeping in mind the final report should be 1500-2000 words at a minimum and suggest improvements."
                )
                
                eval_result = await Runner.run(
                    enhanced_evaluator_agent,
                    eval_input,
                )
                
                evaluation = eval_result.final_output_as(EvaluationResult)
                
                # If improvements needed and score is below threshold, refine the report
                if evaluation.score < 8 and evaluation.improvements:
                    self.printer.update_item(
                        "evaluating", 
                        f"Report quality score: {evaluation.score}/10. Improving report...boss big mad",
                        is_done=True
                    )
                    
                    with custom_span("Improving report"):
                        self.printer.update_item("improving", "Refining the report...because boss be mad")
                        
                        # Request an improved report
                        improve_input = (
                            f"Original query: {query}\n\n"
                            f"Please improve the initial report based on this feedback:\n"
                            f"{evaluation.feedback}\n\n"
                            f"Suggested improvements: {', '.join(evaluation.improvements)}\n\n"
                            f"Initial report: {initial_report.markdown_report}"
                        )
                        
                        improved_result = await Runner.run(
                            enhanced_writer_agent,
                            improve_input,
                        )
                        
                        self.printer.mark_item_done("improving")
                        
                        return improved_result.final_output_as(ReportData)
                else:
                    self.printer.update_item(
                        "evaluating", 
                        f"Report quality score: {evaluation.score}/10. No improvements needed. Good job!",
                        is_done=True
                    )
                    return initial_report
                    
            except Exception as e:
                self.printer.update_item(
                    "evaluation_error",
                    f"Error during evaluation: {str(e)}. Using initial report.",
                    is_done=True
                )
                return initial_report

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
            
        print(f"\nView the full trace at: https://platform.openai.com/traces/{self.trace_id}")