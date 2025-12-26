# LLM Agent with MCP Tools

An intelligent agent that uses OpenAI's LLM to decide which MCP tools to call based on user queries.

## Features

- **AWS Documentation Search**: Search and read AWS documentation
- **Git Operations**: Check status, view logs, see diffs
- **Intelligent Tool Selection**: LLM automatically chooses the right tools
- **Conversation Context**: Maintains conversation history for follow-up questions

## Architecture

```
User Query
    ↓
LLM (GPT-4)
    ↓
Function Calling → Decides which tool(s) to use
    ↓
MCPAgent.execute_tool()
    ↓
├─→ AWSDocsMCPClient (search/read AWS docs)
└─→ GitMCPClient (git operations)
    ↓
Results returned to LLM
    ↓
LLM generates natural language response
    ↓
User receives answer
```

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set OpenAI API key**:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

3. **Ensure uvx is installed** (for MCP servers):
```bash
# Install uv (Python package manager)
pip install uv
```

## Usage

### Interactive Mode (default)

```bash
python llm_agent.py
```

Chat with the agent naturally:
```
You: What's the current status of my git repository?
Agent: [Calls git_status and explains the results]

You: Show me the last 5 commits
Agent: [Calls git_log and summarizes commits]

You: How do I configure S3 bucket policies?
Agent: [Searches AWS docs and provides information]
```

### Demo Mode

```bash
python llm_agent.py demo
```

Runs predefined queries to demonstrate capabilities.

## Available Tools

The agent has access to these tools:

### AWS Documentation Tools
- `search_aws_documentation(search_phrase)` - Search AWS docs
- `read_aws_documentation(url, max_length?)` - Read specific doc page

### Git Tools
- `git_status(repo_path?)` - Get repository status
- `git_log(max_count?, repo_path?)` - View commit history
- `git_diff(cached?, repo_path?)` - See changes

## Example Queries

**Git Operations:**
- "What files have changed in my repository?"
- "Show me the last 10 commits"
- "What's in my staging area?"
- "Show me the diff of unstaged changes"

**AWS Documentation:**
- "How do I set up S3 bucket versioning?"
- "What are Lambda best practices?"
- "Search for DynamoDB pricing information"

**Combined:**
- "Check my git status and then search AWS docs for CodeCommit"

## Commands

- `quit` or `exit` - Exit the agent
- `reset` - Clear conversation history

## Configuration

Edit `llm_agent.py` to customize:

```python
# Change the model
agent = MCPAgent(model="gpt-4o")  # or "gpt-3.5-turbo"

# Adjust max iterations
response = await agent.chat(message, max_iterations=10)
```

## How It Works

1. **User sends a message** to the agent
2. **LLM analyzes** the message and decides which tools to call
3. **Agent executes** the selected MCP tools
4. **Results are sent back** to the LLM
5. **LLM synthesizes** a natural language response
6. **User receives** the final answer

The agent can make multiple tool calls in sequence to answer complex queries.

## Error Handling

- Gracefully handles MCP server connection failures
- Continues working if one MCP server is unavailable
- Provides clear error messages to users
- Prevents infinite loops with max_iterations

## Extending

To add more MCP tools:

1. Create a new client in `unified_mcp_client.py`
2. Add tool definitions to `self.tools` in `MCPAgent.__init__`
3. Add execution logic in `MCPAgent.execute_tool`

Example:
```python
# Add a new MCP client
class WeatherMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            command="uvx",
            args=["weather-mcp-server"],
            client_name="weather-client"
        )
```
