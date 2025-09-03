"""
MCP Tools Registry
==================

Registry and wrapper for MCP tools to integrate with OrionAI.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from .manager import MCPManager

logger = logging.getLogger(__name__)


@dataclass
class ToolWrapper:
    """Wrapper for MCP tools with additional metadata."""
    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]
    category: str = "general"
    example_usage: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'description': self.description,
            'server_name': self.server_name,
            'input_schema': self.input_schema,
            'category': self.category,
            'example_usage': self.example_usage
        }


class MCPToolRegistry:
    """
    Registry for MCP tools with categorization and enhanced functionality.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        """
        Initialize tool registry.
        
        Args:
            mcp_manager: MCP manager instance
        """
        self.mcp_manager = mcp_manager
        self._tool_categories = self._initialize_categories()
        self._tool_wrappers: Dict[str, ToolWrapper] = {}
        self._refresh_tools()
    
    def _initialize_categories(self) -> Dict[str, List[str]]:
        """Initialize tool categories mapping."""
        return {
            'filesystem': ['read_file', 'write_file', 'list_directory', 'file_info'],
            'git': ['git_status', 'git_log', 'git_diff', 'git_commit'],
            'web': ['search_web', 'fetch_url', 'http_get', 'http_post'],
            'calculation': ['calculate', 'math_eval', 'add', 'multiply'],
            'datetime': ['current_time', 'format_date', 'timezone_convert'],
            'weather': ['get_weather', 'weather_forecast'],
            'system': ['system_info', 'cpu_usage', 'memory_usage'],
            'database': ['query_db', 'execute_sql'],
            'json': ['parse_json', 'format_json', 'json_path'],
            'memory': ['store_note', 'retrieve_note', 'list_notes'],
            'code': ['execute_python', 'lint_code', 'format_code']
        }
    
    def _refresh_tools(self):
        """Refresh tool wrappers from MCP manager."""
        self._tool_wrappers.clear()
        
        tools = self.mcp_manager.get_available_tools()
        for tool_info in tools:
            category = self._categorize_tool(tool_info['name'])
            
            wrapper = ToolWrapper(
                name=tool_info['name'],
                description=tool_info['description'],
                server_name=tool_info['server'],
                input_schema=tool_info['input_schema'],
                category=category,
                example_usage=self._generate_example_usage(tool_info)
            )
            
            self._tool_wrappers[wrapper.name] = wrapper
    
    def _categorize_tool(self, tool_name: str) -> str:
        """
        Categorize a tool based on its name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Category name
        """
        tool_name_lower = tool_name.lower()
        
        for category, tool_patterns in self._tool_categories.items():
            for pattern in tool_patterns:
                if pattern.lower() in tool_name_lower:
                    return category
        
        # Try to infer from common patterns
        if any(keyword in tool_name_lower for keyword in ['file', 'read', 'write', 'directory']):
            return 'filesystem'
        elif any(keyword in tool_name_lower for keyword in ['git', 'commit', 'branch']):
            return 'git'
        elif any(keyword in tool_name_lower for keyword in ['web', 'http', 'search', 'url']):
            return 'web'
        elif any(keyword in tool_name_lower for keyword in ['calc', 'math', 'add', 'multiply']):
            return 'calculation'
        elif any(keyword in tool_name_lower for keyword in ['time', 'date', 'timezone']):
            return 'datetime'
        elif any(keyword in tool_name_lower for keyword in ['weather', 'forecast', 'climate']):
            return 'weather'
        elif any(keyword in tool_name_lower for keyword in ['system', 'cpu', 'memory', 'disk']):
            return 'system'
        elif any(keyword in tool_name_lower for keyword in ['database', 'sql', 'query']):
            return 'database'
        elif any(keyword in tool_name_lower for keyword in ['json', 'parse', 'format']):
            return 'json'
        elif any(keyword in tool_name_lower for keyword in ['note', 'memory', 'store', 'remember']):
            return 'memory'
        elif any(keyword in tool_name_lower for keyword in ['code', 'execute', 'run', 'python']):
            return 'code'
        
        return 'general'
    
    def _generate_example_usage(self, tool_info: Dict[str, Any]) -> str:
        """
        Generate example usage for a tool.
        
        Args:
            tool_info: Tool information
            
        Returns:
            Example usage string
        """
        tool_name = tool_info['name']
        schema = tool_info.get('input_schema', {})
        
        # Extract properties from schema
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Generate example based on tool name and schema
        examples = {
            'read_file': "Read content of a file: read_file(path='/path/to/file.txt')",
            'write_file': "Write content to file: write_file(path='/path/to/file.txt', content='Hello World')",
            'list_directory': "List files in directory: list_directory(path='/path/to/directory')",
            'get_weather': "Get current weather: get_weather(location='New York')",
            'calculate': "Perform calculation: calculate(expression='2 + 2 * 3')",
            'current_time': "Get current time: current_time(timezone='UTC')",
            'search_web': "Search the web: search_web(query='Python programming')",
            'git_status': "Check git status: git_status(repository_path='/path/to/repo')",
            'execute_python': "Execute Python code: execute_python(code='print(\"Hello World\")')"
        }
        
        if tool_name in examples:
            return examples[tool_name]
        
        # Generate generic example based on schema
        if properties:
            example_args = []
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'string')
                if prop_type == 'string':
                    example_args.append(f"{prop_name}='example_value'")
                elif prop_type == 'integer':
                    example_args.append(f"{prop_name}=42")
                elif prop_type == 'boolean':
                    example_args.append(f"{prop_name}=True")
                elif prop_type == 'array':
                    example_args.append(f"{prop_name}=['item1', 'item2']")
                else:
                    example_args.append(f"{prop_name}=value")
            
            args_str = ", ".join(example_args[:3])  # Limit to first 3 args
            return f"{tool_name}({args_str})"
        
        return f"{tool_name}()"
    
    def get_tools_by_category(self, category: str = None) -> List[ToolWrapper]:
        """
        Get tools by category.
        
        Args:
            category: Tool category (optional)
            
        Returns:
            List of tool wrappers
        """
        self._refresh_tools()
        
        if category is None:
            return list(self._tool_wrappers.values())
        
        return [tool for tool in self._tool_wrappers.values() 
                if tool.category == category]
    
    def get_available_categories(self) -> List[str]:
        """
        Get list of available tool categories.
        
        Returns:
            List of category names
        """
        self._refresh_tools()
        categories = set(tool.category for tool in self._tool_wrappers.values())
        return sorted(list(categories))
    
    def search_tools(self, query: str) -> List[ToolWrapper]:
        """
        Search tools by name, description, or category.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tool wrappers
        """
        self._refresh_tools()
        query_lower = query.lower()
        
        matching_tools = []
        for tool in self._tool_wrappers.values():
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower() or
                query_lower in tool.category.lower()):
                matching_tools.append(tool)
        
        return matching_tools
    
    def get_tool(self, name: str) -> Optional[ToolWrapper]:
        """
        Get a specific tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool wrapper or None if not found
        """
        self._refresh_tools()
        return self._tool_wrappers.get(name)
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        return self.mcp_manager.call_tool(name, arguments)
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get the input schema for a tool.
        
        Args:
            name: Tool name
            
        Returns:
            Tool schema or None if not found
        """
        tool = self.get_tool(name)
        return tool.input_schema if tool else None
    
    def validate_tool_arguments(self, name: str, arguments: Dict[str, Any]) -> bool:
        """
        Validate arguments against tool schema.
        
        Args:
            name: Tool name
            arguments: Arguments to validate
            
        Returns:
            True if arguments are valid
        """
        schema = self.get_tool_schema(name)
        if not schema:
            return False
        
        # Basic validation
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Check required fields
        for field in required:
            if field not in arguments:
                return False
        
        # Check field types (basic validation)
        for field, value in arguments.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type == 'string' and not isinstance(value, str):
                    return False
                elif expected_type == 'integer' and not isinstance(value, int):
                    return False
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    return False
                elif expected_type == 'array' and not isinstance(value, list):
                    return False
        
        return True
    
    def get_tools_summary(self) -> Dict[str, Any]:
        """
        Get summary of available tools.
        
        Returns:
            Summary information
        """
        self._refresh_tools()
        
        categories = {}
        for tool in self._tool_wrappers.values():
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(tool.name)
        
        return {
            'total_tools': len(self._tool_wrappers),
            'categories': categories,
            'servers': list(set(tool.server_name for tool in self._tool_wrappers.values()))
        }
