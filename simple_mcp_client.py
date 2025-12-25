#!/usr/bin/env python3
"""
Simple MCP Client for AWS Documentation Server
A straightforward implementation that connects to the AWS Documentation MCP server.
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleAWSDocsMCPClient:
    """Simple MCP Client for AWS Documentation Server using subprocess"""
    
    def __init__(self):
        self.process = None
        self.request_id = 0
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    def _get_next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def connect(self) -> bool:
        """Connect to the AWS Documentation MCP server"""
        try:
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                "uvx", "awslabs.aws-documentation-mcp-server@latest",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {
                            "listChanged": True
                        }
                    },
                    "clientInfo": {
                        "name": "simple-aws-docs-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            await self._send_request(init_request)
            response = await self._read_response()
            
            if response and "result" in response:
                logger.info("Successfully connected to AWS Documentation MCP server")
                
                # Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                await self._send_request(initialized_notification)
                
                return True
            else:
                logger.error(f"Failed to initialize: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None
            logger.info("Disconnected from AWS Documentation MCP server")
    
    async def _send_request(self, request: Dict[str, Any]):
        """Send a JSON-RPC request to the server"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Not connected to MCP server")
        
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
    
    async def _read_response(self) -> Dict[str, Any]:
        """Read a JSON-RPC response from the server"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            line = await self.process.stdout.readline()
            if line:
                line_str = line.decode().strip()
                if line_str:  # Only parse non-empty lines
                    return json.loads(line_str)
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            # Try to read stderr for more context
            if self.process.stderr:
                stderr_line = await self.process.stderr.readline()
                if stderr_line:
                    logger.error(f"Server stderr: {stderr_line.decode().strip()}")
            return {}
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the AWS Documentation server"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "tools/list"
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if response and "result" in response:
                return response["result"].get("tools", [])
            else:
                logger.error(f"Failed to list tools: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def search_documentation(self, search_phrase: str, **kwargs) -> Dict[str, Any]:
        """Search AWS documentation"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "tools/call",
                "params": {
                    "name": "search_documentation",
                    "arguments": {
                        "search_phrase": search_phrase,
                        **kwargs
                    }
                }
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    text_content = content[0]["text"]
                    # Try to parse as JSON, if it fails return as text
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError:
                        return {"text": text_content}
                return {}
            else:
                logger.error(f"Failed to search documentation: {response}")
                return {"error": "Failed to search documentation"}
                
        except Exception as e:
            logger.error(f"Failed to search documentation: {e}")
            return {"error": str(e)}
    
    async def read_documentation(self, url: str, **kwargs) -> str:
        """Read a specific AWS documentation page"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "tools/call",
                "params": {
                    "name": "read_documentation",
                    "arguments": {
                        "url": url,
                        **kwargs
                    }
                }
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0]["text"]
                return ""
            else:
                logger.error(f"Failed to read documentation: {response}")
                return f"Error: Failed to read documentation"
                
        except Exception as e:
            logger.error(f"Failed to read documentation: {e}")
            return f"Error: {str(e)}"


async def main():
    """Example usage of the Simple AWS Documentation MCP client"""
    client = SimpleAWSDocsMCPClient()
    
    try:
        # Connect to the server
        if not await client.connect():
            print("Failed to connect to AWS Documentation MCP server")
            return
        
        # List available tools
        print("Available tools:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # Example search
        print("\n" + "="*50)
        print("Example: Searching for S3 documentation")
        result = await client.search_documentation("S3 bucket policies")
        print(json.dumps(result, indent=2))
        
        # Example read (if we have a URL from search results)
        if result.get("search_results") and len(result["search_results"]) > 0:
            first_url = result["search_results"][0]["url"]
            print(f"\n" + "="*50)
            print(f"Example: Reading documentation from {first_url}")
            content = await client.read_documentation(first_url, max_length=1000)
            print(content[:500] + "..." if len(content) > 500 else content)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    
    finally:
        # Always disconnect
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())