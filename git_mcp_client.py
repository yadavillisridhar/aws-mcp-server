#!/usr/bin/env python3
"""
Git MCP Client
A client implementation for the mcp-server-git MCP server.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitMCPClient:
    """MCP Client for Git Server"""
    
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
    
    async def connect(self, timeout: int = 30) -> bool:
        """Connect to the Git MCP server with timeout"""
        try:
            logger.info("Starting Git MCP server...")
            
            # Start the MCP server process with timeout
            self.process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "uvx", "mcp-server-git",
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
                        "name": "git-mcp-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            await self._send_request(init_request)
            response = await asyncio.wait_for(self._read_response(), timeout=10)
            
            if response and "result" in response:
                logger.info("Successfully connected to Git MCP server")
                
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
                logger.info("Disconnected from Git MCP server")
    
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
        """List available tools from the Git server"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "tools/list"
            }
            
            await self._send_request(request)
            response = await self._read_response(timeout=10)
            
            if response and "result" in response:
                return response["result"].get("tools", [])
            else:
                logger.error(f"Failed to list tools: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Git tool with the given arguments"""
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
            response = await self._read_response(timeout=30)
            
            if response and "result" in response:
                return response["result"]
            else:
                logger.error(f"Failed to call tool {tool_name}: {response}")
                return {"error": f"Failed to call tool {tool_name}"}
                
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"error": str(e)}
    
    # Git-specific convenience methods
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


async def main():
    """Example usage of the Git MCP client"""
    client = GitMCPClient()
    
    try:
        print("Connecting to Git MCP server...")
        
        if not await client.connect(timeout=30):
            print("Failed to connect to Git MCP server")
            return
        
        print("Connected successfully!")
        
        # List available tools
        print("\nListing available tools...")
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"- {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # Example: Get git status
        print("\n" + "="*50)
        print("Example: Getting git status")
        result = await client.git_status()
        print(json.dumps(result, indent=2))
        
        # Example: Get git log
        print("\n" + "="*50)
        print("Example: Getting git log (last 5 commits)")
        result = await client.git_log(max_count=5)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    
    finally:
        print("\nDisconnecting...")
        await client.disconnect()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
