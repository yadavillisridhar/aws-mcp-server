#!/usr/bin/env python3
"""
LLM Agent with MCP Tools
An agent that uses LLM to decide which MCP tools to call based on user queries.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from unified_mcp_client import AWSDocsMCPClient, GitMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. Install with: pip install openai")


class MCPAgent:
    """LLM Agent that uses MCP clients as tools"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the agent
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: OpenAI model to use
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library required. Install with: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
        self.aws_client = None
        self.git_client = None
        self.conversation_history = []
        
        # Define available tools for the LLM
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_aws_documentation",
                    "description": "Search AWS documentation for information about AWS services, features, and best practices",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_phrase": {
                                "type": "string",
                                "description": "The search query for AWS documentation"
                            }
                        },
                        "required": ["search_phrase"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_aws_documentation",
                    "description": "Read a specific AWS documentation page given its URL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL of the AWS documentation page to read"
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "Maximum length of content to return (optional)"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_status",
                    "description": "Get the current git status of the repository, showing modified, staged, and untracked files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "repo_path": {
                                "type": "string",
                                "description": "Path to the git repository (optional, defaults to current directory)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_log",
                    "description": "Get the git commit history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_count": {
                                "type": "integer",
                                "description": "Maximum number of commits to return (default: 10)"
                            },
                            "repo_path": {
                                "type": "string",
                                "description": "Path to the git repository (optional)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_diff",
                    "description": "Get the git diff showing changes in the working directory or staged changes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cached": {
                                "type": "boolean",
                                "description": "If true, show staged changes; if false, show unstaged changes"
                            },
                            "repo_path": {
                                "type": "string",
                                "description": "Path to the git repository (optional)"
                            }
                        }
                    }
                }
            }
        ]
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_clients()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup_clients()
    
    async def initialize_clients(self):
        """Initialize MCP clients"""
        logger.info("Initializing MCP clients...")
        
        # Initialize AWS client
        self.aws_client = AWSDocsMCPClient()
        await self.aws_client.__aenter__()
        if not await self.aws_client.connect(timeout=100):
            logger.warning("Failed to connect to AWS Documentation MCP server")
        else:
            logger.info("AWS Documentation client connected")
        
        # Initialize Git client
        self.git_client = GitMCPClient()
        await self.git_client.__aenter__()
        if not await self.git_client.connect(timeout=30):
            logger.warning("Failed to connect to Git MCP server")
        else:
            logger.info("Git client connected")

    async def cleanup_clients(self):
        """Cleanup MCP clients"""
        logger.info("Cleaning up MCP clients...")
        
        if self.aws_client:
            await self.aws_client.__aexit__(None, None, None)
        
        if self.git_client:
            await self.git_client.__aexit__(None, None, None)
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool call and return the result as a string"""
        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            
            if tool_name == "search_aws_documentation":
                result = await self.aws_client.search_documentation(**arguments)
                return json.dumps(result, indent=2)
            
            elif tool_name == "read_aws_documentation":
                result = await self.aws_client.read_documentation(**arguments)
                return result
            
            elif tool_name == "git_status":
                result = await self.git_client.git_status(**arguments)
                return json.dumps(result, indent=2)
            
            elif tool_name == "git_log":
                result = await self.git_client.git_log(**arguments)
                return json.dumps(result, indent=2)
            
            elif tool_name == "git_diff":
                result = await self.git_client.git_diff(**arguments)
                return json.dumps(result, indent=2)
            
            else:
                return f"Error: Unknown tool '{tool_name}'"
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"
    
    async def chat(self, user_message: str, max_iterations: int = 5) -> str:
        """
        Process a user message and return the agent's response
        
        Args:
            user_message: The user's input message
            max_iterations: Maximum number of tool calls to prevent infinite loops
            
        Returns:
            The agent's final response
        """
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call the LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Add assistant's response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls if message.tool_calls else None
            })
            
            # If no tool calls, return the response
            if not message.tool_calls:
                return message.content or "No response generated"
            
            # Execute tool calls
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the tool
                tool_result = await self.execute_tool(function_name, function_args)
                
                # Add tool result to conversation history
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
        
        return "Maximum iterations reached. Please try rephrasing your question."
    
    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation_history = []
        logger.info("Conversation history reset")


async def interactive_mode():
    """Run the agent in interactive mode"""
    print("="*70)
    print("MCP AGENT - Interactive Mode")
    print("="*70)
    print("\nThis agent can help you with:")
    print("  - AWS documentation searches and queries")
    print("  - Git repository operations (status, log, diff)")
    print("\nType 'quit' or 'exit' to stop")
    print("Type 'reset' to clear conversation history")
    print("="*70)
    
    async with MCPAgent() as agent:
        print("\n✓ Agent initialized and ready!\n")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit']:
                    print("\nGoodbye!")
                    break
                
                if user_input.lower() == 'reset':
                    agent.reset_conversation()
                    print("\n✓ Conversation history cleared")
                    continue
                
                print("\nAgent: ", end="", flush=True)
                response = await agent.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\nError: {e}")


async def demo_mode():
    """Run predefined demo queries"""
    print("="*70)
    print("MCP AGENT - Demo Mode")
    print("="*70)
    
    demo_queries = [
        "What is the current git status of this repository?",
        "Show me the last 3 commits in the git log",
        "Search AWS documentation for S3 bucket policies",
    ]
    
    async with MCPAgent() as agent:
        print("\n✓ Agent initialized!\n")
        
        for i, query in enumerate(demo_queries, 1):
            print(f"\n{'='*70}")
            print(f"Demo Query {i}: {query}")
            print('='*70)
            
            response = await agent.chat(query)
            print(f"\nAgent Response:\n{response}")
            
            # Reset conversation between demos
            agent.reset_conversation()
            
            # Small delay between queries
            await asyncio.sleep(1)


async def main():
    """Main entry point"""
    import sys
    
    if not OPENAI_AVAILABLE:
        print("Error: OpenAI library not installed")
        print("Install with: pip install openai")
        return
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        return
    
    # Check command line arguments
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
    
    if mode == "demo":
        await demo_mode()
    else:
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
