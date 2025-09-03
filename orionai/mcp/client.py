"""
MCP Client Implementation
========================

Handles communication with MCP servers using the Model Context Protocol.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


@dataclass
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: List[str]
    args: List[str] = None
    env: Dict[str, str] = None
    working_directory: Optional[str] = None
    description: Optional[str] = None


class MCPClient:
    """
    MCP Client for communicating with MCP servers.
    
    This implements the Model Context Protocol client-side functionality
    to connect to and interact with MCP servers.
    """
    
    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self._message_id = 0
    
    def _next_message_id(self) -> str:
        """Generate next message ID."""
        self._message_id += 1
        return str(self._message_id)
    
    async def connect_server(self, config: MCPServerConfig) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            config: Server configuration
            
        Returns:
            True if connection successful
        """
        try:
            # Build command
            cmd = config.command.copy()
            if config.args:
                cmd.extend(config.args)
            
            # Set up environment
            env = None
            if config.env:
                env = dict(os.environ)
                env.update(config.env)
            
            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=config.working_directory
            )
            
            # Store server info
            self.servers[config.name] = {
                'config': config,
                'process': process,
                'connected': True
            }
            
            # Initialize the connection
            await self._initialize_server(config.name)
            
            # Get server capabilities
            await self._get_server_capabilities(config.name)
            
            logger.info(f"Connected to MCP server: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {config.name}: {e}")
            return False
    
    async def disconnect_server(self, server_name: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            server_name: Name of the server to disconnect
            
        Returns:
            True if disconnection successful
        """
        if server_name not in self.servers:
            return False
        
        try:
            server_info = self.servers[server_name]
            process = server_info['process']
            
            if process.returncode is None:
                process.terminate()
                await process.wait()
            
            # Remove server tools and resources
            self._remove_server_tools(server_name)
            self._remove_server_resources(server_name)
            
            del self.servers[server_name]
            logger.info(f"Disconnected from MCP server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from server {server_name}: {e}")
            return False
    
    async def list_tools(self, server_name: Optional[str] = None) -> List[MCPTool]:
        """
        List available tools.
        
        Args:
            server_name: Optional server name to filter tools
            
        Returns:
            List of available tools
        """
        if server_name:
            return [tool for tool in self.tools.values() 
                   if tool.server_name == server_name]
        return list(self.tools.values())
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        server_name = tool.server_name
        
        if server_name not in self.servers:
            raise ValueError(f"Server '{server_name}' not connected")
        
        message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        return await self._send_message(server_name, message)
    
    async def list_resources(self, server_name: Optional[str] = None) -> List[MCPResource]:
        """
        List available resources.
        
        Args:
            server_name: Optional server name to filter resources
            
        Returns:
            List of available resources
        """
        if server_name:
            return [resource for resource in self.resources.values() 
                   if resource.uri.startswith(f"{server_name}://")]
        return list(self.resources.values())
    
    async def read_resource(self, uri: str) -> Any:
        """
        Read a resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        # Extract server name from URI
        if "://" not in uri:
            raise ValueError(f"Invalid resource URI: {uri}")
        
        server_name = uri.split("://")[0]
        
        if server_name not in self.servers:
            raise ValueError(f"Server '{server_name}' not connected")
        
        message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }
        
        return await self._send_message(server_name, message)
    
    async def _initialize_server(self, server_name: str):
        """Initialize connection with server."""
        message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "clientInfo": {
                    "name": "OrionAI",
                    "version": "1.0.0"
                }
            }
        }
        
        await self._send_message(server_name, message)
    
    async def _get_server_capabilities(self, server_name: str):
        """Get server capabilities and update tools/resources."""
        # Get tools
        tools_message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "tools/list"
        }
        
        try:
            tools_response = await self._send_message(server_name, tools_message)
            if tools_response and "tools" in tools_response:
                for tool_data in tools_response["tools"]:
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_name=server_name
                    )
                    self.tools[tool.name] = tool
        except Exception as e:
            logger.warning(f"Failed to get tools from {server_name}: {e}")
        
        # Get resources
        resources_message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "resources/list"
        }
        
        try:
            resources_response = await self._send_message(server_name, resources_message)
            if resources_response and "resources" in resources_response:
                for resource_data in resources_response["resources"]:
                    resource = MCPResource(
                        uri=resource_data["uri"],
                        name=resource_data.get("name", ""),
                        description=resource_data.get("description"),
                        mime_type=resource_data.get("mimeType")
                    )
                    self.resources[resource.uri] = resource
        except Exception as e:
            logger.warning(f"Failed to get resources from {server_name}: {e}")
    
    async def _send_message(self, server_name: str, message: Dict[str, Any]) -> Any:
        """
        Send a message to an MCP server and wait for response.
        
        Args:
            server_name: Target server name
            message: JSON-RPC message
            
        Returns:
            Response data
        """
        if server_name not in self.servers:
            raise ValueError(f"Server '{server_name}' not connected")
        
        server_info = self.servers[server_name]
        process = server_info['process']
        
        try:
            # Send message
            message_str = json.dumps(message) + "\n"
            process.stdin.write(message_str.encode())
            await process.stdin.drain()
            
            # Read response
            response_line = await process.stdout.readline()
            if not response_line:
                raise Exception("No response from server")
            
            response = json.loads(response_line.decode().strip())
            
            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise Exception(f"Server error: {error.get('message', 'Unknown error')}")
            
            return response.get("result")
            
        except Exception as e:
            logger.error(f"Communication error with server {server_name}: {e}")
            raise
    
    def _remove_server_tools(self, server_name: str):
        """Remove tools from a disconnected server."""
        tools_to_remove = [
            name for name, tool in self.tools.items()
            if tool.server_name == server_name
        ]
        for tool_name in tools_to_remove:
            del self.tools[tool_name]
    
    def _remove_server_resources(self, server_name: str):
        """Remove resources from a disconnected server."""
        resources_to_remove = [
            uri for uri in self.resources.keys()
            if uri.startswith(f"{server_name}://")
        ]
        for uri in resources_to_remove:
            del self.resources[uri]
    
    async def close_all(self):
        """Close all server connections."""
        server_names = list(self.servers.keys())
        for server_name in server_names:
            await self.disconnect_server(server_name)


