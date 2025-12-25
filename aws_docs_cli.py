#!/usr/bin/env python3
"""
CLI interface for AWS Documentation MCP Client
Provides a command-line interface to interact with AWS documentation.
"""

import asyncio
import argparse
import json
import sys
from mcp_client import AWSDocsMCPClient


async def search_command(client: AWSDocsMCPClient, args):
    """Handle search command"""
    kwargs = {}
    if args.service:
        kwargs['product_types'] = [args.service]
    
    result = await client.search_documentation(args.query, **kwargs)
    print(json.dumps(result, indent=2))


async def read_command(client: AWSDocsMCPClient, args):
    """Handle read documentation command"""
    result = await client.read_documentation(args.url)
    print(result)


async def recommend_command(client: AWSDocsMCPClient, args):
    """Handle recommendations command"""
    result = await client.get_recommendations(args.url)
    print(json.dumps(result, indent=2))


async def tools_command(client: AWSDocsMCPClient, args):
    """Handle list tools command"""
    tools = await client.list_tools()
    print("Available tools:")
    for tool in tools:
        print(f"- {tool['name']}")
        print(f"  Description: {tool['description']}")
        print()


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="AWS Documentation MCP Client CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search AWS documentation')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--service', help='Specific AWS service to search in')
    
    # Read documentation command
    read_parser = subparsers.add_parser('read', help='Read AWS documentation page')
    read_parser.add_argument('url', help='URL of the AWS documentation page')
    
    # Recommendations command
    recommend_parser = subparsers.add_parser('recommend', help='Get recommendations for a documentation page')
    recommend_parser.add_argument('url', help='URL of the AWS documentation page')
    
    # List tools command
    tools_parser = subparsers.add_parser('tools', help='List available MCP tools')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create and connect client using async context manager
    try:
        async with AWSDocsMCPClient() as client:
            # Execute command
            if args.command == 'search':
                await search_command(client, args)
            elif args.command == 'read':
                await read_command(client, args)
            elif args.command == 'recommend':
                await recommend_command(client, args)
            elif args.command == 'tools':
                await tools_command(client, args)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))