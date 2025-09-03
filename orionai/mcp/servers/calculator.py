"""
Simple Calculator MCP Server Example
===================================

A basic MCP server that provides calculator functionality.
This is a demonstration server included with OrionAI.
"""

import asyncio
import json
import sys
import math
from typing import Any, Dict


class CalculatorMCPServer:
    """Simple calculator MCP server."""
    
    def __init__(self):
        self.tools = [
            {
                "name": "calculate",
                "description": "Perform mathematical calculations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            },
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "multiply",
                "description": "Multiply two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
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
                            "name": "calculator",
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
            
            elif method == 'resources/list':
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "resources": []
                    }
                }
            
            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                if tool_name == 'calculate':
                    result = self._calculate(arguments.get('expression', ''))
                elif tool_name == 'add':
                    result = self._add(arguments.get('a', 0), arguments.get('b', 0))
                elif tool_name == 'multiply':
                    result = self._multiply(arguments.get('a', 0), arguments.get('b', 0))
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
    
    def _calculate(self, expression: str) -> float:
        """Safely evaluate mathematical expression."""
        # Simple safe evaluation - only allow basic math operations
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({"abs": abs, "round": round})
        
        # Remove any dangerous functions
        dangerous = ['import', 'exec', 'eval', 'open', 'input', '__']
        for danger in dangerous:
            if danger in expression:
                raise ValueError(f"Dangerous operation not allowed: {danger}")
        
        try:
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return float(result)
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")
    
    def _add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return float(a) + float(b)
    
    def _multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return float(a) * float(b)


async def main():
    """Main server loop."""
    server = CalculatorMCPServer()
    
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
