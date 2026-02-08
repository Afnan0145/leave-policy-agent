"""
Leave Policy Agent - Main ADK Agent Implementation
Built with Google ADK (Agent Development Kit)
"""

import os
import logging
from typing import List, Dict, Any, Optional
import json

# Note: In actual implementation, you would import from google.adk
# For this assignment, we'll create a compatible interface
try:
    from google.adk.agents import Agent
    from google.adk.types import Message, ToolCall
    ADK_AVAILABLE = True
except ImportError:
    # Create mock classes for development
    ADK_AVAILABLE = False
    logging.warning("Google ADK not available, using mock implementation")
    
    class Message:
        def __init__(self, role: str, content: str):
            self.role = role
            self.content = content
    
    class ToolCall:
        def __init__(self, name: str, arguments: dict):
            self.name = name
            self.arguments = arguments
    
    class Agent:
        def __init__(self, **kwargs):
            pass

from litellm import completion

from src.tools.leave_policy_tool import leave_policy_tool
from src.tools.eligibility_tool import eligibility_tool
from src.callbacks.before_model import before_model_callback
from src.callbacks.after_model import after_model_callback

logger = logging.getLogger(__name__)


class LeaveAgent:
    """
    Leave Policy Assistant Agent
    
    Features:
    - Answers questions about leave policies
    - Checks leave eligibility
    - Multi-turn conversations
    - Context preservation
    - Security callbacks
    
    Built with:
    - Google ADK for agent framework
    - LiteLLM for model integration
    - Custom tools for domain logic
    """
    
    # Agent system instructions
    SYSTEM_INSTRUCTIONS = """You are a helpful Leave Policy Assistant for a global company.

Your role is to help employees understand leave policies and check their leave eligibility.

Key responsibilities:
1. Answer questions about leave policies (PTO, sick leave, parental leave, etc.)
2. Check if employees are eligible for specific types of leave
3. Explain leave rules, requirements, and restrictions
4. Help employees understand their leave balance

Important guidelines:
- Always be friendly, professional, and helpful
- Ask for employee ID when needed for eligibility checks
- Clarify which country's policies apply if not specified
- Explain policy requirements clearly (tenure, notice period, etc.)
- Handle edge cases gracefully (invalid dates, unknown leave types)
- If information is missing, politely ask for it
- Never make up policy details - use the tools to get accurate information

Available tools:
- get_leave_policy: Get policy details for a country and leave type
- check_leave_eligibility: Check if an employee is eligible for leave

When users ask about leave:
1. First, understand what country they're in (US, India, UK)
2. Identify the leave type they're asking about
3. Use the get_leave_policy tool to fetch accurate information
4. Present the information in a clear, friendly way

For eligibility questions:
1. Ask for employee ID if not provided
2. Ask for leave type if not clear
3. Use check_leave_eligibility tool with all relevant parameters
4. Explain the results clearly, including why they are/aren't eligible

Remember: Always maintain context across the conversation. If a user asks a follow-up question, remember what you discussed earlier."""
    
    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        session_store: Any = None
    ):
        """
        Initialize the Leave Agent
        
        Args:
            model: LLM model to use (default: from env)
            api_key: API key for LLM (default: from env)
            session_store: Optional session store for persistence
        """
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.session_store = session_store
        
        # Tools available to the agent
        self.tools = {
            "get_leave_policy": leave_policy_tool,
            "check_leave_eligibility": eligibility_tool
        }
        
        # Callbacks
        self.before_model_callback = before_model_callback
        self.after_model_callback = after_model_callback
        
        # Conversation history (in-memory for single session)
        self.conversation_history: List[Dict[str, str]] = []
        
        logger.info(
            f"LeaveAgent initialized with model: {self.model}, "
            f"tools: {list(self.tools.keys())}"
        )
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a chat message and return response
        
        Args:
            message: User message
            session_id: Optional session ID for persistence
            user_context: Optional user context (employee_id, country, etc.)
            
        Returns:
            Agent response
        """
        logger.info(f"Processing message: {message[:50]}...")
        
        # Load session history if session_id provided
        if session_id and self.session_store:
            self.conversation_history = self.session_store.load(session_id)
        
        # Add user context to system if provided
        context_prompt = ""
        if user_context:
            context_prompt = f"\n\nUser Context: {json.dumps(user_context)}"
        
        # Build messages for LLM
        messages = [
            {
                "role": "system",
                "content": self.SYSTEM_INSTRUCTIONS + context_prompt
            }
        ]
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Apply before_model callback
        before_result = self.before_model_callback(messages)
        validated_messages = before_result["messages"]
        
        if not before_result["metadata"]["validation_passed"]:
            logger.warning(
                f"Input validation issues: {before_result['metadata']['issues']}"
            )
        
        # Get response from LLM with tools
        response = self._call_llm_with_tools(validated_messages)
        
        # Apply after_model callback
        after_result = self.after_model_callback(response)
        final_response = after_result["response"]
        
        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": final_response
        })
        
        # Save session if session_id provided
        if session_id and self.session_store:
            self.session_store.save(session_id, self.conversation_history)
        
        logger.info("Message processed successfully")
        return final_response
    
    def _call_llm_with_tools(self, messages: List[Dict[str, str]]) -> str:
        """
        Call LLM with tool support
        
        Args:
            messages: Conversation messages
            
        Returns:
            Final response after tool calls
        """
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"LLM call iteration {iteration}")
            
            # Prepare tool schemas for LLM
            tools_schema = [
                leave_policy_tool.get_schema(),
                eligibility_tool.get_schema()
            ]
            
            # Call LLM
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    tools=tools_schema,
                    tool_choice="auto",
                    api_key=self.api_key
                )
                
                message = response.choices[0].message
                
                # If no tool calls, return the response
                if not hasattr(message, 'tool_calls') or not message.tool_calls:
                    return message.content
                
                # Process tool calls
                logger.info(f"Processing {len(message.tool_calls)} tool calls")
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(
                        f"Executing tool: {function_name} with args: {arguments}"
                    )
                    
                    # Call the tool
                    if function_name in self.tools:
                        result = self.tools[function_name](**arguments)
                    else:
                        result = {"error": f"Unknown tool: {function_name}"}
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(result)
                    })
                
                # Continue loop to get final response
                
            except Exception as e:
                logger.error(f"Error calling LLM: {e}")
                return (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try again or contact support if the issue persists."
                )
        
        # If we hit max iterations, return a response
        return (
            "I've gathered the information, but the response became too complex. "
            "Could you please rephrase your question or break it into smaller parts?"
        )
    
    def reset_conversation(self, session_id: Optional[str] = None):
        """
        Reset conversation history
        
        Args:
            session_id: Optional session ID to clear
        """
        self.conversation_history = []
        
        if session_id and self.session_store:
            self.session_store.delete(session_id)
        
        logger.info("Conversation reset")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get current conversation history"""
        return self.conversation_history.copy()


def main():
    """
    Main function for interactive testing
    """
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("Leave Policy Assistant Agent")
    print("=" * 60)
    print("Type 'quit' or 'exit' to end the conversation")
    print("Type 'reset' to start a new conversation")
    print("=" * 60)
    print()
    
    # Initialize agent
    agent = LeaveAgent()
    
    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == 'reset':
                agent.reset_conversation()
                print("\n[Conversation reset]\n")
                continue
            
            # Get response
            response = agent.chat(user_input)
            print(f"\nAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()