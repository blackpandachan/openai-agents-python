from typing import Any
import os
import datetime
import re

from rich.console import Console, Group
from rich.live import Live
from rich.spinner import Spinner


class Printer:
    def __init__(self, console: Console):
        self.live = Live(console=console)
        self.items: dict[str, tuple[str, bool]] = {}
        self.hide_done_ids: set[str] = set()
        self.live.start()
        self.research_query = ""
        self.research_result = ""

    def end(self) -> None:
        self.live.stop()
        # Save the research results to a markdown file when finishing
        if self.research_query and self.research_result:
            self.save_to_markdown()

    def hide_done_checkmark(self, item_id: str) -> None:
        self.hide_done_ids.add(item_id)

    def update_item(
        self, item_id: str, content: str, is_done: bool = False, hide_checkmark: bool = False
    ) -> None:
        self.items[item_id] = (content, is_done)
        if hide_checkmark:
            self.hide_done_ids.add(item_id)
        self.flush()
        
        # Save the research query if this is the main research item
        if "Researching: " in content:
            self.research_query = content.replace("Researching: ", "")
        
        # Save final research output if this is the result
        if is_done and "Research complete" in content:
            # This is a simple heuristic - in a real system we would have a more
            # structured way to identify the final output
            for item_id, (item_content, item_done) in self.items.items():
                if item_done and "Report" in item_id:
                    self.research_result = item_content
                    break

    def mark_item_done(self, item_id: str) -> None:
        self.items[item_id] = (self.items[item_id][0], True)
        self.flush()

    def flush(self) -> None:
        renderables: list[Any] = []
        for item_id, (content, is_done) in self.items.items():
            if is_done:
                prefix = "✅ " if item_id not in self.hide_done_ids else ""
                renderables.append(prefix + content)
            else:
                renderables.append(Spinner("dots", text=content))
        self.live.update(Group(*renderables))
    
    def save_to_markdown(self) -> str:
        """Save the research results to a markdown file."""
        if not self.research_query:
            self.research_query = "Unknown Query"
            
        # Generate a timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        query_text = self.research_query[:40].replace(" ", "_").replace("/", "-").replace("\\", "-")
        filename = f"research_{query_text}_{timestamp}.md"
        
        # Check if we have a complete report in the research_result field
        if self.research_result and len(self.research_result) > 200:
            # We have a complete report, use it directly with minimal wrapping
            report_content = self.research_result
            
            # Check if it already has a title
            if not report_content.startswith("# "):
                report_content = f"# {self.research_query}\n\n{report_content}"
                
            # Add generation timestamp if not present
            if "*Generated on:" not in report_content:
                timestamp_str = f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                # Insert after the title
                title_end = report_content.find("\n")
                if title_end > 0:
                    report_content = report_content[:title_end+2] + timestamp_str + report_content[title_end+2:]
                else:
                    report_content = report_content + "\n\n" + timestamp_str
            
            # Apply formatting enhancements
            report_content = self._enhance_report_formatting(report_content)
            
            # Extract and add an executive summary if not present
            report_content = self._extract_executive_summary(report_content)
            
            # Save the complete report
            output_dir = os.path.join(os.path.dirname(__file__), "research_output")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"\nResearch report saved to: {output_path}")
                return output_path
            except Exception as e:
                print(f"Error saving markdown file: {str(e)}")
                # Fall back to the force save method
                return self.force_save_to_markdown()
        else:
            # No complete report available, use the force save method
            return self.force_save_to_markdown()
            
    def _enhance_report_formatting(self, report_content):
        """Add light formatting enhancements to improve readability."""
        # Add horizontal rules before major sections
        section_headers = ["## Abstract", "## Introduction", "## Literature Review", 
                          "## Methodology", "## Results", "## Discussion", 
                          "## Conclusion", "## References"]
        
        for header in section_headers:
            if header in report_content:
                # Only add horizontal rule if not already present
                section_pos = report_content.find(header)
                if section_pos > 0 and report_content[section_pos-4:section_pos] != "\n---\n":
                    report_content = report_content.replace(header, f"\n---\n{header}")
        
        # Add key insights metadata section if present in the report data
        insights_section = ""
        if hasattr(self, 'report_data') and self.report_data and 'key_insights' in self.report_data and self.report_data['key_insights']:
            insights_section = "\n\n---\n## Key Insights\n\n"
            for insight in self.report_data['key_insights']:
                insights_section += f"- {insight}\n"
            
            # Insert before references or at the end
            if "## References" in report_content:
                report_content = report_content.replace("## References", f"{insights_section}\n## References")
            else:
                report_content += insights_section
        
        return report_content
    
    def _extract_executive_summary(self, report_content):
        """Extract key points from existing content to create an executive summary."""
        # Only add if not already present
        if "## Executive Summary" not in report_content:
            # Extract first sentence from each major section
            sections = ["Abstract", "Introduction", "Results", "Discussion", "Conclusion"]
            summary_points = []
            
            for section in sections:
                section_pattern = f"## {section}(.*?)(?=##|$)"
                match = re.search(section_pattern, report_content, re.DOTALL)
                if match:
                    section_text = match.group(1).strip()
                    
                    # For abstract, use the first two sentences
                    if section == "Abstract":
                        sentences = re.split(r'(?<=[.!?])\s+', section_text)
                        if sentences and len(sentences) >= 1:
                            summary_points.append(f"- {sentences[0]}")
                            if len(sentences) >= 2:
                                summary_points.append(f"- {sentences[1]}")
                    else:
                        # For other sections, extract key points based on formatting
                        # Look for bullet points first
                        bullets = re.findall(r'- \*\*(.*?)\*\*:(.*?)(?=\n-|\n\n|$)', section_text, re.DOTALL)
                        if bullets:
                            for topic, description in bullets[:2]:  # Limit to first 2 bullet points
                                first_sentence = re.split(r'(?<=[.!?])\s+', description.strip())[0]
                                summary_points.append(f"- **{topic}**: {first_sentence}")
                        else:
                            # If no bullets, use first sentence of the section
                            sentences = re.split(r'(?<=[.!?])\s+', section_text)
                            if sentences and len(sentences) >= 1:
                                summary_points.append(f"- {sentences[0]}")
            
            if summary_points:
                # Add a header for the executive summary
                exec_summary = "\n---\n## Executive Summary\n\n" + "\n".join(summary_points) + "\n\n"
                
                # Insert after abstract or after title if no abstract
                if "## Abstract" in report_content:
                    abstract_end = report_content.find("## Abstract")
                    next_section = report_content.find("##", abstract_end + 1)
                    if next_section != -1:
                        report_content = report_content[:next_section] + exec_summary + report_content[next_section:]
                else:
                    # Insert after the title
                    title_end = report_content.find("\n", report_content.find("#"))
                    if title_end > 0:
                        timestamp_line = report_content.find("*Generated on:")
                        if timestamp_line > 0 and timestamp_line < title_end + 30:
                            # Insert after timestamp
                            timestamp_end = report_content.find("\n\n", timestamp_line)
                            if timestamp_end > 0:
                                report_content = report_content[:timestamp_end+2] + exec_summary + report_content[timestamp_end+2:]
                        else:
                            # Insert after title
                            report_content = report_content[:title_end+2] + exec_summary + report_content[title_end+2:]
        
        return report_content
    
    def force_save_to_markdown(self) -> str:
        """
        Force save the current research state to a markdown file, even if incomplete.
        This is useful for debugging or when the research process is interrupted.
        Returns the filename of the saved markdown file.
        """
        # If we don't have a query yet, use a placeholder
        if not self.research_query:
            self.research_query = "Unknown Query"
            
        # Generate a timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        query_text = self.research_query[:40].replace(" ", "_").replace("/", "-").replace("\\", "-")
        filename = f"research_{query_text}_{timestamp}.md"
        
        # Build markdown content
        markdown_content = f"# Research: {self.research_query}\n\n"
        markdown_content += f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        
        # Add status information
        markdown_content += "## Research Status\n\n"
        markdown_content += "This research may be incomplete. The following shows the current state:\n\n"
        
        # Keep track of significant content we've found
        significant_content = {}
        has_report_content = False
        
        # First pass: Add all items from the research process with their status
        for item_id, (content, is_done) in self.items.items():
            status = "✅ Complete" if is_done else "⏳ In Progress"
            markdown_content += f"### {item_id} ({status})\n"
            
            # Show a preview of the content (first 150 chars) in the status section
            # For content that looks like JSON, only show a brief indicator
            if content.strip().startswith("{") and "}" in content:
                if "markdown_report" in content:
                    preview = "Full research report available"
                    # Flag that we have actual report content
                    has_report_content = True
                else:
                    preview = "JSON content (truncated for readability)"
            else:
                preview = content[:150] + "..." if len(content) > 150 else content
            markdown_content += f"{preview}\n\n"
            
            # Store complete, substantial items for the research content section
            if is_done:
                # For substantial text content
                if len(content) > 200 and not content.strip().startswith("{"):
                    significant_content[item_id] = content
                # For JSON content, we'll handle it specially
                elif content.strip().startswith("{") and "}" in content:
                    # Prioritize content with actual report data
                    if "markdown_report" in content:
                        significant_content[item_id] = {"is_json": True, "content": content, "priority": 10}
                    # Also store output that has useful summary info, but at lower priority
                    elif '"short_summary"' in content:
                        significant_content[item_id] = {"is_json": True, "content": content, "priority": 5}
                    else:
                        significant_content[item_id] = {"is_json": True, "content": content, "priority": 1}
                # Include other items that are more than brief status updates
                elif len(content) > 50:
                    significant_content[item_id] = content
        
        # Look for report content in raw output files
        if not has_report_content:
            output_dir = os.path.join(os.path.dirname(__file__), "research_output")
            if os.path.exists(output_dir):
                # Look for raw output files from newest to oldest
                raw_files = [f for f in os.listdir(output_dir) if f.startswith("raw_agent_output_")]
                raw_files.sort(reverse=True)  # Newest first
                
                # Try to find a file with markdown_report content
                for raw_file in raw_files:
                    try:
                        full_path = os.path.join(output_dir, raw_file)
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "markdown_report" in content:
                                significant_content["external_raw_output"] = {
                                    "is_json": True, 
                                    "content": content,
                                    "priority": 11  # Highest priority
                                }
                                has_report_content = True
                                break
                    except Exception:
                        continue
        
        # Add a proper research content section that shows the complete results
        if significant_content:
            markdown_content += "\n## Research Content\n\n"
            
            # Sort content by priority if available
            prioritized_content = []
            for item_id, content in significant_content.items():
                if isinstance(content, dict) and "priority" in content:
                    prioritized_content.append((item_id, content, content["priority"]))
                else:
                    prioritized_content.append((item_id, content, 0))
            
            # Sort by priority (highest first)
            prioritized_content.sort(key=lambda x: x[2], reverse=True)
            
            # Special case: if we have a final report or research result, show it first
            if self.research_result:
                markdown_content += "### final_report\n\n"
                markdown_content += f"{self.research_result}\n\n"
            
            # Work through the prioritized content for report extraction
            extracted_report = False
            for item_id, content, priority in prioritized_content:
                # Skip lower priority items if we already extracted a good report
                if extracted_report and priority < 5:
                    continue
                    
                if isinstance(content, dict) and content.get("is_json", False):
                    try:
                        import json
                        import re
                        
                        raw_content = content["content"]
                        
                        # Try to extract the markdown_report using regex
                        # This pattern looks for the markdown_report field with proper JSON escaping
                        report_pattern = r'"markdown_report"\s*:\s*"((?:\\.|[^"\\])*)"'
                        report_match = re.search(report_pattern, raw_content)
                        
                        if report_match:
                            # Extract and unescape the markdown report
                            report_text = report_match.group(1)
                            report_text = report_text.replace("\\n", "\n").replace('\\"', '"')
                            
                            # If the report content is substantial, add it
                            if len(report_text) > 200:
                                markdown_content += "### Complete Research Report\n\n"
                                markdown_content += report_text + "\n\n"
                                extracted_report = True
                                continue  # Skip to next item
                        
                        # Try alternate JSON parsing approach if regex didn't work
                        try:
                            # Clean up any potential issues with the JSON string
                            # Sometimes there are string concatenation issues in the output
                            cleaned_json = raw_content.replace("'", '"')
                            cleaned_json = re.sub(r'(["\]])\s*\+\s*(["\[])', r'\1\2', cleaned_json)
                            
                            # Extract just the JSON part if there's text before/after
                            json_start = cleaned_json.find('{')
                            json_end = cleaned_json.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                cleaned_json = cleaned_json[json_start:json_end]
                            
                            # Try to parse
                            report_data = json.loads(cleaned_json)
                            
                            if isinstance(report_data, dict) and "markdown_report" in report_data:
                                report_text = report_data["markdown_report"]
                                if len(report_text) > 200:
                                    markdown_content += "### Complete Research Report\n\n"
                                    markdown_content += report_text + "\n\n"
                                    extracted_report = True
                                    continue  # Skip to next item
                            elif isinstance(report_data, dict) and "short_summary" in report_data:
                                markdown_content += "### Report Summary\n\n"
                                markdown_content += report_data["short_summary"] + "\n\n"
                        except Exception as json_err:
                            print(f"Error parsing JSON: {json_err}")
                            
                    except Exception as e:
                        # Log the error but continue
                        print(f"Error extracting report from JSON: {e}")
                        continue
                elif not extracted_report and not isinstance(content, dict):
                    # Only include text content if we haven't found a proper report
                    # and skip common item IDs
                    if item_id not in ["context", "status", "routing", "research_type"]:
                        markdown_content += f"### {item_id}\n\n"
                        markdown_content += f"{content}\n\n"
        
        # Save the file
        output_dir = os.path.join(os.path.dirname(__file__), "research_output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"\nCurrent research state saved to: {output_path}")
            
            # Also scan for and copy any good report content to a final report file
            if not extracted_report:
                final_report_path = os.path.join(output_dir, f"final_{query_text}_{timestamp}.md")
                try:
                    # Scan all raw output files for report content
                    raw_files = [f for f in os.listdir(output_dir) if f.startswith("raw_agent_output_")]
                    for raw_file in raw_files:
                        full_path = os.path.join(output_dir, raw_file)
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "markdown_report" in content:
                                import re
                                report_pattern = r'"markdown_report"\s*:\s*"((?:\\.|[^"\\])*)"'
                                report_match = re.search(report_pattern, content)
                                
                                if report_match:
                                    report_text = report_match.group(1)
                                    report_text = report_text.replace("\\n", "\n").replace('\\"', '"')
                                    
                                    if len(report_text) > 200:
                                        with open(final_report_path, 'w', encoding='utf-8') as report_file:
                                            report_file.write(f"# {self.research_query}\n\n")
                                            report_file.write(report_text)
                                        print(f"Final report extracted and saved to: {final_report_path}")
                                        break
                except Exception as e:
                    print(f"Error trying to extract final report: {e}")
            
            return output_path
        except Exception as e:
            print(f"Error saving markdown file: {str(e)}")
            return ""
