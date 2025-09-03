"""
Interactive MCP Server Manager
Comprehensive menu-driven system for browsing, selecting, and installing external MCP servers
"""

import asyncio
import json
import logging
import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import requests
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns

logger = logging.getLogger(__name__)
console = Console()

def safe_screen_update(clear_screen: bool = False):
    """Safely update screen without causing resize issues"""
    if clear_screen:
        # Only clear if really necessary, use separator otherwise
        try:
            console.clear()
        except:
            # Fallback to separator if clear fails
            console.print("\n" + "="*80 + "\n")
    else:
        console.print("\n" + "="*80 + "\n")

@dataclass
class MCPServerInfo:
    """Complete MCP server information"""
    name: str
    description: str
    registry_type: str  # npm, pypi, oci
    identifier: str
    version: str
    category: str
    priority: int
    transport_type: str = "stdio"
    environment_variables: Dict[str, str] = None
    package_arguments: List[Dict] = None
    repository_url: str = ""
    status: str = "active"
    requires_api_key: bool = False
    api_services: List[str] = None
    installation_notes: str = ""
    
    def __post_init__(self):
        if self.environment_variables is None:
            self.environment_variables = {}
        if self.package_arguments is None:
            self.package_arguments = []
        if self.api_services is None:
            self.api_services = []

