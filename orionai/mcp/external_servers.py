"""
External MCP Servers Registry
Integrates with official MCP registry and external hosted servers
"""

import json
import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

@dataclass
class ExternalMCPServer:
    """Configuration for an external MCP server"""
    name: str
    description: str
    registry_type: str  # npm, pypi, oci
    identifier: str
    version: str
    transport_type: str = "stdio"
    environment_variables: Dict[str, str] = None
    package_arguments: List[Dict] = None
    repository_url: str = ""
    status: str = "active"

class ExternalMCPRegistry:
    """Manages external MCP servers from official registry"""
    
    def __init__(self):
        self.registry_url = "https://registry.modelcontextprotocol.io"
        self.github_registry_url = "https://raw.githubusercontent.com/modelcontextprotocol/registry/main/data/seed.json"
        self.servers_cache = {}
        self.installed_servers = set()
        
        # Popular server categories
        self.featured_servers = {
            # Web Search & Information
            "exa-mcp-server": {
                "category": "search",
                "priority": 1,
                "description": "Web search with Exa API"
            },
            "mcp_tavily": {
                "category": "search", 
                "priority": 2,
                "description": "Tavily search API"
            },
            "firecrawl-mcp": {
                "category": "web",
                "priority": 1,
                "description": "Web scraping with Firecrawl"
            },
            
            # Calculators & Math
            "mcp-solver": {
                "category": "math",
                "priority": 1, 
                "description": "Constraint optimization and solving"
            },
            "mcp_weather_server": {
                "category": "utility",
                "priority": 2,
                "description": "Weather information"
            },
            
            # Development Tools
            "terminal-controller": {
                "category": "development",
                "priority": 1,
                "description": "Terminal command execution"
            },
            "@circleci/mcp-server-circleci": {
                "category": "development", 
                "priority": 2,
                "description": "CircleCI integration"
            },
            
            # Databases
            "mcp-clickhouse": {
                "category": "database",
                "priority": 1,
                "description": "ClickHouse database"
            },
            "@elastic/mcp-server-elasticsearch": {
                "category": "database",
                "priority": 2,
                "description": "Elasticsearch integration"
            },
            "chroma-mcp": {
                "category": "database",
                "priority": 1,
                "description": "Chroma vector database"
            },
            
            # Social & Communication
            "@enescinar/twitter-mcp": {
                "category": "social",
                "priority": 1,
                "description": "Twitter integration"
            },
            "spotify-mcp": {
                "category": "media",
                "priority": 1,
                "description": "Spotify integration"
            },
            
            # Productivity
            "@abhiz123/todoist-mcp-server": {
                "category": "productivity",
                "priority": 1,
                "description": "Todoist task management"
            },
            
            # Finance & Business
            "mcp-stripe": {
                "category": "finance",
                "priority": 1,
                "description": "Stripe payments"
            },
            
            # File & Cloud
            "mcp-server-box": {
                "category": "storage",
                "priority": 1,
                "description": "Box cloud storage"
            },
            
            # AI & ML
            "arize-phoenix": {
                "category": "ai",
                "priority": 1,
                "description": "AI observability"
            },
        }
    
    async def fetch_registry_servers(self) -> List[Dict]:
        """Fetch servers from official MCP registry"""
        try:
            response = requests.get(self.github_registry_url, timeout=10)
            response.raise_for_status()
            
            servers_data = response.json()
            logger.info(f"Fetched {len(servers_data)} servers from official registry")
            return servers_data
            
        except Exception as e:
            logger.error(f"Failed to fetch registry: {e}")
            return []
    
    def parse_server_config(self, server_data: Dict) -> Optional[ExternalMCPServer]:
        """Parse server data from registry into our format"""
        try:
            if not server_data.get("packages"):
                return None
                
            package = server_data["packages"][0]  # Use first package
            
            return ExternalMCPServer(
                name=server_data["name"],
                description=server_data.get("description", ""),
                registry_type=package["registry_type"],
                identifier=package["identifier"],
                version=package.get("version", "latest"),
                transport_type=package.get("transport_type", "stdio"),
                environment_variables={
                    var["name"]: var.get("description", "")
                    for var in package.get("environment_variables", [])
                },
                package_arguments=package.get("package_arguments", []),
                repository_url=server_data.get("repository", {}).get("url", ""),
                status=server_data.get("status", "active")
            )
            
        except Exception as e:
            logger.error(f"Failed to parse server {server_data.get('name', 'unknown')}: {e}")
            return None
    
    async def load_featured_servers(self) -> List[ExternalMCPServer]:
        """Load featured external servers"""
        registry_servers = await self.fetch_registry_servers()
        featured = []
        
        # Create lookup by identifier
        server_lookup = {}
        for server_data in registry_servers:
            if server_data.get("packages"):
                identifier = server_data["packages"][0]["identifier"]
                server_lookup[identifier] = server_data
                # Also add by name for easier lookup
                server_lookup[server_data["name"]] = server_data
        
        # Find featured servers
        for server_id, config in self.featured_servers.items():
            if server_id in server_lookup:
                server = self.parse_server_config(server_lookup[server_id])
                if server:
                    featured.append(server)
                    logger.info(f"Added featured server: {server.name}")
        
        # Sort by priority
        featured.sort(key=lambda x: self.featured_servers.get(x.identifier, {}).get("priority", 99))
        
        return featured[:50]  # Top 50 servers
    
    async def install_npm_server(self, server: ExternalMCPServer, config_dir: Path) -> bool:
        """Install NPM-based MCP server"""
        try:
            # Create installation directory
            install_dir = config_dir / "external_servers" / server.identifier.replace("/", "_")
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # Create package.json
            package_json = {
                "name": f"orionai-{server.identifier.replace('/', '-')}",
                "version": "1.0.0",
                "dependencies": {
                    server.identifier: server.version
                }
            }
            
            with open(install_dir / "package.json", "w") as f:
                json.dump(package_json, f, indent=2)
            
            # Install via npm
            result = subprocess.run(
                ["npm", "install"],
                cwd=install_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed NPM server: {server.name}")
                return True
            else:
                logger.error(f"NPM install failed for {server.name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install NPM server {server.name}: {e}")
            return False
    
    async def install_pypi_server(self, server: ExternalMCPServer) -> bool:
        """Install PyPI-based MCP server"""
        try:
            # Install via pip
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", f"{server.identifier}=={server.version}"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed PyPI server: {server.name}")
                return True
            else:
                logger.error(f"PyPI install failed for {server.name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install PyPI server {server.name}: {e}")
            return False
    
    def generate_claude_config(self, server: ExternalMCPServer, install_dir: Optional[Path] = None) -> Dict:
        """Generate Claude Desktop configuration for external server"""
        config = {
            "command": self._get_server_command(server, install_dir),
            "args": self._get_server_args(server, install_dir),
            "env": {}
        }
        
        # Add environment variables with placeholders
        if server.environment_variables:
            for env_var, description in server.environment_variables.items():
                config["env"][env_var] = f"${{{env_var}}}"  # Placeholder for user to fill
        
        return config
    
    def _get_server_command(self, server: ExternalMCPServer, install_dir: Optional[Path] = None) -> str:
        """Get the command to run the server"""
        if server.registry_type == "npm":
            if install_dir:
                return "node"
            else:
                return "npx"
        elif server.registry_type == "pypi":
            return sys.executable
        elif server.registry_type == "oci":
            return "docker"
        else:
            return "unknown"
    
    def _get_server_args(self, server: ExternalMCPServer, install_dir: Optional[Path] = None) -> List[str]:
        """Get the arguments to run the server"""
        args = []
        
        if server.registry_type == "npm":
            if install_dir:
                # Run from installed node_modules
                args.extend([
                    str(install_dir / "node_modules" / server.identifier / "index.js")
                ])
            else:
                # Run via npx
                args.extend([server.identifier])
        elif server.registry_type == "pypi":
            # Run python module
            args.extend(["-m", server.identifier])
        elif server.registry_type == "oci":
            # Run docker container
            args.extend(["run", "-i", "--rm", server.identifier])
        
        # Add package arguments if specified
        if server.package_arguments:
            for arg in server.package_arguments:
                if arg["type"] == "named":
                    args.extend([arg["name"], arg.get("value", "")])
                elif arg["type"] == "positional":
                    args.append(arg.get("value", ""))
        
        return args

