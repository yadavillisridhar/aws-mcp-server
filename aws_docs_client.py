#!/usr/bin/env python3
"""
AWS Documentation MCP Client
A complete CLI tool for interacting with AWS documentation via MCP.
"""

import asyncio
import json
import argparse
import sys
from simple_mcp_client import SimpleAWSDocsMCPClient


async def search_command(args):
    """Handle search command"""
    async with SimpleAWSDocsMCPClient() as client:
        if not await client.connect():
            print("Error: Failed to connect to AWS Documentation MCP server", file=sys.stderr)
            return 1
        
        kwargs = {}
        if args.service:
            kwargs['product_types'] = [args.service]
        if args.limit:
            kwargs['limit'] = args.limit
        
        result = await client.search_documentation(args.query, **kwargs)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            # Pretty print search results
            if "search_results" in result:
                print(f"Found {len(result['search_results'])} results for '{args.query}':\n")
                for i, item in enumerate(result['search_results'], 1):
                    print(f"{i}. {item['title']}")
                    print(f"   URL: {item['url']}")
                    if item.get('context'):
                        print(f"   Context: {item['context']}")
                    print()
            else:
                print("No results found or error occurred.")
                if "error" in result:
                    print(f"Error: {result['error']}")
        
        await client.disconnect()
        return 0


async def read_command(args):
    """Handle read documentation command"""
    async with SimpleAWSDocsMCPClient() as client:
        if not await client.connect():
            print("Error: Failed to connect to AWS Documentation MCP server", file=sys.stderr)
            return 1
        
        kwargs = {}
        if args.max_length:
            kwargs['max_length'] = args.max_length
        if args.start_index:
            kwargs['start_index'] = args.start_index
        
        result = await client.read_documentation(args.url, **kwargs)
        print(result)
        
        await client.disconnect()
        return 0


async def tools_command(args):
    """Handle list tools command"""
    async with SimpleAWSDocsMCPClient() as client:
        if not await client.connect():
            print("Error: Failed to connect to AWS Documentation MCP server", file=sys.stderr)
            return 1
        
        tools = await client.list_tools()
        print("Available AWS Documentation MCP Tools:\n")
        for tool in tools:
            print(f"• {tool['name']}")
            print(f"  {tool['description'][:100]}...")
            print()
        
        await client.disconnect()
        return 0


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="AWS Documentation MCP Client - Search and read AWS documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s search "S3 bucket policies"
  %(prog)s search "Lambda functions" --service "AWS Lambda"
  %(prog)s read https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html
  %(prog)s tools
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search AWS documentation')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--service', help='Filter by specific AWS service')
    search_parser.add_argument('--limit', type=int, help='Maximum number of results (default: 10)')
    search_parser.add_argument('--json', action='store_true', help='Output raw JSON response')
    
    # Read documentation command
    read_parser = subparsers.add_parser('read', help='Read AWS documentation page')
    read_parser.add_argument('url', help='URL of the AWS documentation page')
    read_parser.add_argument('--max-length', type=int, help='Maximum characters to return')
    read_parser.add_argument('--start-index', type=int, help='Starting character index')
    
    # List tools command
    tools_parser = subparsers.add_parser('tools', help='List available MCP tools')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Execute command
    try:
        if args.command == 'search':
            return asyncio.run(search_command(args))
        elif args.command == 'read':
            return asyncio.run(read_command(args))
        elif args.command == 'tools':
            return asyncio.run(tools_command(args))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())