class InteractiveMCPManager:
    """Interactive menu-driven MCP server management"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".orionai" / "mcp"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for local clean registry first
        local_clean_registry = self.config_dir / "clean_registry.json"
        if local_clean_registry.exists():
            self.registry_url = f"file://{local_clean_registry.absolute().as_posix()}"
            print("🧹 Using local clean registry (problematic servers removed)")
        else:
            self.registry_url = "https://raw.githubusercontent.com/modelcontextprotocol/registry/main/data/seed.json"
        
        self.all_servers: List[MCPServerInfo] = []
        self.selected_servers: Set[str] = set()
        self.installed_servers: Set[str] = set()
        
        # Load installed servers
        self._load_installed_servers()
        
        # Categories and their priorities
        self.categories = {
            "search": {"name": "🔍 Web Search & Information", "priority": 1},
            "math": {"name": "🔢 Calculators & Math", "priority": 2},
            "development": {"name": "💻 Development Tools", "priority": 3},
            "database": {"name": "🗄️ Database & Storage", "priority": 4},
            "social": {"name": "📱 Social Media", "priority": 5},
            "productivity": {"name": "📋 Productivity & Tasks", "priority": 6},
            "finance": {"name": "💰 Finance & Business", "priority": 7},
            "media": {"name": "🎵 Media & Entertainment", "priority": 8},
            "ai": {"name": "🤖 AI & Machine Learning", "priority": 9},
            "utility": {"name": "🛠️ Utilities", "priority": 10},
            "web": {"name": "🌐 Web Tools", "priority": 11},
            "storage": {"name": "☁️ Cloud Storage", "priority": 12},
            "communication": {"name": "💬 Communication", "priority": 13},
            "other": {"name": "📦 Other Tools", "priority": 99}
        }
    
    def _load_installed_servers(self):
        """Load list of already installed servers"""
        try:
            installed_file = self.config_dir / "installed_servers.json"
            if installed_file.exists():
                with open(installed_file) as f:
                    data = json.load(f)
                    self.installed_servers = set(data.get("installed", []))
        except Exception as e:
            logger.error(f"Failed to load installed servers: {e}")
    
    def _save_installed_servers(self):
        """Save list of installed servers"""
        try:
            installed_file = self.config_dir / "installed_servers.json"
            with open(installed_file, "w") as f:
                json.dump({"installed": list(self.installed_servers)}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save installed servers: {e}")
    
    async def fetch_all_servers(self) -> bool:
        """Fetch all available MCP servers from registry"""
        try:
            with console.status("[bold green]Fetching MCP servers from registry..."):
                if self.registry_url.startswith("file://"):
                    # Load from local file
                    file_path = self.registry_url[7:]  # Remove "file://" prefix
                    with open(file_path, 'r') as f:
                        registry_data = json.load(f)
                else:
                    # Load from URL
                    response = requests.get(self.registry_url, timeout=30)
                    response.raise_for_status()
                    registry_data = response.json()
                
                console.print(f"[green]✓[/green] Found {len(registry_data)} servers in registry")
                
                # Parse and categorize servers
                self.all_servers = []
                for server_data in registry_data:
                    server = self._parse_server_data(server_data)
                    if server:
                        self.all_servers.append(server)
                
                # Sort by category and priority
                self.all_servers.sort(key=lambda x: (
                    self.categories.get(x.category, {}).get("priority", 99),
                    x.priority,
                    x.name
                ))
                
                console.print(f"[green]✓[/green] Parsed {len(self.all_servers)} valid servers")
                return True
                
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to fetch servers: {e}")
            return False
    
    def _parse_server_data(self, data: Dict) -> Optional[MCPServerInfo]:
        """Parse server data from registry"""
        try:
            if not data.get("packages"):
                return None
            
            package = data["packages"][0]
            
            # Determine category and priority
            category, priority = self._categorize_server(data["name"], data.get("description", ""))
            
            # Check if requires API key
            env_vars = {
                var["name"]: var.get("description", "")
                for var in package.get("environment_variables", [])
            }
            
            requires_api_key = any(
                "api" in var.lower() or "key" in var.lower() or "token" in var.lower()
                for var in env_vars.keys()
            )
            
            # Extract API services
            api_services = []
            if requires_api_key:
                api_services = self._extract_api_services(data["name"], data.get("description", ""))
            
            return MCPServerInfo(
                name=data["name"],
                description=data.get("description", ""),
                registry_type=package["registry_type"],
                identifier=package["identifier"],
                version=package.get("version", "latest"),
                category=category,
                priority=priority,
                transport_type=package.get("transport_type", "stdio"),
                environment_variables=env_vars,
                package_arguments=package.get("package_arguments", []),
                repository_url=data.get("repository", {}).get("url", ""),
                status=data.get("status", "active"),
                requires_api_key=requires_api_key,
                api_services=api_services,
                installation_notes=self._get_installation_notes(package)
            )
            
        except Exception as e:
            logger.error(f"Failed to parse server {data.get('name', 'unknown')}: {e}")
            return None
    
    def _categorize_server(self, name: str, description: str) -> Tuple[str, int]:
        """Categorize server and assign priority"""
        name_lower = name.lower()
        desc_lower = description.lower()
        
        # Search & Information
        if any(x in name_lower or x in desc_lower for x in ["search", "exa", "tavily", "web", "google", "bing"]):
            return "search", 1
        
        # Math & Calculations
        if any(x in name_lower or x in desc_lower for x in ["math", "calc", "solver", "equation", "compute"]):
            return "math", 1
        
        # Development
        if any(x in name_lower or x in desc_lower for x in ["git", "github", "terminal", "circleci", "docker", "dev"]):
            return "development", 1
        
        # Database
        if any(x in name_lower or x in desc_lower for x in ["database", "db", "sql", "mongo", "postgres", "clickhouse", "elastic", "chroma"]):
            return "database", 1
        
        # Social Media
        if any(x in name_lower or x in desc_lower for x in ["twitter", "social", "instagram", "linkedin", "reddit"]):
            return "social", 1
        
        # Productivity
        if any(x in name_lower or x in desc_lower for x in ["todoist", "task", "calendar", "note", "productivity"]):
            return "productivity", 1
        
        # Finance
        if any(x in name_lower or x in desc_lower for x in ["stripe", "payment", "finance", "bank", "money"]):
            return "finance", 1
        
        # Media
        if any(x in name_lower or x in desc_lower for x in ["spotify", "music", "video", "media", "image"]):
            return "media", 1
        
        # AI/ML
        if any(x in name_lower or x in desc_lower for x in ["ai", "ml", "machine learning", "model", "phoenix", "arize"]):
            return "ai", 1
        
        # Utilities
        if any(x in name_lower or x in desc_lower for x in ["weather", "time", "utility", "tool"]):
            return "utility", 1
        
        # Web Tools
        if any(x in name_lower or x in desc_lower for x in ["http", "api", "webhook", "firecrawl", "scrape"]):
            return "web", 1
        
        # Storage
        if any(x in name_lower or x in desc_lower for x in ["storage", "file", "box", "drive", "cloud"]):
            return "storage", 1
        
        return "other", 10
    
    def _extract_api_services(self, name: str, description: str) -> List[str]:
        """Extract API service names from server name/description"""
        services = []
        name_desc = f"{name} {description}".lower()
        
        service_keywords = {
            "OpenAI": ["openai", "gpt"],
            "Anthropic": ["anthropic", "claude"],
            "Google": ["google", "gemini"],
            "Exa": ["exa"],
            "Tavily": ["tavily"],
            "Twitter": ["twitter"],
            "Spotify": ["spotify"],
            "Stripe": ["stripe"],
            "GitHub": ["github"],
            "OpenWeatherMap": ["weather", "openweather"],
            "Todoist": ["todoist"],
            "Box": ["box"],
            "CircleCI": ["circleci"],
            "Elasticsearch": ["elastic"],
        }
        
        for service, keywords in service_keywords.items():
            if any(keyword in name_desc for keyword in keywords):
                services.append(service)
        
        return services
    
    def _get_installation_notes(self, package: Dict) -> str:
        """Get installation notes for the package"""
        notes = []
        
        if package["registry_type"] == "npm":
            notes.append("Requires Node.js and npm")
        elif package["registry_type"] == "pypi":
            notes.append("Python package via pip")
        elif package["registry_type"] == "oci":
            notes.append("Requires Docker")
        
        if package.get("environment_variables"):
            notes.append("Requires environment configuration")
        
        return "; ".join(notes)
    
    def display_main_menu(self) -> str:
        """Display main menu and get user choice"""
        safe_screen_update(clear_screen=False)
        
        # Header
        console.print(Panel.fit(
            "[bold blue]🚀 OrionAI - Interactive MCP Server Manager[/bold blue]\n"
            "[dim]Browse, select, and install external MCP servers[/dim]",
            border_style="blue"
        ))
        
        # Stats
        total_servers = len(self.all_servers)
        installed_count = len(self.installed_servers)
        selected_count = len(self.selected_servers)
        
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_row("📦 Total Servers:", f"[bold]{total_servers}[/bold]")
        stats_table.add_row("✅ Installed:", f"[green bold]{installed_count}[/green bold]")
        stats_table.add_row("🎯 Selected:", f"[yellow bold]{selected_count}[/yellow bold]")
        
        console.print(Panel(stats_table, title="Statistics", border_style="green"))
        
        # Menu options
        menu_table = Table(show_header=False, box=None, padding=(0, 1))
        menu_table.add_column("Option", style="bold cyan")
        menu_table.add_column("Description")
        
        menu_table.add_row("1", "Browse all servers")
        menu_table.add_row("2", "Browse by category")
        menu_table.add_row("3", "Search servers")
        menu_table.add_row("4", "View selected servers")
        menu_table.add_row("5", "Install selected servers")
        menu_table.add_row("6", "View installed servers")
        menu_table.add_row("7", "Generate configurations")
        menu_table.add_row("8", "Help & Instructions")
        menu_table.add_row("0", "Exit")
        
        console.print(Panel(menu_table, title="Main Menu", border_style="cyan"))
        
        return Prompt.ask("\n[bold]Choose an option", choices=['0','1','2','3','4','5','6','7','8'], default="1")
    
    def browse_all_servers(self):
        """Browse all available servers with pagination"""
        page_size = 20
        page = 0
        total_pages = (len(self.all_servers) + page_size - 1) // page_size
        
        while True:
            safe_screen_update(clear_screen=False)
            console.print(f"[bold]📦 All MCP Servers (Page {page + 1}/{total_pages})[/bold]\n")
            
            # Display current page
            start_idx = page * page_size
            end_idx = min(start_idx + page_size, len(self.all_servers))
            page_servers = self.all_servers[start_idx:end_idx]
            
            self._display_server_list(page_servers, start_idx)
            
            # Navigation options
            console.print(f"\n[dim]Page {page + 1} of {total_pages}[/dim]")
            
            choices = []
            if page > 0:
                choices.append("p")
            if page < total_pages - 1:
                choices.append("n")
            choices.extend(["s", "b"])
            
            nav_options = []
            if page > 0:
                nav_options.append("[p] Previous page")
            if page < total_pages - 1:
                nav_options.append("[n] Next page")
            nav_options.extend(["[s] Select servers", "[b] Back to main menu"])
            
            console.print(" | ".join(nav_options))
            
            choice = Prompt.ask("\nAction", choices=choices, default="s")
            
            if choice == "p" and page > 0:
                page -= 1
            elif choice == "n" and page < total_pages - 1:
                page += 1
            elif choice == "s":
                self._select_servers_from_list(page_servers, start_idx)
            elif choice == "b":
                break
    
    def browse_by_category(self):
        """Browse servers by category"""
        while True:
            safe_screen_update(clear_screen=False)
            console.print("[bold]🗂️ Browse by Category[/bold]\n")
            
            # Display categories
            cat_table = Table(show_header=False, box=None, padding=(0, 1))
            cat_table.add_column("Option", style="bold cyan")
            cat_table.add_column("Category")
            cat_table.add_column("Count", justify="right")
            
            sorted_categories = sorted(
                self.categories.items(),
                key=lambda x: x[1]["priority"]
            )
            
            for i, (cat_key, cat_info) in enumerate(sorted_categories, 1):
                count = len([s for s in self.all_servers if s.category == cat_key])
                cat_table.add_row(str(i), cat_info["name"], f"[dim]({count})[/dim]")
            
            cat_table.add_row("0", "[red]Back to main menu[/red]", "")
            
            console.print(cat_table)
            
            choice = IntPrompt.ask(
                "\nSelect category",
                choices=list(range(len(sorted_categories) + 1)),
                default=0
            )
            
            if choice == 0:
                break
            
            # Show servers in selected category
            selected_cat = sorted_categories[choice - 1][0]
            category_servers = [s for s in self.all_servers if s.category == selected_cat]
            
            if category_servers:
                self._browse_category_servers(selected_cat, category_servers)
            else:
                console.print("[red]No servers found in this category[/red]")
                console.input("Press Enter to continue...")
    
    def _browse_category_servers(self, category: str, servers: List[MCPServerInfo]):
        """Browse servers within a specific category"""
        # Use print instead of clear to avoid resize issues
        console.print("\n" + "="*80)
        cat_name = self.categories.get(category, {}).get("name", category)
        console.print(f"[bold]{cat_name}[/bold]\n")
        
        self._display_server_list(servers)
        
        console.print("\n[s] Select servers | [b] Back to categories")
        choice = Prompt.ask("Action", choices=["s", "b"], default="s")
        
        if choice == "s":
            self._select_servers_from_list(servers)
    
    def _display_server_list(self, servers: List[MCPServerInfo], start_idx: int = 0):
        """Display a list of servers in a formatted table"""
        table = Table(box=None, padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="bold")
        table.add_column("Type", style="cyan", width=6)
        table.add_column("API Key", width=8, justify="center")
        table.add_column("Status", width=10, justify="center")
        table.add_column("Description", style="dim")
        
        for i, server in enumerate(servers):
            idx = start_idx + i + 1
            
            # Status indicators
            status_parts = []
            if server.name in self.installed_servers:
                status_parts.append("[green]✅ Installed[/green]")
            if server.name in self.selected_servers:
                status_parts.append("[yellow]🎯 Selected[/yellow]")
            
            status = " ".join(status_parts) if status_parts else "[dim]Available[/dim]"
            
            api_key = "[red]Required[/red]" if server.requires_api_key else "[green]None[/green]"
            
            table.add_row(
                str(idx),
                server.name,
                server.registry_type.upper(),
                api_key,
                status,
                server.description[:60] + "..." if len(server.description) > 60 else server.description
            )
        
        console.print(table)
    
    def _select_servers_from_list(self, servers: List[MCPServerInfo], start_idx: int = 0):
        """Allow user to select servers from a list"""
        console.print("\n[bold yellow]Select servers to add to your installation queue:[/bold yellow]")
        console.print("[dim]Enter server numbers separated by commas (e.g., 1,3,5) or 'all' for all servers[/dim]")
        console.print("[dim]Use 'clear' to clear current selection, 'done' to finish[/dim]")
        
        while True:
            current_selection = [s.name for s in servers if s.name in self.selected_servers]
            console.print(f"\n[blue]Currently selected from this list: {len(current_selection)}[/blue]")
            
            try:
                selection = Prompt.ask("Server selection").strip()
                
                if not selection:
                    console.print("[yellow]Please enter a selection (numbers, 'all', 'clear', or 'done')[/yellow]")
                    continue
                
                selection_lower = selection.lower()
                
                if selection_lower == "done":
                    break
                elif selection_lower == "clear":
                    for server in servers:
                        self.selected_servers.discard(server.name)
                    console.print("[green]✓[/green] Selection cleared")
                elif selection_lower == "all":
                    for server in servers:
                        self.selected_servers.add(server.name)
                    console.print(f"[green]✓[/green] Added all {len(servers)} servers to selection")
                else:
                    try:
                        indices = [int(x.strip()) for x in selection.split(",") if x.strip()]
                        if not indices:
                            console.print("[yellow]Please enter valid server numbers[/yellow]")
                            continue
                            
                        added = 0
                        for idx in indices:
                            # Convert global index to local page index if start_idx is provided
                            if start_idx > 0:
                                local_idx = idx - start_idx
                                if 1 <= local_idx <= len(servers):
                                    server = servers[local_idx - 1]
                                    if server.name not in self.selected_servers:
                                        self.selected_servers.add(server.name)
                                        added += 1
                            else:
                                # Direct indexing for non-paginated lists
                                if 1 <= idx <= len(servers):
                                    server = servers[idx - 1]
                                    if server.name not in self.selected_servers:
                                        self.selected_servers.add(server.name)
                                        added += 1
                        
                        if added > 0:
                            console.print(f"[green]✓[/green] Added {added} servers to selection")
                        else:
                            console.print("[yellow]No new servers added[/yellow]")
                            
                    except ValueError:
                        console.print("[red]Invalid selection format. Use numbers separated by commas (e.g., 1,3,5)[/red]")
                        
            except KeyboardInterrupt:
                console.print("\n[yellow]Selection cancelled[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[yellow]Please try again or use 'done' to finish[/yellow]")
    
    def search_servers(self):
        """Search servers by name or description"""
        safe_screen_update(clear_screen=False)
        console.print("[bold]🔍 Search MCP Servers[/bold]\n")
        
        query = Prompt.ask("Enter search query").strip()
        if not query:
            return
        
        # Search in name and description
        query_lower = query.lower()
        matching_servers = [
            server for server in self.all_servers
            if query_lower in server.name.lower() or query_lower in server.description.lower()
        ]
        
        if not matching_servers:
            console.print(f"[red]No servers found matching '{query}'[/red]")
            console.input("Press Enter to continue...")
            return
        
        console.print(f"[green]Found {len(matching_servers)} servers matching '{query}':[/green]\n")
        self._display_server_list(matching_servers)
        
        console.print("\n[s] Select servers | [b] Back to main menu")
        choice = Prompt.ask("Action", choices=["s", "b"], default="s")
        
        if choice == "s":
            self._select_servers_from_list(matching_servers)
    
    def view_selected_servers(self):
        """View currently selected servers"""
        safe_screen_update(clear_screen=False)
        console.print("[bold]🎯 Selected Servers[/bold]\n")
        
        if not self.selected_servers:
            console.print("[yellow]No servers currently selected[/yellow]")
            console.input("Press Enter to continue...")
            return
        
        selected_server_objects = [
            server for server in self.all_servers
            if server.name in self.selected_servers
        ]
        
        self._display_server_list(selected_server_objects)
        
        # Show summary
        by_type = {}
        api_key_required = 0
        for server in selected_server_objects:
            by_type[server.registry_type] = by_type.get(server.registry_type, 0) + 1
            if server.requires_api_key:
                api_key_required += 1
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"Total selected: {len(selected_server_objects)}")
        for reg_type, count in by_type.items():
            console.print(f"{reg_type.upper()}: {count}")
        console.print(f"API keys required: {api_key_required}")
        
        console.print("\n[c] Clear selection | [r] Remove specific servers | [i] Install all | [b] Back")
        choice = Prompt.ask("Action", choices=["c", "r", "i", "b"], default="b")
        
        if choice == "c":
            self.selected_servers.clear()
            console.print("[green]✓[/green] Selection cleared")
            console.input("Press Enter to continue...")
        elif choice == "r":
            self._remove_from_selection(selected_server_objects)
        elif choice == "i":
            asyncio.run(self.install_selected_servers())
    
    def _remove_from_selection(self, servers: List[MCPServerInfo]):
        """Remove specific servers from selection"""
        console.print("\n[yellow]Remove servers from selection:[/yellow]")
        console.print("[dim]Enter server numbers separated by commas[/dim]")
        
        selection = Prompt.ask("Servers to remove").strip()
        try:
            indices = [int(x.strip()) for x in selection.split(",")]
            removed = 0
            for idx in indices:
                if 1 <= idx <= len(servers):
                    server = servers[idx - 1]
                    if server.name in self.selected_servers:
                        self.selected_servers.remove(server.name)
                        removed += 1
            
            console.print(f"[green]✓[/green] Removed {removed} servers from selection")
            console.input("Press Enter to continue...")
            
        except ValueError:
            console.print("[red]Invalid selection format[/red]")
            console.input("Press Enter to continue...")
    
    async def install_selected_servers(self):
        """Install all selected servers"""
        if not self.selected_servers:
            console.print("[yellow]No servers selected for installation[/yellow]")
            console.input("Press Enter to continue...")
            return
        
        selected_server_objects = [
            server for server in self.all_servers
            if server.name in self.selected_servers
        ]
        
        safe_screen_update(clear_screen=False)
        console.print("[bold]🚀 Installing Selected MCP Servers[/bold]\n")
        
        # Show installation plan
        self._show_installation_plan(selected_server_objects)
        
        if not Confirm.ask("\nProceed with installation?"):
            return
        
        # Check dependencies
        await self._check_and_install_dependencies(selected_server_objects)
        
        # Handle API keys
        await self._handle_api_keys(selected_server_objects)
        
        # Install servers
        await self._install_servers(selected_server_objects)
        
        # Generate configurations
        await self._generate_configurations(selected_server_objects)
        
        console.print("\n[bold green]🎉 Installation complete![/bold green]")
        console.input("Press Enter to continue...")
    
    def _show_installation_plan(self, servers: List[MCPServerInfo]):
        """Show detailed installation plan"""
        # Group by type
        by_type = {"npm": [], "pypi": [], "oci": []}
        api_servers = []
        
        for server in servers:
            by_type[server.registry_type].append(server)
            if server.requires_api_key:
                api_servers.append(server)
        
        plan_table = Table(title="Installation Plan", box=None)
        plan_table.add_column("Type", style="bold cyan")
        plan_table.add_column("Count", justify="right")
        plan_table.add_column("Dependencies")
        
        for reg_type, server_list in by_type.items():
            if server_list:
                if reg_type == "npm":
                    deps = "Node.js, npm"
                elif reg_type == "pypi":
                    deps = "Python, pip"
                elif reg_type == "oci":
                    deps = "Docker"
                else:
                    deps = "Unknown"
                
                plan_table.add_row(reg_type.upper(), str(len(server_list)), deps)
        
        console.print(plan_table)
        
        if api_servers:
            console.print(f"\n[yellow]⚠️  {len(api_servers)} servers require API keys[/yellow]")
            for server in api_servers[:5]:  # Show first 5
                services = ", ".join(server.api_services) if server.api_services else "Unknown service"
                console.print(f"  • {server.name}: {services}")
            if len(api_servers) > 5:
                console.print(f"  ... and {len(api_servers) - 5} more")
    
    async def _check_and_install_dependencies(self, servers: List[MCPServerInfo]):
        """Check and install required dependencies"""
        console.print("\n[bold]📋 Checking Dependencies[/bold]")
        
        # Check Node.js for npm packages
        npm_servers = [s for s in servers if s.registry_type == "npm"]
        if npm_servers:
            if not self._check_nodejs():
                console.print("[red]✗[/red] Node.js not found")
                if Confirm.ask("Install Node.js?"):
                    await self._install_nodejs()
                else:
                    console.print("[yellow]Skipping NPM servers[/yellow]")
                    return
            else:
                console.print("[green]✓[/green] Node.js available")
        
        # Check Docker for OCI packages
        oci_servers = [s for s in servers if s.registry_type == "oci"]
        if oci_servers:
            if not self._check_docker():
                console.print("[red]✗[/red] Docker not found")
                console.print("[yellow]Please install Docker manually for OCI servers[/yellow]")
            else:
                console.print("[green]✓[/green] Docker available")
        
        # Python is assumed to be available
        pypi_servers = [s for s in servers if s.registry_type == "pypi"]
        if pypi_servers:
            console.print("[green]✓[/green] Python available")
    
    def _check_nodejs(self) -> bool:
        """Check if Node.js is available"""
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    async def _install_nodejs(self):
        """Provide Node.js installation instructions"""
        console.print("\n[bold yellow]Node.js Installation Required[/bold yellow]")
        console.print("Please install Node.js from: https://nodejs.org/")
        console.print("Or use a package manager:")
        console.print("  • Windows: winget install OpenJS.NodeJS")
        console.print("  • macOS: brew install node")
        console.print("  • Linux: sudo apt install nodejs npm")
        console.input("Press Enter after installing Node.js...")
    
    async def _handle_api_keys(self, servers: List[MCPServerInfo]):
        """Handle API key configuration for servers that need them"""
        api_servers = [s for s in servers if s.requires_api_key]
        if not api_servers:
            return
        
        console.print(f"\n[bold]🔑 API Key Configuration[/bold]")
        console.print(f"[yellow]{len(api_servers)} servers require API keys[/yellow]")
        
        if not Confirm.ask("Configure API keys now?"):
            console.print("[yellow]API keys can be configured later in the config files[/yellow]")
            return
        
        api_config = {}
        
        for server in api_servers:
            console.print(f"\n[bold]{server.name}[/bold]")
            if server.api_services:
                console.print(f"Required services: {', '.join(server.api_services)}")
            
            for env_var, description in server.environment_variables.items():
                if "api" in env_var.lower() or "key" in env_var.lower() or "token" in env_var.lower():
                    value = Prompt.ask(
                        f"Enter {env_var}",
                        default="",
                        show_default=False
                    )
                    if value:
                        api_config[env_var] = value
        
        # Save API configuration
        if api_config:
            api_file = self.config_dir / "api_keys.json"
            with open(api_file, "w") as f:
                json.dump(api_config, f, indent=2)
            console.print(f"[green]✓[/green] API keys saved to {api_file}")
    
    async def _install_servers(self, servers: List[MCPServerInfo]):
        """Install the actual servers"""
        console.print("\n[bold]📦 Installing Servers[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Installing servers...", total=len(servers))
            
            for server in servers:
                progress.update(task, description=f"Installing {server.name}")
                
                success = False
                if server.registry_type == "npm":
                    success = await self._install_npm_server(server)
                elif server.registry_type == "pypi":
                    success = await self._install_pypi_server(server)
                elif server.registry_type == "oci":
                    success = await self._install_oci_server(server)
                
                if success:
                    self.installed_servers.add(server.name)
                    self.selected_servers.discard(server.name)
                
                progress.advance(task)
        
        # Save installed servers list
        self._save_installed_servers()
        
        installed_count = len([s for s in servers if s.name in self.installed_servers])
        console.print(f"\n[green]✓[/green] Successfully installed {installed_count}/{len(servers)} servers")
    
    async def _install_npm_server(self, server: MCPServerInfo) -> bool:
        """Install NPM-based server"""
        try:
            install_dir = self.config_dir / "external_servers" / server.identifier.replace("/", "_")
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
            
            # Install
            result = subprocess.run(
                ["npm", "install"],
                cwd=install_dir,
                capture_output=True,
                text=True,
                timeout=300,
                shell=True  # Use shell=True on Windows for proper npm execution
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed NPM server: {server.name}")
                return True
            else:
                logger.error(f"NPM install failed for {server.name}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                console.print(f"[red]Failed to install {server.name}:[/red]")
                console.print(f"[dim]Error: {result.stderr.strip() if result.stderr else 'Unknown error'}[/dim]")
                return False
            
        except Exception as e:
            logger.error(f"Failed to install NPM server {server.name}: {e}")
            console.print(f"[red]Failed to install {server.name}: {e}[/red]")
            return False
    
    async def _install_pypi_server(self, server: MCPServerInfo) -> bool:
        """Install PyPI-based server"""
        try:
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
                logger.error(f"PyPI install failed for {server.name}")
                logger.error(f"Command: {sys.executable} -m pip install {server.identifier}=={server.version}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                console.print(f"[red]Failed to install {server.name}:[/red]")
                console.print(f"[dim]Error: {result.stderr.strip() if result.stderr else 'Unknown error'}[/dim]")
                return False
            
        except Exception as e:
            logger.error(f"Failed to install PyPI server {server.name}: {e}")
            console.print(f"[red]Failed to install {server.name}: {e}[/red]")
            return False
    
    async def _install_oci_server(self, server: MCPServerInfo) -> bool:
        """Install OCI/Docker-based server"""
        try:
            # Pull the container
            result = subprocess.run(
                ["docker", "pull", server.identifier],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to install OCI server {server.name}: {e}")
            return False
    
    async def _generate_configurations(self, servers: List[MCPServerInfo]):
        """Generate configuration files for installed servers"""
        console.print("\n[bold]⚙️  Generating Configurations[/bold]")
        
        # Generate Claude Desktop config
        claude_config = {"mcpServers": {}}
        
        for server in servers:
            if server.name in self.installed_servers:
                config = self._generate_server_config(server)
                claude_config["mcpServers"][server.name] = config
        
        # Save configurations
        claude_file = self.config_dir / "claude_desktop_config.json"
        with open(claude_file, "w") as f:
            json.dump(claude_config, f, indent=2)
        
        # Generate usage instructions
        instructions = self._generate_usage_instructions(servers)
        instructions_file = self.config_dir / "usage_instructions.md"
        with open(instructions_file, "w") as f:
            f.write(instructions)
        
        console.print(f"[green]✓[/green] Configurations saved to {self.config_dir}")
    
    def _generate_server_config(self, server: MCPServerInfo) -> Dict:
        """Generate configuration for a single server"""
        config = {}
        
        if server.registry_type == "npm":
            install_dir = self.config_dir / "external_servers" / server.identifier.replace("/", "_")
            config["command"] = "node"
            config["args"] = [str(install_dir / "node_modules" / server.identifier / "index.js")]
        elif server.registry_type == "pypi":
            config["command"] = sys.executable
            config["args"] = ["-m", server.identifier]
        elif server.registry_type == "oci":
            config["command"] = "docker"
            config["args"] = ["run", "-i", "--rm", server.identifier]
        
        # Add environment variables
        if server.environment_variables:
            config["env"] = {}
            for var_name in server.environment_variables:
                config["env"][var_name] = f"${{{var_name}}}"
        
        return config
    
    def _generate_usage_instructions(self, servers: List[MCPServerInfo]) -> str:
        """Generate comprehensive usage instructions"""
        instructions = [
            "# OrionAI MCP Servers - Usage Instructions\n",
            f"Generated on: {asyncio.get_event_loop().time()}\n",
            f"Total servers configured: {len([s for s in servers if s.name in self.installed_servers])}\n",
            "## Quick Start\n",
            "1. Copy the contents of `claude_desktop_config.json` to your Claude Desktop configuration",
            "2. Configure any required API keys (see below)",
            "3. Restart Claude Desktop",
            "4. Start using the new MCP tools!\n",
            "## Configuration Files\n",
            f"- **Main config**: `{self.config_dir / 'claude_desktop_config.json'}`",
            f"- **API keys**: `{self.config_dir / 'api_keys.json'}`",
            f"- **Installation log**: `{self.config_dir / 'installed_servers.json'}`\n",
            "## Servers Requiring API Keys\n"
        ]
        
        api_servers = [s for s in servers if s.requires_api_key and s.name in self.installed_servers]
        for server in api_servers:
            instructions.append(f"### {server.name}\n")
            instructions.append(f"**Description**: {server.description}\n")
            if server.api_services:
                instructions.append(f"**Required services**: {', '.join(server.api_services)}\n")
            instructions.append("**Environment variables**:\n")
            for var, desc in server.environment_variables.items():
                instructions.append(f"- `{var}`: {desc}\n")
            instructions.append("\n")
        
        instructions.extend([
            "## Server Categories\n",
            "Your installed servers cover these categories:\n"
        ])
        
        # Group by category
        by_category = {}
        for server in servers:
            if server.name in self.installed_servers:
                cat = server.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(server)
        
        for category, cat_servers in by_category.items():
            cat_name = self.categories.get(category, {}).get("name", category)
            instructions.append(f"### {cat_name}\n")
            for server in cat_servers:
                instructions.append(f"- **{server.name}**: {server.description}\n")
            instructions.append("\n")
        
        instructions.append("## Troubleshooting\n")
        instructions.append("If you encounter issues:\n")
        instructions.append("1. Check that all required dependencies are installed\n")
        instructions.append("2. Verify API keys are correctly configured\n")
        instructions.append("3. Restart Claude Desktop after configuration changes\n")
        instructions.append("4. Check the server logs for error messages\n")
        
        return "".join(instructions)
    
    def view_installed_servers(self):
        """View currently installed servers"""
        console.clear()
        console.print("[bold]✅ Installed MCP Servers[/bold]\n")
        
        if not self.installed_servers:
            console.print("[yellow]No servers currently installed[/yellow]")
            console.input("Press Enter to continue...")
            return
        
        installed_server_objects = [
            server for server in self.all_servers
            if server.name in self.installed_servers
        ]
        
        self._display_server_list(installed_server_objects)
        
        console.print("\n[u] Uninstall servers | [c] View configurations | [b] Back")
        choice = Prompt.ask("Action", choices=["u", "c", "b"], default="b")
        
        if choice == "u":
            self._uninstall_servers(installed_server_objects)
        elif choice == "c":
            self._view_configurations()
    
    def _uninstall_servers(self, servers: List[MCPServerInfo]):
        """Uninstall selected servers"""
        console.print("\n[red]Uninstall servers:[/red]")
        console.print("[dim]Enter server numbers separated by commas[/dim]")
        
        selection = Prompt.ask("Servers to uninstall").strip()
        try:
            indices = [int(x.strip()) for x in selection.split(",")]
            to_uninstall = []
            
            for idx in indices:
                if 1 <= idx <= len(servers):
                    to_uninstall.append(servers[idx - 1])
            
            if to_uninstall and Confirm.ask(f"Uninstall {len(to_uninstall)} servers?"):
                for server in to_uninstall:
                    self.installed_servers.discard(server.name)
                
                self._save_installed_servers()
                console.print(f"[green]✓[/green] Marked {len(to_uninstall)} servers as uninstalled")
                console.print("[yellow]Note: Files may still exist, manual cleanup may be needed[/yellow]")
            
            console.input("Press Enter to continue...")
            
        except ValueError:
            console.print("[red]Invalid selection format[/red]")
            console.input("Press Enter to continue...")
    
    def _view_configurations(self):
        """View generated configuration files"""
        console.clear()
        console.print("[bold]⚙️  Configuration Files[/bold]\n")
        
        config_files = [
            ("claude_desktop_config.json", "Claude Desktop MCP configuration"),
            ("api_keys.json", "API keys and environment variables"),
            ("installed_servers.json", "List of installed servers"),
            ("usage_instructions.md", "Comprehensive usage guide")
        ]
        
        table = Table(box=None)
        table.add_column("File", style="bold cyan")
        table.add_column("Description")
        table.add_column("Status", justify="center")
        
        for filename, description in config_files:
            filepath = self.config_dir / filename
            status = "[green]✓ Exists[/green]" if filepath.exists() else "[red]✗ Missing[/red]"
            table.add_row(filename, description, status)
        
        console.print(table)
        console.print(f"\n[dim]Configuration directory: {self.config_dir}[/dim]")
        console.input("Press Enter to continue...")
    
    def generate_configurations(self):
        """Regenerate configuration files"""
        console.clear()
        console.print("[bold]⚙️  Generate Configurations[/bold]\n")
        
        if not self.installed_servers:
            console.print("[yellow]No installed servers found[/yellow]")
            console.input("Press Enter to continue...")
            return
        
        installed_server_objects = [
            server for server in self.all_servers
            if server.name in self.installed_servers
        ]
        
        console.print(f"Generating configurations for {len(installed_server_objects)} installed servers...")
        
        asyncio.run(self._generate_configurations(installed_server_objects))
        
        console.print("[green]✓[/green] Configurations regenerated")
        console.input("Press Enter to continue...")
    
    def show_help(self):
        """Show help and instructions"""
        console.clear()
        
        help_text = """
