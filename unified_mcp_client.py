#!/usr/bin/env python3
"""
Unified MCP Client
A generic base class for MCP clients with specialized implementations for different servers.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseMCPClient:
    """Base MCP Client with common functionality for all MCP servers"""
    
    def __init__(self, command: str, args: List[str], client_name: str, client_version: str = "1.0.0"):
        """
        Initialize the MCP client
        
        Args:
            command: Command to run (e.g., "uvx")
            args: Arguments for the command (e.g., ["mcp-server-git"])
            client_name: Name of the client for identification
            client_version: Version of the client
        """
        self.command = command
        self.args = args
        self.client_name = client_name
        self.client_version = client_version
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
    
    async def connect(self, timeout: int = 30) -> bool:
        """Connect to the MCP server with timeout"""
        try:
            logger.info(f"Starting {self.client_name} MCP server...")
            
            # Start the MCP server process with timeout
            self.process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    self.command, *self.args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=timeout
            )
            
            logger.info("MCP server process started, initializing...")
            
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
                        "name": self.client_name,
                        "version": self.client_version
                    }
                }
            }
            
            await self._send_request(init_request)
            response = await asyncio.wait_for(self._read_response(), timeout=10)
            
            if response and "result" in response:
                logger.info(f"Successfully connected to {self.client_name} MCP server")
                
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
                
        except asyncio.TimeoutError:
            logger.error(f"Connection timed out after {timeout} seconds")
            await self.disconnect()
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.disconnect()
            return False

    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.process:
            try:
                # Close stdin first to signal the process to stop
                if self.process.stdin and not self.process.stdin.is_closing():
                    self.process.stdin.close()
                    await asyncio.sleep(0.1)
                
                # Try graceful termination first
                if self.process.returncode is None:
                    self.process.terminate()
                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=3)
                        logger.info("Process terminated gracefully")
                    except asyncio.TimeoutError:
                        logger.warning("Process didn't terminate gracefully, forcing kill")
                        self.process.kill()
                        await self.process.wait()
                        logger.info("Process killed forcefully")
                        
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                try:
                    if self.process and self.process.returncode is None:
                        self.process.kill()
                        await self.process.wait()
                except:
                    pass
            finally:
                self.process = None
                logger.info(f"Disconnected from {self.client_name} MCP server")
    
    async def _send_request(self, request: Dict[str, Any]):
        """Send a JSON-RPC request to the server"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Not connected to MCP server")
        
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
    
    async def _read_response(self, timeout: int = 10) -> Dict[str, Any]:
        """Read a JSON-RPC response from the server with timeout"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout=timeout)
            if line:
                line_str = line.decode().strip()
                if line_str:
                    return json.loads(line_str)
            return {}
        except asyncio.TimeoutError:
            logger.error(f"Response timed out after {timeout} seconds")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            if self.process.stderr:
                try:
                    stderr_line = await asyncio.wait_for(self.process.stderr.readline(), timeout=1)
                    if stderr_line:
                        logger.error(f"Server stderr: {stderr_line.decode().strip()}")
                except asyncio.TimeoutError:
                    pass
            return {}
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "tools/list"
            }
            
            await self._send_request(request)
            response = await self._read_response(timeout=100)
            
            if response and "result" in response:
                return response["result"].get("tools", [])
            else:
                logger.error(f"Failed to list tools: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Call a tool with the given arguments"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            await self._send_request(request)
            response = await self._read_response(timeout=timeout)
            
            if response and "result" in response:
                return response["result"]
            else:
                logger.error(f"Failed to call tool {tool_name}: {response}")
                return {"error": f"Failed to call tool {tool_name}"}
                
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"error": str(e)}


class AWSDocsMCPClient(BaseMCPClient):
    """MCP Client for AWS Documentation Server"""
    
    def __init__(self):
        super().__init__(
            command="uvx",
            args=["awslabs.aws-documentation-mcp-server@latest"],
            client_name="aws-docs-client"
        )
    
    async def search_documentation(self, search_phrase: str, **kwargs) -> Dict[str, Any]:
        """Search AWS documentation"""
        try:
            result = await self.call_tool("search_documentation", {
                "search_phrase": search_phrase,
                **kwargs
            })
            
            # Parse the content if it's in the result
            if "content" in result and len(result["content"]) > 0:
                text_content = result["content"][0]["text"]
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return {"text": text_content}
            
            return result
                
        except Exception as e:
            logger.error(f"Failed to search documentation: {e}")
            return {"error": str(e)}
    
    async def read_documentation(self, url: str, **kwargs) -> str:
        """Read a specific AWS documentation page"""
        try:
            result = await self.call_tool("read_documentation", {
                "url": url,
                **kwargs
            })
            
            # Extract text content from result
            if "content" in result and len(result["content"]) > 0:
                return result["content"][0]["text"]
            
            return str(result)
                
        except Exception as e:
            logger.error(f"Failed to read documentation: {e}")
            return f"Error: {str(e)}"


class GitMCPClient(BaseMCPClient):
    """MCP Client for Git Server"""
    
    def __init__(self):
        super().__init__(
            command="uvx",
            args=["mcp-server-git"],
            client_name="git-client"
        )
    
    async def git_status(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Get git status"""
        args = {}
        if repo_path:
            args["repo_path"] = repo_path
        return await self.call_tool("git_status", args)
    
    async def git_log(self, repo_path: Optional[str] = None, max_count: int = 10) -> Dict[str, Any]:
        """Get git log"""
        args = {"max_count": max_count}
        if repo_path:
            args["repo_path"] = repo_path
        return await self.call_tool("git_log", args)
    
    async def git_diff(self, repo_path: Optional[str] = None, cached: bool = False) -> Dict[str, Any]:
        """Get git diff"""
        args = {"cached": cached}
        if repo_path:
            args["repo_path"] = repo_path
        return await self.call_tool("git_diff", args)
    
    async def git_commit(self, message: str, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a git commit"""
        args = {"message": message}
        if repo_path:
            args["repo_path"] = repo_path
        return await self.call_tool("git_commit", args)
    
    async def git_add(self, files: List[str], repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Stage files for commit"""
        args = {"files": files}
        if repo_path:
            args["repo_path"] = repo_path
        return await self.call_tool("git_add", args)


async def demo_aws_client():
    """Demo AWS Documentation client"""
    print("="*60)
    print("AWS DOCUMENTATION CLIENT DEMO")
    print("="*60)
    
    async with AWSDocsMCPClient() as client:
        print("\nConnecting to AWS Documentation MCP server...")
        print("This may take 30-60 seconds on first run...")
        
        if not await client.connect(timeout=100):
            print("Failed to connect")
            return
        
        print("Connected successfully!")
        
        # List tools
        print("\nAvailable tools:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # Search example
        print("\n" + "-"*60)
        print("Searching for 'S3 bucket policies'...")
        result = await client.search_documentation("S3 bucket policies")
        print(json.dumps(result, indent=2)[:500] + "...")


async def demo_git_client():
    """Demo Git client"""
    print("\n" + "="*60)
    print("GIT CLIENT DEMO")
    print("="*60)
    
    async with GitMCPClient() as client:
        print("\nConnecting to Git MCP server...")
        
        if not await client.connect(timeout=30):
            print("Failed to connect")
            return
        
        print("Connected successfully!")
        
        # List tools
        print("\nAvailable tools:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # Git status example
        print("\n" + "-"*60)
        print("Getting git status...")
        result = await client.git_status()
        print(json.dumps(result, indent=2))
        
        # Git log example
        print("\n" + "-"*60)
        print("Getting git log (last 5 commits)...")
        result = await client.git_log(max_count=5)
        print(json.dumps(result, indent=2))


async def main():
    """Run demos for both clients"""
    try:
        await demo_aws_client()
    except Exception as e:
        logger.error(f"AWS client demo error: {e}")
    
    try:
        await demo_git_client()
    except Exception as e:
        logger.error(f"Git client demo error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
