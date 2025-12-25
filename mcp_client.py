#!/usr/bin/env python3
"""
MCP Client for AWS Documentation Server
Connects to the AWS Documentation MCP server and provides methods to query AWS documentation.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSDocsMCPClient:
    """MCP Client for AWS Documentation Server"""
    
    def __init__(self):
        self.server_params = StdioServerParameters(
            command="uvx",
            args=["awslabs.aws-documentation-mcp-server@latest"],
            env={"FASTMCP_LOG_LEVEL": "ERROR"}
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        try:
            # Create stdio client connection using context manager
            self.stdio_context = stdio_client(self.server_params)
            read_stream, write_stream = await self.stdio_context.__aenter__()
            self.session = ClientSession(read_stream, write_stream)
            
            # Initialize the session
            await self.session.initialize()
            logger.info("Successfully connected to AWS Documentation MCP server")
            return self
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        
        if hasattr(self, 'stdio_context') and self.stdio_context:
            await self.stdio_context.__aexit__(exc_type, exc_val, exc_tb)
            
        logger.info("Disconnected from AWS Documentation MCP server")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the AWS Documentation server"""
        if not hasattr(self, 'session') or not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            response = await self.session.list_tools()
            return [{"name": tool.name, "description": tool.description} for tool in response.tools]
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def search_documentation(self, search_phrase: str, **kwargs) -> Dict[str, Any]:
        """Search AWS documentation"""
        if not hasattr(self, 'session') or not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            # Prepare arguments for the search tool
            args = {"search_phrase": search_phrase}
            args.update(kwargs)
            
            # Call the search tool
            response = await self.session.call_tool("mcp_aws_docs_search_documentation", args)
            return json.loads(response.content[0].text) if response.content else {}
            
        except Exception as e:
            logger.error(f"Failed to search documentation: {e}")
            return {"error": str(e)}
    
    async def read_documentation(self, url: str, **kwargs) -> str:
        """Read a specific AWS documentation page"""
        if not hasattr(self, 'session') or not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            # Prepare arguments for the read tool
            args = {"url": url}
            args.update(kwargs)
            
            # Call the read tool
            response = await self.session.call_tool("mcp_aws_docs_read_documentation", args)
            return response.content[0].text if response.content else ""
            
        except Exception as e:
            logger.error(f"Failed to read documentation: {e}")
            return f"Error: {str(e)}"
    
    async def get_recommendations(self, url: str) -> Dict[str, Any]:
        """Get content recommendations for an AWS documentation page"""
        if not hasattr(self, 'session') or not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            # Call the recommend tool
            response = await self.session.call_tool("mcp_aws_docs_recommend", {"url": url})
            return json.loads(response.content[0].text) if response.content else {}
            
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return {"error": str(e)}


async def main():
    """Example usage of the AWS Documentation MCP client"""
    
    try:
        async with AWSDocsMCPClient() as client:
            # List available tools
            print("Available tools:")
            tools = await client.list_tools()
            for tool in tools:
                print(f"- {tool['name']}: {tool['description']}")
            
            # Example searches
            print("\n" + "="*50)
            print("Example: Searching for S3 documentation")
            result = await client.search_documentation("S3 bucket policies")
            print(json.dumps(result, indent=2))
            
            print("\n" + "="*50)
            print("Example: Searching for Lambda documentation")
            result = await client.search_documentation("Lambda function configuration")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":
    asyncio.run(main())