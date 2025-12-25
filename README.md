# AWS Documentation MCP Client

This project provides a Python client for connecting to the AWS Documentation MCP (Model Context Protocol) server. It allows you to programmatically search and retrieve AWS documentation.

## Prerequisites

1. **Install uv and uvx**: The MCP server uses `uvx` to run. Install it following the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

2. **Python 3.8+**: Make sure you have Python 3.8 or later installed.

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. The MCP server configuration is already set up in `.kiro/settings/mcp.json`.

## Usage

### Command Line Interface (Recommended)

The CLI provides the easiest way to interact with AWS documentation:

```bash
# Search AWS documentation
python aws_docs_client.py search "S3 bucket policies"

# Search with service filter
python aws_docs_client.py search "encryption" --service "Amazon Simple Storage Service"

# Read a specific documentation page
python aws_docs_client.py read "https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html"

# Read with length limit
python aws_docs_client.py read "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html" --max-length 1000

# List available MCP tools
python aws_docs_client.py tools

# Get raw JSON output
python aws_docs_client.py search "Lambda functions" --json
```

### Python API

```python
import asyncio
from simple_mcp_client import SimpleAWSDocsMCPClient

async def example():
    client = SimpleAWSDocsMCPClient()
    
    # Connect to the server
    if await client.connect():
        # Search documentation
        result = await client.search_documentation("S3 bucket policies")
        print(result)
        
        # Read specific documentation
        content = await client.read_documentation(
            "https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html",
            max_length=1000
        )
        print(content)
        
        # Disconnect
        await client.disconnect()

# Run the example
asyncio.run(example())
```

### Using Async Context Manager

```python
async def example_with_context():
    async with SimpleAWSDocsMCPClient() as client:
        if await client.connect():
            result = await client.search_documentation("Lambda functions")
            print(result)
        # Automatic cleanup on exit
```

## Available Commands

### Search Documentation
- **Command**: `search <query>`
- **Options**:
  - `--service <service_name>`: Filter by AWS service
  - `--limit <number>`: Maximum results to return
  - `--json`: Output raw JSON response

### Read Documentation
- **Command**: `read <url>`
- **Options**:
  - `--max-length <chars>`: Maximum characters to return
  - `--start-index <index>`: Starting character position

### List Tools
- **Command**: `tools`
- Lists all available MCP tools with descriptions

## Features

- **Simple Interface**: Easy-to-use CLI and Python API
- **Async Support**: Built with asyncio for efficient I/O operations
- **Error Handling**: Comprehensive error handling and logging
- **Flexible Output**: Both human-readable and JSON output formats
- **Pagination Support**: Handle large documents with start_index parameter

## Files

- **`simple_mcp_client.py`** - Core MCP client implementation
- **`aws_docs_client.py`** - CLI interface (recommended for most users)
- **`mcp_client.py`** - Alternative implementation using MCP library
- **`.kiro/settings/mcp.json`** - MCP server configuration

## Troubleshooting

1. **Connection Issues**: Make sure `uvx` is installed and available in your PATH
2. **Server Not Found**: The AWS Documentation MCP server will be downloaded automatically on first use
3. **Permission Errors**: Ensure you have proper permissions to run `uvx` commands
4. **JSON Parse Errors**: The server may return non-JSON responses; check error logs

## Example Output

```bash
$ python aws_docs_client.py search "S3 bucket policies"
Found 10 results for 'S3 bucket policies':

1. Bucket policies for Amazon S3 - Amazon Simple Storage Service
   URL: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html
   Context: Manage access permissions, object ownership, and policies for S3 buckets...

2. Examples of Amazon S3 bucket policies - Amazon Simple Storage Service
   URL: https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-bucket-policies.html
   Context: This policy manages access to S3 objects, requiring encryption, MFA...
```