# Synchronous wrapper for easier CLI usage
class SyncMCPClient:
    """Synchronous wrapper for MCPClient."""
    
    def __init__(self):
        self._client = MCPClient()
        self._loop = None
    
    def _ensure_loop(self):
        """Ensure event loop is running."""
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        self._ensure_loop()
        if self._loop.is_running():
            # If loop is already running, use asyncio.create_task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return self._loop.run_until_complete(coro)
    
    def connect_server(self, config: MCPServerConfig) -> bool:
        """Connect to an MCP server (sync)."""
        return self._run_async(self._client.connect_server(config))
    
    def disconnect_server(self, server_name: str) -> bool:
        """Disconnect from an MCP server (sync)."""
        return self._run_async(self._client.disconnect_server(server_name))
    
    def list_tools(self, server_name: Optional[str] = None) -> List[MCPTool]:
        """List available tools (sync)."""
        return self._run_async(self._client.list_tools(server_name))
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool (sync)."""
        return self._run_async(self._client.call_tool(tool_name, arguments))
    
    def list_resources(self, server_name: Optional[str] = None) -> List[MCPResource]:
        """List available resources (sync)."""
        return self._run_async(self._client.list_resources(server_name))
    
    def read_resource(self, uri: str) -> Any:
        """Read a resource (sync)."""
        return self._run_async(self._client.read_resource(uri))
    
    def close_all(self):
        """Close all server connections (sync)."""
        return self._run_async(self._client.close_all())
    
    @property
    def tools(self) -> Dict[str, MCPTool]:
        """Get available tools."""
        return self._client.tools
    
    @property
    def resources(self) -> Dict[str, MCPResource]:
        """Get available resources."""
        return self._client.resources
    
    @property
    def servers(self) -> Dict[str, Dict[str, Any]]:
        """Get connected servers."""
        return self._client.servers
