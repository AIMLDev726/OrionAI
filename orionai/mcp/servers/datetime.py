"""
Date and Time MCP Server Example
===============================

A basic MCP server that provides date and time functionality.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict
import time


class DateTimeMCPServer:
    """Date and time MCP server."""
    
    def __init__(self):
        self.tools = [
            {
                "name": "current_time",
                "description": "Get the current date and time",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "Timezone (optional, defaults to UTC)",
                            "default": "UTC"
                        },
                        "format": {
                            "type": "string",
                            "description": "Format string (optional, defaults to ISO format)",
                            "default": "%Y-%m-%d %H:%M:%S"
                        }
                    }
                }
            },
            {
                "name": "timestamp",
                "description": "Get current Unix timestamp",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "format_date",
                "description": "Format a given timestamp",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "number",
                            "description": "Unix timestamp to format"
                        },
                        "format": {
                            "type": "string",
                            "description": "Format string",
                            "default": "%Y-%m-%d %H:%M:%S"
                        }
                    },
                    "required": ["timestamp"]
                }
            }
        ]
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP message."""
        method = message.get('method')
        params = message.get('params', {})
        message_id = message.get('id')
        
        try:
            if method == 'initialize':
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "datetime",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == 'tools/list':
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "tools": self.tools
                    }
                }
            
            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                if tool_name == 'current_time':
                    result = self._current_time(
                        arguments.get('timezone', 'UTC'),
                        arguments.get('format', '%Y-%m-%d %H:%M:%S')
                    )
                elif tool_name == 'timestamp':
                    result = self._timestamp()
                elif tool_name == 'format_date':
                    result = self._format_date(
                        arguments.get('timestamp'),
                        arguments.get('format', '%Y-%m-%d %H:%M:%S')
                    )
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    def _current_time(self, timezone_str: str = 'UTC', format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
        """Get current time."""
        if timezone_str == 'UTC':
            dt = datetime.now(timezone.utc)
        else:
            # For simplicity, just use UTC for now
            dt = datetime.now(timezone.utc)
        
        return dt.strftime(format_str)
    
    def _timestamp(self) -> float:
        """Get current Unix timestamp."""
        return time.time()
    
    def _format_date(self, timestamp: float, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
        """Format a timestamp."""
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime(format_str)


async def main():
    """Main server loop."""
    server = DateTimeMCPServer()
    
    # Read messages from stdin and send responses to stdout
    while True:
        try:
            line = input()
            if not line.strip():
                continue
                
            message = json.loads(line)
            response = await server.handle_message(message)
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except EOFError:
            break
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
