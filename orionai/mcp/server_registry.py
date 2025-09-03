"""
MCP Server Registry
==================

Registry of common MCP servers with their configurations.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ServerTemplate:
    """Template for MCP server configuration."""
    name: str
    description: str
    command: List[str]
    args: List[str] = None
    env: Dict[str, str] = None
    requirements: List[str] = None
    install_instructions: str = None


class MCPServerRegistry:
    """Registry of common MCP servers."""
    
    def __init__(self):
        self._templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, ServerTemplate]:
        """Initialize built-in server templates."""
        templates = {}
        
        # Built-in OrionAI MCP Servers
        orionai_path = sys.modules['orionai'].__file__
        orionai_dir = str(Path(orionai_path).parent)
        
        templates['calculator-builtin'] = ServerTemplate(
            name='calculator-builtin',
            description='Built-in calculator with basic mathematical operations',
            command=[sys.executable, '-m', 'orionai.mcp.servers.calculator'],
            requirements=[],
            install_instructions='Built-in server - no installation needed'
        )
        
        templates['datetime-builtin'] = ServerTemplate(
            name='datetime-builtin', 
            description='Built-in date and time operations',
            command=[sys.executable, '-m', 'orionai.mcp.servers.datetime'],
            requirements=[],
            install_instructions='Built-in server - no installation needed'
        )
        
        # File System MCP Server
        templates['filesystem'] = ServerTemplate(
            name='filesystem',
            description='Provides file system operations like reading, writing, and listing files',
            command=[sys.executable, '-m', 'mcp_server_filesystem'],
            requirements=['mcp-server-filesystem'],
            install_instructions='pip install mcp-server-filesystem'
        )
        
        # Git MCP Server
        templates['git'] = ServerTemplate(
            name='git',
            description='Git repository operations and version control',
            command=[sys.executable, '-m', 'mcp_server_git'],
            requirements=['mcp-server-git'],
            install_instructions='pip install mcp-server-git'
        )
        
        # Database MCP Server
        templates['database'] = ServerTemplate(
            name='database',
            description='Database operations and SQL queries',
            command=[sys.executable, '-m', 'mcp_server_database'],
            requirements=['mcp-server-database'],
            install_instructions='pip install mcp-server-database'
        )
        
        # Web Search MCP Server
        templates['web-search'] = ServerTemplate(
            name='web-search',
            description='Web search capabilities using various search engines',
            command=[sys.executable, '-m', 'mcp_server_web_search'],
            requirements=['mcp-server-web-search'],
            install_instructions='pip install mcp-server-web-search'
        )
        
        # Weather MCP Server
        templates['weather'] = ServerTemplate(
            name='weather',
            description='Get weather information and forecasts',
            command=[sys.executable, '-m', 'mcp_server_weather'],
            requirements=['mcp-server-weather'],
            install_instructions='pip install mcp-server-weather'
        )
        
        # Calculator MCP Server
        templates['calculator'] = ServerTemplate(
            name='calculator',
            description='Mathematical calculations and expressions',
            command=[sys.executable, '-m', 'mcp_server_calculator'],
            requirements=['mcp-server-calculator'],
            install_instructions='pip install mcp-server-calculator'
        )
        
        # Time/Date MCP Server
        templates['datetime'] = ServerTemplate(
            name='datetime',
            description='Date and time operations, timezone conversions',
            command=[sys.executable, '-m', 'mcp_server_datetime'],
            requirements=['mcp-server-datetime'],
            install_instructions='pip install mcp-server-datetime'
        )
        
        # HTTP MCP Server
        templates['http'] = ServerTemplate(
            name='http',
            description='HTTP requests and API interactions',
            command=[sys.executable, '-m', 'mcp_server_http'],
            requirements=['mcp-server-http'],
            install_instructions='pip install mcp-server-http'
        )
        
        # JSON MCP Server
        templates['json'] = ServerTemplate(
            name='json',
            description='JSON processing and manipulation',
            command=[sys.executable, '-m', 'mcp_server_json'],
            requirements=['mcp-server-json'],
            install_instructions='pip install mcp-server-json'
        )
        
        # System Info MCP Server
        templates['system'] = ServerTemplate(
            name='system',
            description='System information and monitoring',
            command=[sys.executable, '-m', 'mcp_server_system'],
            requirements=['mcp-server-system'],
            install_instructions='pip install mcp-server-system'
        )
        
        # Memory MCP Server (for persistent storage)
        templates['memory'] = ServerTemplate(
            name='memory',
            description='Persistent memory and note-taking',
            command=[sys.executable, '-m', 'mcp_server_memory'],
            requirements=['mcp-server-memory'],
            install_instructions='pip install mcp-server-memory'
        )
        
        # Code Execution MCP Server
        templates['code'] = ServerTemplate(
            name='code',
            description='Safe code execution in sandboxed environment',
            command=[sys.executable, '-m', 'mcp_server_code'],
            requirements=['mcp-server-code'],
            install_instructions='pip install mcp-server-code'
        )
        
        return templates
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available server templates.
        
        Returns:
            List of template information
        """
        return [
            {
                'name': template.name,
                'description': template.description,
                'requirements': template.requirements or [],
                'install_instructions': template.install_instructions
            }
            for template in self._templates.values()
        ]
    
    def get_template(self, name: str) -> ServerTemplate:
        """
        Get a server template by name.
        
        Args:
            name: Template name
            
        Returns:
            Server template
            
        Raises:
            KeyError: If template not found
        """
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found")
        
        return self._templates[name]
    
    def search_templates(self, query: str) -> List[Dict[str, Any]]:
        """
        Search templates by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        matching = []
        
        for template in self._templates.values():
            if (query_lower in template.name.lower() or 
                query_lower in template.description.lower()):
                matching.append({
                    'name': template.name,
                    'description': template.description,
                    'requirements': template.requirements or [],
                    'install_instructions': template.install_instructions
                })
        
        return matching
    
    def get_categories(self) -> Dict[str, List[str]]:
        """
        Get templates organized by categories.
        
        Returns:
            Dictionary mapping categories to template names
        """
        categories = {
            'Built-in': ['calculator-builtin', 'datetime-builtin'],
            'File Operations': ['filesystem', 'git'],
            'Data & Database': ['database', 'json'],
            'Web & Network': ['web-search', 'http'],
            'System & Utilities': ['system', 'calculator', 'datetime'],
            'Weather & Information': ['weather'],
            'Development': ['code', 'memory']
        }
        
        return categories
    
    def add_custom_template(self, template: ServerTemplate):
        """
        Add a custom server template.
        
        Args:
            template: Custom server template
        """
        self._templates[template.name] = template
    
    def remove_template(self, name: str) -> bool:
        """
        Remove a template.
        
        Args:
            name: Template name
            
        Returns:
            True if removed successfully
        """
        if name in self._templates:
            del self._templates[name]
            return True
        return False
