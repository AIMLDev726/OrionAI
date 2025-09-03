# MCP (Model Context Protocol) Integration

OrionAI now includes full support for the Model Context Protocol (MCP), allowing the LLM to access external tools and services for enhanced functionality.

## What is MCP?

Model Context Protocol (MCP) is a standard for connecting language models to external tools and data sources. It allows LLMs to:

- Perform calculations
- Get current date/time information
- Access file systems
- Query databases
- Search the web
- Get weather information
- Execute code safely
- And much more through various MCP servers

## Features

### 🔌 MCP Server Management
- Add, remove, and configure MCP servers
- Built-in servers for common functionality
- Support for third-party MCP servers
- Auto-connect to servers on startup
- Real-time server status monitoring

### 🛠️ Tool Discovery and Usage
- Automatic tool discovery from connected servers
- Browse tools by category
- Search tools by name or description
- Interactive tool testing
- Schema validation for tool arguments

### 🤖 LLM Integration
- Seamless tool access during conversations
- Automatic tool execution when LLM requests it
- Context-aware tool suggestions
- Error handling and retry logic

## Getting Started

### 1. Enable MCP in Settings

1. Run OrionAI CLI: `python -m orionai.cli.main`
2. Go to Settings (option 5)
3. Enable MCP features
4. Set auto-connect if desired

### 2. Add MCP Servers

1. From main menu, select "MCP (Model Context Protocol)" (option 4)
2. Go to "Manage MCP Servers" (option 1)
3. Choose "Add New Server" (option 1)
4. Select from built-in templates or add custom servers

### 3. Built-in Servers

OrionAI includes these built-in MCP servers:

#### Calculator Server
- **Name**: `calculator-builtin`
- **Tools**: `calculate`, `add`, `multiply`
- **Usage**: Mathematical calculations and basic arithmetic

#### DateTime Server  
- **Name**: `datetime-builtin`
- **Tools**: `current_time`, `timestamp`, `format_date`
- **Usage**: Date and time operations

### 4. Installing Additional Servers

Many third-party MCP servers are available. Install them via pip:

```bash
# File system operations
pip install mcp-server-filesystem

# Weather information  
pip install mcp-server-weather

# Web search
pip install mcp-server-web-search

# Git operations
pip install mcp-server-git

# Database operations
pip install mcp-server-database
```

Then add them through the MCP interface using the server templates.

## Using MCP Tools in Chat

Once MCP servers are connected, the LLM can automatically use available tools. For example:

**User**: "What's 2 + 2 * 3?"

**LLM Response**: 
```json
{
  "action": "use_tool",
  "tool_name": "calculate", 
  "arguments": {"expression": "2 + 2 * 3"},
  "reasoning": "I'll use the calculator to evaluate this mathematical expression"
}
```

**Result**: 
🔧 I'll use the calculator to evaluate this mathematical expression

🛠️ Executed tool: **calculate**
📊 Arguments: `{"expression": "2 + 2 * 3"}`
✅ Result:
```
8.0
```

**User**: "What time is it?"

**LLM Response**:
```json
{
  "action": "use_tool",
  "tool_name": "current_time",
  "arguments": {},
  "reasoning": "I'll get the current date and time"
}
```

## MCP Server Configuration

### Server Configuration Format

```json
{
  "name": "server-name",
  "command": ["python", "-m", "server_module"],
  "args": ["--option", "value"],
  "env": {"API_KEY": "your-key"},
  "working_directory": "/path/to/workdir",
  "description": "Server description"
}
```

### Built-in Server Templates

The MCP interface includes templates for common servers:

| Category | Servers |
|----------|---------|
| **Built-in** | calculator-builtin, datetime-builtin |
| **File Operations** | filesystem, git |
| **Data & Database** | database, json |
| **Web & Network** | web-search, http |
| **System & Utilities** | system, calculator, datetime |
| **Weather & Information** | weather |
| **Development** | code, memory |

## CLI Interface

### Main MCP Menu
- `1` - Manage MCP Servers
- `2` - Browse & Use Tools  
- `3` - Install Server Templates
- `4` - Server Status & Information
- `5` - Test Tools
- `6` - MCP Settings

### Server Management
- Add/remove servers
- Connect/disconnect servers
- View server details
- Bulk operations

### Tool Browser
- List all available tools
- Browse by category
- Search tools
- Interactive tool usage
- View tool schemas

## Configuration Files

MCP configuration is stored in:
- `~/.orionai/config.yaml` - Main configuration
- `~/.orionai/mcp/servers.json` - Server configurations

## Troubleshooting

### Server Won't Connect
1. Check server installation: `pip list | grep mcp-server`
2. Verify command path in server configuration
3. Check server logs in terminal
4. Ensure required dependencies are installed

### Tool Not Available
1. Verify server is connected: MCP Menu → Server Status
2. Refresh tool list: Reconnect to server
3. Check tool name spelling
4. Verify tool arguments match schema

### Performance Issues
1. Limit number of connected servers
2. Disable auto-connect for unused servers  
3. Check MCP timeout settings
4. Monitor system resources

## Advanced Usage

### Custom MCP Servers

You can create custom MCP servers for specialized functionality:

```python
# custom_server.py
import asyncio
import json
import sys

class CustomMCPServer:
    def __init__(self):
        self.tools = [
            {
                "name": "my_tool",
                "description": "Custom functionality",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    }
                }
            }
        ]
    
    async def handle_message(self, message):
        # Handle MCP protocol messages
        pass

if __name__ == "__main__":
    server = CustomMCPServer()
    # Server main loop
```

### Environment Variables

Set these environment variables for MCP servers that require API keys:

```bash
export OPENWEATHER_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"  
export DATABASE_URL="your-connection-string"
```

## Security Considerations

- MCP servers run as separate processes
- Tool execution is sandboxed where possible
- Validate tool inputs and outputs
- Monitor server resource usage
- Use trusted MCP servers only
- Review server permissions

## Contributing

To add new built-in MCP servers:

1. Create server in `orionai/mcp/servers/`
2. Add to `__init__.py` imports
3. Add template to `server_registry.py`
4. Update documentation
5. Add tests

## Support

For MCP-related issues:

1. Check server status in MCP interface
2. Review configuration files
3. Test individual tools
4. Check OrionAI logs
5. Consult MCP server documentation

## Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [MCP Server Examples](https://github.com/modelcontextprotocol)
- [OrionAI Documentation](./README.md)
