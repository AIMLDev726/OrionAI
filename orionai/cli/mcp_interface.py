"""
MCP CLI Interface
================

Command-line interface for managing MCP servers and tools.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.align import Align
import rich.box

from ..mcp.manager import MCPManager
from ..mcp.server_registry import MCPServerRegistry
from ..mcp.tools import MCPToolRegistry


def create_mcp_header() -> Panel:
    """Create MCP header panel."""
    header_text = Text()
    header_text.append("🔌 ", style="bold yellow")
    header_text.append("MCP Manager", style="bold green")
    header_text.append(" - Model Context Protocol Integration", style="bold white")
    
    return Panel(
        Align.center(header_text),
        box=rich.box.DOUBLE,
        style="green"
    )


def show_mcp_main_menu(mcp_manager: MCPManager, console: Console):
    """Show MCP main menu."""
    registry = MCPServerRegistry()
    tool_registry = MCPToolRegistry(mcp_manager)
    
    while True:
        console.clear()
        console.print(create_mcp_header())
        
        # Show current status
        status = mcp_manager.get_server_status()
        connected_servers = sum(1 for s in status.values() if s['connected'])
        total_servers = len(status)
        total_tools = len(mcp_manager.get_available_tools())
        
        status_text = Text()
        status_text.append("📊 Status: ", style="bold")
        status_text.append(f"{connected_servers}/{total_servers} servers connected", style="green" if connected_servers > 0 else "yellow")
        status_text.append(" | ")
        status_text.append(f"{total_tools} tools available", style="cyan")
        
        console.print(Panel(Align.center(status_text), style="blue"))
        
        # Menu options
        menu_table = Table(box=rich.box.ROUNDED, show_header=False)
        menu_table.add_column("Option", style="cyan", width=8)
        menu_table.add_column("Description", style="white")
        
        menu_options = [
            ("1", "🔌 Manage MCP Servers"),
            ("2", "🛠️  Browse & Use Tools"),
            ("3", "📦 Install Server Templates"),
            ("4", "📊 Server Status & Information"),
            ("5", "🔧 Test Tools"),
            ("6", "⚙️  MCP Settings"),
            ("0", "🔙 Back to Main Menu"),
        ]
        
        for option, desc in menu_options:
            menu_table.add_row(option, desc)
        
        console.print(menu_table)
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6"], default="1")
        
        if choice == "0":
            break
        elif choice == "1":
            manage_servers_menu(mcp_manager, registry, console)
        elif choice == "2":
            browse_tools_menu(tool_registry, console)
        elif choice == "3":
            install_templates_menu(mcp_manager, registry, console)
        elif choice == "4":
            show_server_status(mcp_manager, console)
        elif choice == "5":
            test_tools_menu(tool_registry, console)
        elif choice == "6":
            mcp_settings_menu(mcp_manager, console)


def manage_servers_menu(mcp_manager: MCPManager, registry: MCPServerRegistry, console: Console):
    """Manage MCP servers menu."""
    while True:
        console.clear()
        console.print(Panel.fit("🔌 Manage MCP Servers", style="bold green"))
        
        # Show configured servers
        servers = mcp_manager.list_configured_servers()
        if servers:
            server_table = Table(title="Configured Servers", box=rich.box.ROUNDED)
            server_table.add_column("Name", style="cyan")
            server_table.add_column("Command", style="white")
            server_table.add_column("Status", style="yellow")
            server_table.add_column("Description", style="blue")
            
            for server in servers:
                status = "🟢 Connected" if server['connected'] else "🔴 Disconnected"
                server_table.add_row(
                    server['name'],
                    server['command'][:50] + "..." if len(server['command']) > 50 else server['command'],
                    status,
                    server['description'][:40] + "..." if len(server['description']) > 40 else server['description']
                )
            
            console.print(server_table)
        else:
            console.print("ℹ️  No servers configured", style="blue")
        
        # Menu
        menu_table = Table(box=rich.box.ROUNDED, show_header=False)
        menu_table.add_column("Option", style="cyan", width=8)
        menu_table.add_column("Description", style="white")
        
        options = [
            ("1", "➕ Add New Server"),
            ("2", "🔌 Connect to Server"),
            ("3", "🔌 Disconnect Server"),
            ("4", "🔌 Connect All Servers"),
            ("5", "❌ Remove Server"),
            ("6", "ℹ️  Server Details"),
            ("0", "🔙 Back"),
        ]
        
        for option, desc in options:
            menu_table.add_row(option, desc)
        
        console.print(menu_table)
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6"], default="0")
        
        if choice == "0":
            break
        elif choice == "1":
            add_server_interactive(mcp_manager, registry, console)
        elif choice == "2":
            connect_server_interactive(mcp_manager, console)
        elif choice == "3":
            disconnect_server_interactive(mcp_manager, console)
        elif choice == "4":
            console.print("🔌 Connecting to all servers...")
            results = mcp_manager.connect_all_servers()
            for name, success in results.items():
                status = "✅" if success else "❌"
                console.print(f"{status} {name}")
            input("Press Enter to continue...")
        elif choice == "5":
            remove_server_interactive(mcp_manager, console)
        elif choice == "6":
            show_server_details(mcp_manager, console)


def add_server_interactive(mcp_manager: MCPManager, registry: MCPServerRegistry, console: Console):
    """Add server interactively."""
    console.print(Panel.fit("➕ Add New MCP Server", style="bold green"))
    
    # Ask if user wants to use a template
    use_template = Confirm.ask("Use a server template?", default=True)
    
    if use_template:
        # Show available templates
        templates = registry.list_templates()
        if not templates:
            console.print("❌ No templates available", style="red")
            input("Press Enter to continue...")
            return
        
        template_table = Table(title="Available Templates", box=rich.box.ROUNDED)
        template_table.add_column("Option", style="cyan", width=8)
        template_table.add_column("Name", style="green")
        template_table.add_column("Description", style="white")
        
        for i, template in enumerate(templates, 1):
            template_table.add_row(
                str(i),
                template['name'],
                template['description'][:60] + "..." if len(template['description']) > 60 else template['description']
            )
        
        console.print(template_table)
        
        try:
            choice = IntPrompt.ask(f"Select template (1-{len(templates)})", default=1)
            if 1 <= choice <= len(templates):
                template_name = templates[choice - 1]['name']
                template = registry.get_template(template_name)
                
                # Show installation instructions if needed
                if template.install_instructions:
                    console.print(f"📦 Installation required: {template.install_instructions}", style="yellow")
                    if not Confirm.ask("Continue with this template?"):
                        return
                
                # Configure server name
                server_name = Prompt.ask("Server name", default=template.name)
                
                # Add server
                success = mcp_manager.add_server(
                    name=server_name,
                    command=template.command,
                    args=template.args or [],
                    env=template.env or {},
                    description=template.description
                )
                
                if success:
                    console.print(f"✅ Added server: {server_name}", style="green")
                    
                    # Ask if user wants to connect immediately
                    if Confirm.ask("Connect to server now?", default=True):
                        if mcp_manager.connect_server(server_name):
                            console.print(f"✅ Connected to {server_name}", style="green")
                        else:
                            console.print(f"❌ Failed to connect to {server_name}", style="red")
                else:
                    console.print("❌ Failed to add server", style="red")
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")
    else:
        # Manual configuration
        name = Prompt.ask("Server name")
        command = Prompt.ask("Command (space-separated)").split()
        args = Prompt.ask("Arguments (optional)", default="").split() if Prompt.ask("Arguments (optional)", default="") else []
        description = Prompt.ask("Description (optional)", default="")
        
        success = mcp_manager.add_server(
            name=name,
            command=command,
            args=args,
            description=description
        )
        
        if success:
            console.print(f"✅ Added server: {name}", style="green")
        else:
            console.print("❌ Failed to add server", style="red")
    
    input("Press Enter to continue...")


def connect_server_interactive(mcp_manager: MCPManager, console: Console):
    """Connect to server interactively."""
    servers = mcp_manager.list_configured_servers()
    disconnected = [s for s in servers if not s['connected']]
    
    if not disconnected:
        console.print("ℹ️  All servers are already connected", style="blue")
        input("Press Enter to continue...")
        return
    
    console.print("🔌 Select server to connect:")
    for i, server in enumerate(disconnected, 1):
        console.print(f"  {i}. {server['name']} - {server['description']}")
    
    try:
        choice = IntPrompt.ask(f"Select server (1-{len(disconnected)})")
        if 1 <= choice <= len(disconnected):
            server_name = disconnected[choice - 1]['name']
            
            console.print(f"🔌 Connecting to {server_name}...")
            if mcp_manager.connect_server(server_name):
                console.print(f"✅ Connected to {server_name}", style="green")
            else:
                console.print(f"❌ Failed to connect to {server_name}", style="red")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
    
    input("Press Enter to continue...")


def disconnect_server_interactive(mcp_manager: MCPManager, console: Console):
    """Disconnect from server interactively."""
    servers = mcp_manager.list_configured_servers()
    connected = [s for s in servers if s['connected']]
    
    if not connected:
        console.print("ℹ️  No servers are connected", style="blue")
        input("Press Enter to continue...")
        return
    
    console.print("🔌 Select server to disconnect:")
    for i, server in enumerate(connected, 1):
        console.print(f"  {i}. {server['name']} - {server['description']}")
    
    try:
        choice = IntPrompt.ask(f"Select server (1-{len(connected)})")
        if 1 <= choice <= len(connected):
            server_name = connected[choice - 1]['name']
            
            console.print(f"🔌 Disconnecting from {server_name}...")
            if mcp_manager.disconnect_server(server_name):
                console.print(f"✅ Disconnected from {server_name}", style="green")
            else:
                console.print(f"❌ Failed to disconnect from {server_name}", style="red")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
    
    input("Press Enter to continue...")


def remove_server_interactive(mcp_manager: MCPManager, console: Console):
    """Remove server interactively."""
    servers = mcp_manager.list_configured_servers()
    
    if not servers:
        console.print("ℹ️  No servers configured", style="blue")
        input("Press Enter to continue...")
        return
    
    console.print("❌ Select server to remove:")
    for i, server in enumerate(servers, 1):
        status = "🟢 Connected" if server['connected'] else "🔴 Disconnected"
        console.print(f"  {i}. {server['name']} ({status}) - {server['description']}")
    
    try:
        choice = IntPrompt.ask(f"Select server (1-{len(servers)})")
        if 1 <= choice <= len(servers):
            server_name = servers[choice - 1]['name']
            
            if Confirm.ask(f"Remove server '{server_name}'? This cannot be undone!"):
                if mcp_manager.remove_server(server_name):
                    console.print(f"✅ Removed server: {server_name}", style="green")
                else:
                    console.print(f"❌ Failed to remove server: {server_name}", style="red")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
    
    input("Press Enter to continue...")


def show_server_details(mcp_manager: MCPManager, console: Console):
    """Show detailed server information."""
    servers = mcp_manager.list_configured_servers()
    
    if not servers:
        console.print("ℹ️  No servers configured", style="blue")
        input("Press Enter to continue...")
        return
    
    console.print("ℹ️  Select server for details:")
    for i, server in enumerate(servers, 1):
        status = "🟢 Connected" if server['connected'] else "🔴 Disconnected"
        console.print(f"  {i}. {server['name']} ({status})")
    
    try:
        choice = IntPrompt.ask(f"Select server (1-{len(servers)})")
        if 1 <= choice <= len(servers):
            server_name = servers[choice - 1]['name']
            
            console.clear()
            console.print(Panel.fit(f"📊 Server Details: {server_name}", style="bold blue"))
            
            # Get server status
            status = mcp_manager.get_server_status()[server_name]
            
            details_table = Table(box=rich.box.ROUNDED, show_header=False)
            details_table.add_column("Property", style="cyan", width=20)
            details_table.add_column("Value", style="white")
            
            details_table.add_row("Name", server_name)
            details_table.add_row("Status", "🟢 Connected" if status['connected'] else "🔴 Disconnected")
            details_table.add_row("Command", status['command'])
            details_table.add_row("Description", status['description'])
            details_table.add_row("Tools Count", str(status['tools_count']))
            details_table.add_row("Resources Count", str(status['resources_count']))
            
            console.print(details_table)
            
            # Show tools if connected
            if status['connected'] and status['tools_count'] > 0:
                tools = mcp_manager.get_available_tools(server_name)
                
                tools_table = Table(title="Available Tools", box=rich.box.ROUNDED)
                tools_table.add_column("Tool Name", style="green")
                tools_table.add_column("Description", style="white")
                
                for tool in tools:
                    tools_table.add_row(
                        tool['name'],
                        tool['description'][:50] + "..." if len(tool['description']) > 50 else tool['description']
                    )
                
                console.print(tools_table)
                
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
    
    input("Press Enter to continue...")


def browse_tools_menu(tool_registry: MCPToolRegistry, console: Console):
    """Browse and use tools menu."""
    while True:
        console.clear()
        console.print(Panel.fit("🛠️  Browse & Use Tools", style="bold green"))
        
        # Show tool summary
        summary = tool_registry.get_tools_summary()
        console.print(f"📊 Total Tools: {summary['total_tools']}")
        console.print(f"📦 Categories: {', '.join(summary['categories'].keys())}")
        console.print(f"🔌 Servers: {', '.join(summary['servers'])}")
        console.print()
        
        # Menu
        menu_table = Table(box=rich.box.ROUNDED, show_header=False)
        menu_table.add_column("Option", style="cyan", width=8)
        menu_table.add_column("Description", style="white")
        
        options = [
            ("1", "📋 List All Tools"),
            ("2", "🏷️  Browse by Category"),
            ("3", "🔍 Search Tools"),
            ("4", "🛠️  Use Tool"),
            ("5", "ℹ️  Tool Details"),
            ("0", "🔙 Back"),
        ]
        
        for option, desc in options:
            menu_table.add_row(option, desc)
        
        console.print(menu_table)
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5"], default="0")
        
        if choice == "0":
            break
        elif choice == "1":
            list_all_tools(tool_registry, console)
        elif choice == "2":
            browse_by_category(tool_registry, console)
        elif choice == "3":
            search_tools_interactive(tool_registry, console)
        elif choice == "4":
            use_tool_interactive(tool_registry, console)
        elif choice == "5":
            show_tool_details(tool_registry, console)


def list_all_tools(tool_registry: MCPToolRegistry, console: Console):
    """List all available tools."""
    console.clear()
    console.print(Panel.fit("📋 All Available Tools", style="bold blue"))
    
    tools = tool_registry.get_tools_by_category()
    
    if not tools:
        console.print("ℹ️  No tools available. Connect to MCP servers first.", style="blue")
        input("Press Enter to continue...")
        return
    
    tools_table = Table(box=rich.box.ROUNDED)
    tools_table.add_column("Tool Name", style="green")
    tools_table.add_column("Category", style="cyan")
    tools_table.add_column("Server", style="yellow")
    tools_table.add_column("Description", style="white")
    
    for tool in tools:
        tools_table.add_row(
            tool.name,
            tool.category,
            tool.server_name,
            tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
        )
    
    console.print(tools_table)
    input("Press Enter to continue...")


def browse_by_category(tool_registry: MCPToolRegistry, console: Console):
    """Browse tools by category."""
    console.clear()
    console.print(Panel.fit("🏷️  Browse Tools by Category", style="bold blue"))
    
    categories = tool_registry.get_available_categories()
    
    if not categories:
        console.print("ℹ️  No categories available", style="blue")
        input("Press Enter to continue...")
        return
    
    console.print("📋 Available Categories:")
    for i, category in enumerate(categories, 1):
        tools_count = len(tool_registry.get_tools_by_category(category))
        console.print(f"  {i}. {category} ({tools_count} tools)")
    
    try:
        choice = IntPrompt.ask(f"Select category (1-{len(categories)})")
        if 1 <= choice <= len(categories):
            category = categories[choice - 1]
            tools = tool_registry.get_tools_by_category(category)
            
            console.clear()
            console.print(Panel.fit(f"🏷️  {category.title()} Tools", style="bold blue"))
            
            tools_table = Table(box=rich.box.ROUNDED)
            tools_table.add_column("Tool Name", style="green")
            tools_table.add_column("Server", style="yellow")
            tools_table.add_column("Description", style="white")
            tools_table.add_column("Example", style="cyan")
            
            for tool in tools:
                tools_table.add_row(
                    tool.name,
                    tool.server_name,
                    tool.description[:40] + "..." if len(tool.description) > 40 else tool.description,
                    tool.example_usage[:30] + "..." if tool.example_usage and len(tool.example_usage) > 30 else tool.example_usage or "N/A"
                )
            
            console.print(tools_table)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
    
    input("Press Enter to continue...")


def search_tools_interactive(tool_registry: MCPToolRegistry, console: Console):
    """Search tools interactively."""
    console.clear()
    console.print(Panel.fit("🔍 Search Tools", style="bold blue"))
    
    query = Prompt.ask("Search query")
    tools = tool_registry.search_tools(query)
    
    if not tools:
        console.print(f"ℹ️  No tools found matching '{query}'", style="blue")
        input("Press Enter to continue...")
        return
    
    console.print(f"🔍 Found {len(tools)} tools matching '{query}':")
    
    tools_table = Table(box=rich.box.ROUNDED)
    tools_table.add_column("Tool Name", style="green")
    tools_table.add_column("Category", style="cyan")
    tools_table.add_column("Server", style="yellow")
    tools_table.add_column("Description", style="white")
    
    for tool in tools:
        tools_table.add_row(
            tool.name,
            tool.category,
            tool.server_name,
            tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
        )
    
    console.print(tools_table)
    input("Press Enter to continue...")


def use_tool_interactive(tool_registry: MCPToolRegistry, console: Console):
    """Use a tool interactively."""
    console.clear()
    console.print(Panel.fit("🛠️  Use Tool", style="bold blue"))
    
    tools = tool_registry.get_tools_by_category()
    
    if not tools:
        console.print("ℹ️  No tools available", style="blue")
        input("Press Enter to continue...")
        return
    
    # Show available tools
    console.print("🛠️  Available Tools:")
    for i, tool in enumerate(tools, 1):
        console.print(f"  {i}. {tool.name} ({tool.category}) - {tool.description[:60]}")
    
    try:
        choice = IntPrompt.ask(f"Select tool (1-{len(tools)})")
        if 1 <= choice <= len(tools):
            tool = tools[choice - 1]
            
            console.print(f"\n🛠️  Using tool: {tool.name}")
            console.print(f"📄 Description: {tool.description}")
            
            if tool.example_usage:
                console.print(f"💡 Example: {tool.example_usage}")
            
            # Get tool schema
            schema = tool.input_schema
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            # Collect arguments
            arguments = {}
            console.print("\n📝 Enter tool arguments:")
            
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'string')
                prop_desc = prop_info.get('description', '')
                is_required = prop_name in required
                
                prompt_text = f"{prop_name}"
                if prop_desc:
                    prompt_text += f" ({prop_desc})"
                if is_required:
                    prompt_text += " [REQUIRED]"
                
                if prop_type == 'boolean':
                    value = Confirm.ask(prompt_text, default=False)
                else:
                    value = Prompt.ask(prompt_text, default="" if not is_required else None)
                    
                    if value:  # Only add non-empty values
                        # Convert types
                        if prop_type == 'integer':
                            try:
                                value = int(value)
                            except ValueError:
                                console.print(f"⚠️  Invalid integer value for {prop_name}", style="yellow")
                                continue
                        elif prop_type == 'array':
                            value = value.split(',') if ',' in value else [value]
                
                if value or is_required:
                    arguments[prop_name] = value
            
            # Validate and call tool
            if tool_registry.validate_tool_arguments(tool.name, arguments):
                console.print(f"\n🚀 Calling tool: {tool.name}")
                console.print(f"📊 Arguments: {arguments}")
                
                try:
                    result = tool_registry.call_tool(tool.name, arguments)
                    console.print(f"\n✅ Result:", style="green")
                    console.print(result)
                except Exception as e:
                    console.print(f"\n❌ Error calling tool: {e}", style="red")
            else:
                console.print("❌ Invalid arguments", style="red")
                
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
    
    input("Press Enter to continue...")


def show_tool_details(tool_registry: MCPToolRegistry, console: Console):
    """Show detailed tool information."""
    console.clear()
    console.print(Panel.fit("ℹ️  Tool Details", style="bold blue"))
    
    tool_name = Prompt.ask("Tool name")
    tool = tool_registry.get_tool(tool_name)
    
    if not tool:
        console.print(f"❌ Tool '{tool_name}' not found", style="red")
        input("Press Enter to continue...")
        return
    
    # Show tool details
    details_table = Table(box=rich.box.ROUNDED, show_header=False)
    details_table.add_column("Property", style="cyan", width=20)
    details_table.add_column("Value", style="white")
    
    details_table.add_row("Name", tool.name)
    details_table.add_row("Category", tool.category)
    details_table.add_row("Server", tool.server_name)
    details_table.add_row("Description", tool.description)
    details_table.add_row("Example Usage", tool.example_usage or "N/A")
    
    console.print(details_table)
    
    # Show schema
    if tool.input_schema:
        console.print("\n📋 Input Schema:")
        properties = tool.input_schema.get('properties', {})
        required = tool.input_schema.get('required', [])
        
        if properties:
            schema_table = Table(box=rich.box.ROUNDED)
            schema_table.add_column("Parameter", style="green")
            schema_table.add_column("Type", style="cyan")
            schema_table.add_column("Required", style="yellow")
            schema_table.add_column("Description", style="white")
            
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'string')
                is_required = "Yes" if prop_name in required else "No"
                description = prop_info.get('description', 'No description')
                
                schema_table.add_row(prop_name, prop_type, is_required, description)
            
            console.print(schema_table)
    
    input("Press Enter to continue...")


def install_templates_menu(mcp_manager: MCPManager, registry: MCPServerRegistry, console: Console):
    """Install server templates menu."""
    console.clear()
    console.print(Panel.fit("📦 Install Server Templates", style="bold green"))
    
    templates = registry.list_templates()
    
    if not templates:
        console.print("ℹ️  No templates available", style="blue")
        input("Press Enter to continue...")
        return
    
    # Group by categories
    categories = registry.get_categories()
    
    for category, template_names in categories.items():
        console.print(f"\n🏷️  {category}:")
        for template_name in template_names:
            template_info = next((t for t in templates if t['name'] == template_name), None)
            if template_info:
                console.print(f"  • {template_info['name']} - {template_info['description']}")
    
    console.print("\n📋 Available Templates:")
    template_table = Table(box=rich.box.ROUNDED)
    template_table.add_column("Option", style="cyan", width=8)
    template_table.add_column("Name", style="green")
    template_table.add_column("Description", style="white")
    template_table.add_column("Installation", style="yellow")
    
    for i, template in enumerate(templates, 1):
        template_table.add_row(
            str(i),
            template['name'],
            template['description'][:50] + "..." if len(template['description']) > 50 else template['description'],
            template['install_instructions'] or "No installation needed"
        )
    
    console.print(template_table)
    
    try:
        choice = IntPrompt.ask(f"Select template to install (1-{len(templates)})", default=1)
        if 1 <= choice <= len(templates):
            template_info = templates[choice - 1]
            
            console.print(f"\n📦 Installing template: {template_info['name']}")
            console.print(f"📄 Description: {template_info['description']}")
            
            if template_info['install_instructions']:
                console.print(f"💡 Installation: {template_info['install_instructions']}")
                
                if Confirm.ask("Run installation command?"):
                    # Here you could add actual installation logic
                    console.print("ℹ️  Please run the installation command manually", style="blue")
            
            # Add server configuration
            if Confirm.ask("Add server configuration?", default=True):
                template = registry.get_template(template_info['name'])
                server_name = Prompt.ask("Server name", default=template.name)
                
                success = mcp_manager.add_server(
                    name=server_name,
                    command=template.command,
                    args=template.args or [],
                    env=template.env or {},
                    description=template.description
                )
                
                if success:
                    console.print(f"✅ Added server configuration: {server_name}", style="green")
                else:
                    console.print("❌ Failed to add server configuration", style="red")
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
    
    input("Press Enter to continue...")


def show_server_status(mcp_manager: MCPManager, console: Console):
    """Show server status and information."""
    console.clear()
    console.print(Panel.fit("📊 Server Status & Information", style="bold blue"))
    
    status = mcp_manager.get_server_status()
    
    if not status:
        console.print("ℹ️  No servers configured", style="blue")
        input("Press Enter to continue...")
        return
    
    # Overall status
    total_servers = len(status)
    connected_servers = sum(1 for s in status.values() if s['connected'])
    total_tools = sum(s['tools_count'] for s in status.values())
    total_resources = sum(s['resources_count'] for s in status.values())
    
    summary_table = Table(title="Overall Status", box=rich.box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("Total Servers", str(total_servers))
    summary_table.add_row("Connected Servers", str(connected_servers))
    summary_table.add_row("Total Tools", str(total_tools))
    summary_table.add_row("Total Resources", str(total_resources))
    
    console.print(summary_table)
    
    # Individual server status
    servers_table = Table(title="Server Details", box=rich.box.ROUNDED)
    servers_table.add_column("Server", style="green")
    servers_table.add_column("Status", style="yellow")
    servers_table.add_column("Tools", style="cyan")
    servers_table.add_column("Resources", style="blue")
    servers_table.add_column("Command", style="white")
    
    for name, info in status.items():
        status_text = "🟢 Connected" if info['connected'] else "🔴 Disconnected"
        command = info['command'][:30] + "..." if len(info['command']) > 30 else info['command']
        
        servers_table.add_row(
            name,
            status_text,
            str(info['tools_count']),
            str(info['resources_count']),
            command
        )
    
    console.print(servers_table)
    input("Press Enter to continue...")


def test_tools_menu(tool_registry: MCPToolRegistry, console: Console):
    """Test tools menu."""
    console.clear()
    console.print(Panel.fit("🔧 Test Tools", style="bold green"))
    
    # Show some quick test options
    console.print("🔧 Quick Tests:")
    console.print("  1. Test Calculator (if available)")
    console.print("  2. Test DateTime (if available)")
    console.print("  3. Test System Info (if available)")
    console.print("  4. Custom Tool Test")
    
    choice = Prompt.ask("Select test", choices=["1", "2", "3", "4"], default="4")
    
    if choice == "1":
        test_calculator_tool(tool_registry, console)
    elif choice == "2":
        test_datetime_tool(tool_registry, console)
    elif choice == "3":
        test_system_tool(tool_registry, console)
    elif choice == "4":
        use_tool_interactive(tool_registry, console)


def test_calculator_tool(tool_registry: MCPToolRegistry, console: Console):
    """Test calculator tool."""
    calc_tools = [t for t in tool_registry.get_tools_by_category() if 'calc' in t.name.lower()]
    
    if not calc_tools:
        console.print("❌ No calculator tools available", style="red")
        input("Press Enter to continue...")
        return
    
    tool = calc_tools[0]
    console.print(f"🧮 Testing calculator tool: {tool.name}")
    
    try:
        result = tool_registry.call_tool(tool.name, {"expression": "2 + 2 * 3"})
        console.print(f"✅ Test result: {result}", style="green")
    except Exception as e:
        console.print(f"❌ Test failed: {e}", style="red")
    
    input("Press Enter to continue...")


def test_datetime_tool(tool_registry: MCPToolRegistry, console: Console):
    """Test datetime tool."""
    datetime_tools = [t for t in tool_registry.get_tools_by_category() if 'time' in t.name.lower() or 'date' in t.name.lower()]
    
    if not datetime_tools:
        console.print("❌ No datetime tools available", style="red")
        input("Press Enter to continue...")
        return
    
    tool = datetime_tools[0]
    console.print(f"📅 Testing datetime tool: {tool.name}")
    
    try:
        result = tool_registry.call_tool(tool.name, {})
        console.print(f"✅ Test result: {result}", style="green")
    except Exception as e:
        console.print(f"❌ Test failed: {e}", style="red")
    
    input("Press Enter to continue...")


def test_system_tool(tool_registry: MCPToolRegistry, console: Console):
    """Test system tool."""
    system_tools = [t for t in tool_registry.get_tools_by_category() if 'system' in t.name.lower()]
    
    if not system_tools:
        console.print("❌ No system tools available", style="red")
        input("Press Enter to continue...")
        return
    
    tool = system_tools[0]
    console.print(f"💻 Testing system tool: {tool.name}")
    
    try:
        result = tool_registry.call_tool(tool.name, {})
        console.print(f"✅ Test result: {result}", style="green")
    except Exception as e:
        console.print(f"❌ Test failed: {e}", style="red")
    
    input("Press Enter to continue...")


def mcp_settings_menu(mcp_manager: MCPManager, console: Console):
    """MCP settings menu."""
    console.clear()
    console.print(Panel.fit("⚙️  MCP Settings", style="bold blue"))
    
    console.print("⚙️  MCP Configuration Settings:")
    console.print("  - Auto-connect to servers on startup")
    console.print("  - Connection timeout settings")
    console.print("  - Retry settings")
    console.print("  - Tool execution timeout")
    
    console.print("\nℹ️  Current settings are managed in the main OrionAI configuration.", style="blue")
    console.print("🔧 Use the main settings menu to modify MCP configuration.", style="blue")
    
    input("Press Enter to continue...")