class ExternalMCPManager:
    """Manages external MCP server configurations"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.registry = ExternalMCPRegistry()
        self.external_config_file = config_dir / "external_servers.json"
        self.claude_config_file = config_dir / "claude_mcp_config.json"
        
        # Ensure directories exist
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "external_servers").mkdir(exist_ok=True)
    
    async def setup_featured_servers(self) -> Dict[str, Any]:
        """Set up featured external MCP servers"""
        logger.info("Setting up featured external MCP servers...")
        
        featured_servers = await self.registry.load_featured_servers()
        setup_results = {
            "total_servers": len(featured_servers),
            "successful_installs": 0,
            "failed_installs": 0,
            "servers": [],
            "claude_config": {}
        }
        
        claude_config = {}
        
        for server in featured_servers:
            try:
                logger.info(f"Setting up server: {server.name}")
                
                # Attempt installation based on type
                install_success = False
                install_dir = None
                
                if server.registry_type == "npm":
                    install_success = await self.registry.install_npm_server(server, self.config_dir)
                    if install_success:
                        install_dir = self.config_dir / "external_servers" / server.identifier.replace("/", "_")
                elif server.registry_type == "pypi":
                    install_success = await self.registry.install_pypi_server(server)
                
                # Generate configuration regardless of install success
                server_config = self.registry.generate_claude_config(server, install_dir)
                
                # Add to Claude config
                claude_config[server.name] = server_config
                
                setup_results["servers"].append({
                    "name": server.name,
                    "description": server.description,
                    "type": server.registry_type,
                    "installed": install_success,
                    "config": server_config
                })
                
                if install_success:
                    setup_results["successful_installs"] += 1
                else:
                    setup_results["failed_installs"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to setup server {server.name}: {e}")
                setup_results["failed_installs"] += 1
        
        # Save configurations
        setup_results["claude_config"] = claude_config
        await self._save_configurations(setup_results)
        
        logger.info(f"Setup complete: {setup_results['successful_installs']} successful, {setup_results['failed_installs']} failed")
        return setup_results
    
    async def _save_configurations(self, setup_results: Dict):
        """Save external server configurations"""
        try:
            # Save external servers config
            with open(self.external_config_file, "w") as f:
                json.dump(setup_results, f, indent=2)
            
            # Save Claude MCP config
            with open(self.claude_config_file, "w") as f:
                json.dump({
                    "mcpServers": setup_results["claude_config"]
                }, f, indent=2)
            
            logger.info(f"Configurations saved to {self.config_dir}")
            
        except Exception as e:
            logger.error(f"Failed to save configurations: {e}")
    
    def get_installation_instructions(self) -> str:
        """Get installation instructions for users"""
        instructions = """
