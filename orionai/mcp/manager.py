"""
MCP Manager
===========

Manages MCP servers, their lifecycle, and provides high-level interface
for OrionAI to interact with MCP capabilities.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .client import SyncMCPClient, MCPServerConfig, MCPTool, MCPResource

logger = logging.getLogger(__name__)


class MCPManager:
    """
    High-level manager for MCP functionality in OrionAI.
    
    Handles server lifecycle, configuration persistence, and provides
    a unified interface for MCP capabilities.
    """
    
    def __init__(self, config_dir: Path):
        """
        Initialize MCP Manager.
        
        Args:
            config_dir: Directory for storing MCP configurations
        """
        self.config_dir = config_dir / "mcp"
        self.config_dir.mkdir(exist_ok=True)
        
        self.servers_config_file = self.config_dir / "servers.json"
        self.client = SyncMCPClient()
        self._server_configs: Dict[str, MCPServerConfig] = {}
        
        # Load existing configurations
        self.load_server_configs()
        
        # Add built-in servers if no servers are configured
        self._ensure_default_servers()
    
    def load_server_configs(self):
        """Load server configurations from file."""
        if not self.servers_config_file.exists():
            return
        
        try:
            with open(self.servers_config_file, 'r') as f:
                data = json.load(f)
            
            for server_data in data.get('servers', []):
                config = MCPServerConfig(
                    name=server_data['name'],
                    command=server_data['command'],
                    args=server_data.get('args', []),
                    env=server_data.get('env', {}),
                    working_directory=server_data.get('working_directory'),
                    description=server_data.get('description')
                )
                self._server_configs[config.name] = config
                
        except Exception as e:
            logger.error(f"Failed to load server configs: {e}")
    
    def save_server_configs(self):
        """Save server configurations to file."""
        try:
            data = {
                'servers': [
                    {
                        'name': config.name,
                        'command': config.command,
                        'args': config.args or [],
                        'env': config.env or {},
                        'working_directory': config.working_directory,
                        'description': config.description
                    }
                    for config in self._server_configs.values()
                ]
            }
            
            with open(self.servers_config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save server configs: {e}")
    
    def _ensure_default_servers(self):
        """Ensure default built-in servers are added if no servers exist."""
        if not self._server_configs:
            # Add built-in calculator server using the new implementation
            import sys
            python_exe = sys.executable
            
            self.add_server(
                name="calculator",
                command=[python_exe, "-m", "orionai.mcp.servers.calculator"],
                description="Built-in calculator with mathematical operations (sin, cos, log, sqrt, etc.)"
            )
            
            logger.info("Added default calculator MCP server")
    
    def add_server(self, name: str, command: List[str], args: List[str] = None,
                   env: Dict[str, str] = None, working_directory: str = None,
                   description: str = None) -> bool:
        """
        Add a new MCP server configuration.
        
        Args:
            name: Server name
            command: Command to start the server
            args: Additional arguments
            env: Environment variables
            working_directory: Working directory
            description: Server description
            
        Returns:
            True if added successfully
        """
        if name in self._server_configs:
            logger.warning(f"Server '{name}' already exists")
            return False
        
        config = MCPServerConfig(
            name=name,
            command=command,
            args=args or [],
            env=env or {},
            working_directory=working_directory,
            description=description
        )
        
        self._server_configs[name] = config
        self.save_server_configs()
        
        logger.info(f"Added MCP server: {name}")
        return True
    
    def remove_server(self, name: str) -> bool:
        """
        Remove an MCP server configuration.
        
        Args:
            name: Server name to remove
            
        Returns:
            True if removed successfully
        """
        if name not in self._server_configs:
            return False
        
        # Disconnect if connected
        self.disconnect_server(name)
        
        del self._server_configs[name]
        self.save_server_configs()
        
        logger.info(f"Removed MCP server: {name}")
        return True
    
    def list_configured_servers(self) -> List[Dict[str, Any]]:
        """
        List all configured servers.
        
        Returns:
            List of server information
        """
        servers = []
        for config in self._server_configs.values():
            server_info = {
                'name': config.name,
                'command': ' '.join(config.command),
                'description': config.description or 'No description',
                'connected': config.name in self.client.servers
            }
            servers.append(server_info)
        
        return servers
    
    def connect_server(self, name: str) -> bool:
        """
        Connect to a configured MCP server.
        
        Args:
            name: Server name to connect
            
        Returns:
            True if connection successful
        """
        if name not in self._server_configs:
            logger.error(f"Server '{name}' not configured")
            return False
        
        config = self._server_configs[name]
        
        try:
            success = self.client.connect_server(config)
            if success:
                logger.info(f"Connected to MCP server: {name}")
            return success
        except Exception as e:
            logger.error(f"Failed to connect to server {name}: {e}")
            return False
    
    def disconnect_server(self, name: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            name: Server name to disconnect
            
        Returns:
            True if disconnection successful
        """
        try:
            success = self.client.disconnect_server(name)
            if success:
                logger.info(f"Disconnected from MCP server: {name}")
            return success
        except Exception as e:
            logger.error(f"Failed to disconnect from server {name}: {e}")
            return False
    
    def connect_all_servers(self) -> Dict[str, bool]:
        """
        Connect to all configured servers.
        
        Returns:
            Dictionary mapping server names to connection success
        """
        results = {}
        for name in self._server_configs:
            results[name] = self.connect_server(name)
        return results
    
    def disconnect_all_servers(self):
        """Disconnect from all servers."""
        self.client.close_all()
    
    def get_available_tools(self, server_name: str = None) -> List[Dict[str, Any]]:
        """
        Get available MCP tools.
        
        Args:
            server_name: Optional server name to filter tools
            
        Returns:
            List of tool information
        """
        tools = self.client.list_tools(server_name)
        
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'server': tool.server_name,
                'input_schema': tool.input_schema
            }
            for tool in tools
        ]
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        try:
            return self.client.call_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise
    
    def get_available_resources(self, server_name: str = None) -> List[Dict[str, Any]]:
        """
        Get available MCP resources.
        
        Args:
            server_name: Optional server name to filter resources
            
        Returns:
            List of resource information
        """
        resources = self.client.list_resources(server_name)
        
        return [
            {
                'uri': resource.uri,
                'name': resource.name,
                'description': resource.description or 'No description',
                'mime_type': resource.mime_type
            }
            for resource in resources
        ]
    
    def read_resource(self, uri: str) -> Any:
        """
        Read an MCP resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        try:
            return self.client.read_resource(uri)
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            raise
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all servers.
        
        Returns:
            Dictionary mapping server names to status info
        """
        status = {}
        
        for name, config in self._server_configs.items():
            is_connected = name in self.client.servers
            tools_count = len([t for t in self.client.tools.values() 
                             if t.server_name == name])
            resources_count = len([r for r in self.client.resources.values() 
                                 if r.uri.startswith(f"{name}://")])
            
            status[name] = {
                'connected': is_connected,
                'description': config.description or 'No description',
                'tools_count': tools_count,
                'resources_count': resources_count,
                'command': ' '.join(config.command)
            }
        
        return status
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        Search available tools by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tools
        """
        query_lower = query.lower()
        tools = self.get_available_tools()
        
        matching_tools = []
        for tool in tools:
            if (query_lower in tool['name'].lower() or 
                query_lower in tool['description'].lower()):
                matching_tools.append(tool)
        
        return matching_tools
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information or None if not found
        """
        if tool_name not in self.client.tools:
            return None
        
        tool = self.client.tools[tool_name]
        return {
            'name': tool.name,
            'description': tool.description,
            'server': tool.server_name,
            'input_schema': tool.input_schema,
            'available': tool.server_name in self.client.servers
        }
