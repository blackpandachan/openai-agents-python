from agents import Agent, function_tool
from agents.model_settings import ModelSettings

FILE_SEARCH_PROMPT = """
You are a research assistant specializing in extracting relevant information from files.
Given a query and a file, you will search through the file to find and extract the most
relevant information that addresses the query.

Your task is to:
1. Analyze the query to understand what information is needed
2. Use the file_search function to find relevant content within the file
3. Extract and summarize the most important information
4. Organize the information in a clear, concise format
5. Focus on relevance - only include information that directly helps answer the query

Your response should be a concise summary of the relevant information found in the file,
formatted in a way that makes it easy to incorporate into a research report.
"""

@function_tool
async def local_file_search(query: str, file_path: str) -> str:
    """Search through a local file for relevant information.
    
    Args:
        query: The search query to use for finding relevant information
        file_path: The path to the file to search
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # In a real implementation, we would do more sophisticated searching
        # For now, just return the first 2000 characters of the file
        return f"File content from {file_path} (first 2000 chars): {content[:2000]}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

enhanced_file_search_agent = Agent(
    name="FileSearchAgent",
    instructions=FILE_SEARCH_PROMPT,
    tools=[local_file_search],
    model_settings=ModelSettings(tool_choice="required"),
)