# External MCP Servers Setup Complete!

## Next Steps:

1. **Configure Environment Variables**: 
   - Open the generated config files in your config directory
   - Replace placeholder values like ${API_KEY} with actual API keys
   - Get API keys from respective service providers

2. **Claude Desktop Integration**:
   - Copy contents from 'claude_mcp_config.json' to your Claude Desktop config
   - Location: ~/.claude/claude_desktop_config.json (macOS/Linux) or %APPDATA%\\Claude\\claude_desktop_config.json (Windows)

3. **Popular API Keys Needed**:
   - Exa API: https://exa.ai/ (for web search)
   - Tavily API: https://tavily.com/ (for search)
   - OpenWeatherMap: https://openweathermap.org/api (for weather)
   - Twitter API: https://developer.twitter.com/ (for social)
   - Spotify API: https://developer.spotify.com/ (for music)
   - And many more depending on which servers you want to use

4. **Test the Setup**:
   - Restart Claude Desktop
   - Try asking Claude to search the web or perform calculations
   - The external servers should now be available as tools

## Server Categories Available:
- Web Search & Information Retrieval
- Mathematical Calculations & Solving
- Database Integration (ClickHouse, Elasticsearch, Chroma)
- Development Tools (Terminal, CircleCI)
- Social Media Integration (Twitter, Spotify)
- Productivity Tools (Todoist, Calendar)
- File & Cloud Storage (Box, etc.)
- Financial Services (Stripe)
- AI/ML Observability

Enjoy your enhanced AI assistant with 50+ external capabilities!
        """
        return instructions

# Convenience functions for easy integration
async def setup_external_mcp_servers(config_dir: str = None) -> Dict[str, Any]:
    """Main function to set up external MCP servers"""
    if config_dir is None:
        config_dir = Path.home() / ".orionai" / "mcp"
    else:
        config_dir = Path(config_dir)
    
    manager = ExternalMCPManager(config_dir)
    return await manager.setup_featured_servers()

def get_setup_instructions(config_dir: str = None) -> str:
    """Get setup instructions"""
    if config_dir is None:
        config_dir = Path.home() / ".orionai" / "mcp"
    else:
        config_dir = Path(config_dir)
    
    manager = ExternalMCPManager(config_dir)
    return manager.get_installation_instructions()

if __name__ == "__main__":
    # Example usage
    async def main():
        results = await setup_external_mcp_servers()
        print(f"Setup {results['total_servers']} servers")
        print(f"Successfully installed: {results['successful_installs']}")
        print(f"Failed installs: {results['failed_installs']}")
        print("\n" + get_setup_instructions())
    
    asyncio.run(main())