[bold blue]🚀 OrionAI Interactive MCP Manager - Help[/bold blue]

[bold]What are MCP Servers?[/bold]
Model Context Protocol (MCP) servers provide external capabilities to AI assistants.
They can perform web searches, calculations, database queries, API calls, and much more.

[bold]How to Use This Manager:[/bold]

1. [cyan]Browse Servers[/cyan]: Explore 100+ available MCP servers
   • Browse all servers with pagination
   • Filter by category (search, math, development, etc.)
   • Search by name or description

2. [cyan]Select Servers[/cyan]: Choose servers for installation
   • Add multiple servers to your selection
   • Review selected servers before installation
   • Clear or modify selections as needed

3. [cyan]Install Servers[/cyan]: Automated installation process
   • Dependency checking (Node.js, Python, Docker)
   • Automatic package installation
   • API key configuration assistance
   • Progress tracking and error handling

4. [cyan]Configuration[/cyan]: Automatic config generation
   • Claude Desktop integration files
   • Environment variable templates
   • Usage instructions and documentation

[bold]Server Types:[/bold]
• [green]NPM[/green]: Node.js packages (requires Node.js/npm)
• [blue]PyPI[/blue]: Python packages (requires Python/pip)
• [yellow]OCI[/yellow]: Docker containers (requires Docker)

