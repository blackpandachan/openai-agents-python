from __future__ import annotations

import asyncio
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

import openai
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class EnhancedAgent:
    """Base agent class that leverages the new Response API"""
    
    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = "gpt-4-response",
        output_type: Optional[Type[T]] = None,
        tools: List[str] = None,
        tool_choice: str = "auto",
        max_retries: int = 2,
        retry_delay: float = 1.0
    ):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.output_type = output_type
        self.tools = tools or []
        self.tool_choice = tool_choice
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    async def run(
        self, 
        user_input: str, 
        context: Optional[List[dict]] = None,
        session_id: Optional[str] = None
    ) -> RunResult:
        """Run the agent with the given input and optional context."""
        messages = [
            {"role": "system", "content": self.instructions},
        ]
        
        # Add context messages if provided
        if context:
            messages.extend(context)
            
        # Add the user input
        messages.append({"role": "user", "content": user_input})
        
        return await self._execute_with_retry(messages, session_id)
    
    async def run_with_tools(
        self,
        user_input: str,
        tool_handlers: dict[str, Callable] = None,
        context: Optional[List[dict]] = None,
        session_id: Optional[str] = None
    ) -> RunResult:
        """Run the agent with tools and handle tool invocations."""
        messages = [
            {"role": "system", "content": self.instructions},
        ]
        
        # Add context messages if provided
        if context:
            messages.extend(context)
            
        # Add the user input
        messages.append({"role": "user", "content": user_input})
        
        for retry in range(self.max_retries + 1):
            try:
                response = await openai.Response.acreate(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice=self.tool_choice,
                    response_format={"type": "json_object"} if self.output_type else None,
                    user=session_id
                )
                
                structured_response = response.get('structured_content', {})
                
                # Check for tool invocations
                tool_invocations = []
                for tool in self.tools:
                    invoke_key = f"invoke_{tool}"
                    if invoke_key in structured_response:
                        tool_invocations.append((tool, structured_response[invoke_key]))
                
                # If there are tool invocations, process them
                if tool_invocations and tool_handlers:
                    for tool_name, tool_params in tool_invocations:
                        if tool_name in tool_handlers:
                            tool_result = await tool_handlers[tool_name](tool_params)
                            
                            # Add the tool invocation and result to messages
                            messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [{
                                    "id": f"call_{len(messages)}",
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": str(tool_params)
                                    }
                                }]
                            })
                            
                            messages.append({
                                "role": "tool",
                                "content": str(tool_result),
                                "tool_call_id": f"call_{len(messages) - 1}"
                            })
                    
                    # Get the final response after tool usage
                    return await self._execute_with_retry(messages, session_id)
                
                return RunResult(response, self.output_type)
                
            except Exception as e:
                if retry < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** retry))  # Exponential backoff
                else:
                    raise e
    
    async def _execute_with_retry(self, messages: List[dict], session_id: Optional[str] = None) -> RunResult:
        """Execute the agent with retry logic."""
        for retry in range(self.max_retries + 1):
            try:
                response = await openai.Response.acreate(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice=self.tool_choice,
                    response_format={"type": "json_object"} if self.output_type else None,
                    user=session_id
                )
                
                return RunResult(response, self.output_type)
                
            except Exception as e:
                if retry < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** retry))  # Exponential backoff
                else:
                    raise e


class RunResult:
    """Contains the response from an agent run."""
    
    def __init__(self, response: Any, output_type: Optional[Type[T]] = None):
        self.response = response
        self.output_type = output_type
        self._final_output = None
    
    @property
    def final_output(self) -> Any:
        """Get the final structured output from the response."""
        if self._final_output is None:
            self._final_output = self.response.get('structured_content', {})
        return self._final_output
    
    def final_output_as(self, model_type: Type[T]) -> T:
        """Convert the final output to the specified model type."""
        return model_type.parse_obj(self.final_output)
    
    async def stream_events(self):
        """Stream events from a streaming response."""
        # This needs to be implemented based on how the new Response API handles streaming
        if hasattr(self.response, 'stream_events'):
            async for event in self.response.stream_events():
                yield event
        else:
            yield self.response