[bold]API Keys:[/bold]
Many servers require API keys from external services:
• Web search: Exa, Tavily, Google
• Social media: Twitter, Instagram
• Productivity: Todoist, Notion
• Finance: Stripe, banking APIs
• Weather: OpenWeatherMap
• And many more...

[bold]Configuration Files:[/bold]
All configurations are saved to your config directory:
• Claude Desktop integration
• API key templates
• Installation tracking
• Usage documentation

[bold]Tips:[/bold]
• Start with servers that don't require API keys
• Group similar servers together (all search, all math, etc.)
• Read server descriptions to understand capabilities
• Check installation notes for special requirements

[bold]Support:[/bold]
For issues or questions:
• Check the generated usage instructions
• Review server documentation links
• Verify all dependencies are installed
• Ensure API keys are correctly configured
"""
        
        console.print(Panel(help_text, border_style="blue"))
        console.input("\nPress Enter to continue...")
    
    async def run(self):
        """Main interactive loop"""
        console.clear()
        console.print("[bold blue]🚀 Starting OrionAI MCP Manager...[/bold blue]")
        
        # Fetch servers if not already loaded
        if not self.all_servers:
            if not await self.fetch_all_servers():
                console.print("[red]Failed to load MCP servers. Exiting.[/red]")
                return
        
        while True:
            choice = self.display_main_menu()
            
            if choice == "0":
                console.print("[bold]Thank you for using OrionAI MCP Manager! 🚀[/bold]")
                break
            elif choice == "1":
                self.browse_all_servers()
            elif choice == "2":
                self.browse_by_category()
            elif choice == "3":
                self.search_servers()
            elif choice == "4":
                self.view_selected_servers()
            elif choice == "5":
                await self.install_selected_servers()
            elif choice == "6":
                self.view_installed_servers()
            elif choice == "7":
                self.generate_configurations()
            elif choice == "8":
                self.show_help()

# Main entry point
async def main():
    """Main entry point for interactive MCP manager"""
    manager = InteractiveMCPManager()
    await manager.run()

if __name__ == "__main__":
    asyncio.run(main())
