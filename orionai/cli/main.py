"""
Main CLI Interface for OrionAI
==============================

Rich CLI interface with session management and LLM selection.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
import rich.box

from .config import ConfigManager
from .session import SessionManager
from .chat import InteractiveChatSession


def create_header() -> Panel:
    """Create the header panel."""
    header_text = Text()
    header_text.append("🚀 ", style="bold yellow")
    header_text.append("OrionAI", style="bold blue")
    header_text.append(" - Interactive LLM Chat with Code Execution", style="bold white")
    
    return Panel(
        Align.center(header_text),
        box=rich.box.DOUBLE,
        style="blue"
    )


def show_llm_selection(config_manager: ConfigManager) -> bool:
    """Show LLM provider selection interface."""
    console = Console()
    
    # Create provider table
    table = Table(title="🤖 Available LLM Providers", box=rich.box.ROUNDED)
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Provider", style="green", width=15)
    table.add_column("Description", style="white")
    table.add_column("Status", style="yellow", width=10)
    
    providers = [
        ("1", "OpenAI", "GPT-3.5, GPT-4 models", "✅ Available"),
        ("2", "Anthropic", "Claude models", "✅ Available"),
        ("3", "Google", "Gemini models", "✅ Available"),
    ]
    
    for option, provider, desc, status in providers:
        table.add_row(option, provider, desc, status)
    
    console.print(table)
    
    # Current configuration
    current = config_manager.config.llm
    if current.provider and current.model:
        console.print(f"\n📋 Current: {current.provider} ({current.model})")
    
    # Get user choice
    choice = Prompt.ask(
        "\nSelect provider or press Enter to use current",
        choices=["1", "2", "3", ""], 
        default=""
    )
    
    if choice:
        provider_map = {"1": "openai", "2": "anthropic", "3": "google"}
        provider = provider_map[choice]
        
        # Setup the provider
        return config_manager.setup_llm_provider(provider)
    
    # Check if current config is valid
    if not current.provider or not config_manager.get_api_key():
        console.print("❌ No valid LLM configuration found.", style="red")
        setup = Confirm.ask("Setup LLM provider now?")
        if setup:
            return config_manager.setup_llm_provider()
        return False
    
    return True


def show_session_selection(session_manager: SessionManager, console: Console) -> Optional[str]:
    """Show session selection interface."""
    sessions = session_manager.list_sessions()
    
    # Create sessions table
    table = Table(title="📝 Available Sessions", box=rich.box.ROUNDED)
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Session ID", style="green", width=12)
    table.add_column("Title", style="white", width=30)
    table.add_column("Messages", style="yellow", width=10)
    table.add_column("Updated", style="blue")
    
    # Add new session option
    table.add_row("0", "NEW", "Create New Session", "-", "-")
    
    # Add existing sessions
    for i, session in enumerate(sessions[:9], 1):  # Limit to 9 sessions
        updated = session["updated_at"][:16].replace("T", " ")
        table.add_row(
            str(i),
            session["session_id"],
            session["title"][:30],
            str(session["total_messages"]),
            updated
        )
    
    console.print(table)
    
    if not sessions:
        console.print("ℹ️  No existing sessions found. Creating new session...", style="blue")
        return None
    
    # Get user choice
    max_choice = min(len(sessions), 9)
    choice = IntPrompt.ask(
        f"Select session (0 for new, 1-{max_choice})",
        default=0
    )
    
    if choice == 0:
        return None
    elif 1 <= choice <= len(sessions):
        return sessions[choice - 1]["session_id"]
    else:
        console.print("❌ Invalid choice", style="red")
        return show_session_selection(session_manager, console)


def create_new_session(session_manager: SessionManager, config_manager: ConfigManager, auto_start_chat: bool = False) -> bool:
    """Create a new session interactively."""
    console = Console()
    
    console.print(Panel.fit("📝 Create New Session", style="bold green"))
    
    # Get session title
    title = Prompt.ask("Session title", default=f"Session {session_manager.sessions_dir.name}")
    
    # Confirm LLM settings
    llm_config = config_manager.config.llm
    console.print(f"🤖 Using: {llm_config.provider} ({llm_config.model})")
    
    change_llm = Confirm.ask("Change LLM settings?", default=False)
    if change_llm:
        show_llm_selection(config_manager)
    
    # Create session
    session_id = session_manager.create_session(
        title=title,
        llm_provider=config_manager.config.llm.provider,
        llm_model=config_manager.config.llm.model
    )
    
    console.print(f"✅ Created session: {session_id}", style="green")
    
    # Ask if user wants to start chatting immediately
    if auto_start_chat or Confirm.ask("🚀 Start chatting now?", default=True):
        console.clear()
        chat_session = InteractiveChatSession(config_manager, session_manager)
        chat_session.run()
        return True
    
    return True


def show_main_menu(config_manager: ConfigManager, session_manager: SessionManager):
    """Show the main menu and handle user choices."""
    console = Console()
    
    # Initialize and auto-connect MCP servers on first load
    try:
        from ..mcp.manager import MCPManager
        mcp_manager = MCPManager(config_manager.config_dir)
        mcp_manager.connect_all_servers()
    except Exception as e:
        # Silently handle MCP connection errors to not disrupt main menu
        pass
    
    # Initialize console with better handling
    console = Console(force_terminal=True, width=None)
    
    # Track if this is the first display
    first_display = True
    
    while True:
        # Only clear on first display or when explicitly needed
        if first_display:
            console.clear()
            first_display = False
        else:
            # Just add some spacing instead of clearing
            console.print("\n" * 2)
        
        console.print(create_header())
        
        # Show current status
        status_text = Text()
        
        # LLM Status
        llm_config = config_manager.config.llm
        if llm_config.provider and config_manager.get_api_key():
            status_text.append("🤖 LLM: ", style="bold")
            status_text.append(f"{llm_config.provider} ({llm_config.model})", style="green")
        else:
            status_text.append("🤖 LLM: ", style="bold")
            status_text.append("Not configured", style="red")
        
        status_text.append(" | ")
        
        # Session Status
        if session_manager.current_session:
            status_text.append("📝 Session: ", style="bold")
            status_text.append(session_manager.current_session.session_id, style="green")
        else:
            status_text.append("📝 Session: ", style="bold")
            status_text.append("None", style="yellow")
        
        console.print(Panel(Align.center(status_text), style="blue"))
        
        # Menu options
        # Create enhanced menu with individual rows
        menu_table = Table(title="🎯 Main Menu", box=rich.box.ROUNDED, show_header=False)
        menu_table.add_column("Option", style="cyan", width=8)
        menu_table.add_column("Description", style="white")
        
        # Add each option with individual separators
        menu_table.add_row("1", "🚀 Start Interactive Chat")
        menu_table.add_section()
        menu_table.add_row("2", "📝 Manage Sessions")
        menu_table.add_section()
        menu_table.add_row("3", "🤖 Configure LLM Provider")
        menu_table.add_section()
        menu_table.add_row("4", "🔌 MCP Local Servers (Manage existing)")
        menu_table.add_section()
        menu_table.add_row("5", "📦 Browse & Install MCP Servers (396+ available)")
        menu_table.add_section()
        menu_table.add_row("6", " Live Code Editor")
        menu_table.add_section()
        menu_table.add_row("7", "⚙️ Settings")
        menu_table.add_section()
        menu_table.add_row("0", "🚪 Exit")
        
        console.print(menu_table)
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="1")
        
        if choice == "0":
            console.print("👋 Goodbye!", style="yellow")
            sys.exit(0)
        
        elif choice == "1":
            # Start interactive chat
            if not config_manager.get_api_key():
                console.print("❌ No LLM configured. Please configure first.", style="red")
                input("Press Enter to continue...")
                continue
            
            if not session_manager.current_session:
                console.print("📝 No active session. Please select or create one.")
                session_id = show_session_selection(session_manager, console)
                
                if session_id:
                    if not session_manager.load_session(session_id):
                        console.print("❌ Failed to load session", style="red")
                        input("Press Enter to continue...")
                        continue
                else:
                    # Create new session with auto-start chat option
                    create_new_session(session_manager, config_manager, auto_start_chat=True)
                    # After creating and potentially chatting, continue to main menu
                    continue
            
            # Start chat
            console.clear()
            chat_session = InteractiveChatSession(config_manager, session_manager)
            chat_session.run()
        
        elif choice == "2":
            # Manage sessions
            handle_session_management(session_manager, config_manager, console)
        
        elif choice == "3":
            # Configure LLM
            show_llm_selection(config_manager)
            input("Press Enter to continue...")
        
        elif choice == "4":
            # MCP Management
            from ..mcp.manager import MCPManager
            mcp_manager = MCPManager(config_manager.config_dir)
            from .mcp_interface import show_mcp_main_menu
            show_mcp_main_menu(mcp_manager, console)
        
        elif choice == "5":
            # Interactive MCP Server Manager
            console.print("🚀 Starting Interactive MCP Server Manager...", style="blue")
            try:
                from ..mcp.interactive_mcp_manager import InteractiveMCPManager
                import asyncio
                
                manager = InteractiveMCPManager(config_manager.config_dir / "mcp")
                asyncio.run(manager.run())
                
            except Exception as e:
                console.print(f"❌ Failed to start MCP manager: {e}", style="red")
                console.print("Please check that all dependencies are installed.", style="yellow")
                input("Press Enter to continue...")
        
        elif choice == "6":
            # Live Code Editor  
            from .live_code import show_live_code_menu
            # Create LLM interface using the same config if LLM is configured
            llm_interface = None
            try:
                api_key = config_manager.get_api_key()
                if api_key and hasattr(config_manager.config, 'llm') and hasattr(config_manager.config.llm, 'provider'):
                    from ..core.llm_interface import LLMInterface, OpenAIProvider, AnthropicProvider, GoogleProvider
                    
                    provider_classes = {
                        "openai": OpenAIProvider,
                        "anthropic": AnthropicProvider,
                        "google": GoogleProvider
                    }
                    
                    provider_class = provider_classes.get(config_manager.config.llm.provider)
                    if provider_class:
                        model = getattr(config_manager.config.llm, 'model', None)
                        provider = provider_class(
                            api_key=api_key,
                            model=model
                        )
                        llm_interface = LLMInterface(provider=provider)
                        console.print("[dim green]✅ LLM interface initialized for code editor[/dim green]")
                    else:
                        console.print(f"[yellow]⚠️  Unknown LLM provider: {config_manager.config.llm.provider}[/yellow]")
                else:
                    console.print("[yellow]⚠️  No LLM configuration found - proceeding without AI suggestions[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not initialize LLM interface: {e}[/yellow]")
                console.print("[dim]Code editor will work without AI suggestions[/dim]")
            
            show_live_code_menu(llm_interface)
        
        elif choice == "7":
            # Settings
            handle_settings(config_manager, console)


def handle_session_management(session_manager: SessionManager, config_manager: ConfigManager, console: Console):
    """Handle session management operations."""
    while True:
        console.clear()
        console.print(Panel.fit("📝 Session Management", style="bold blue"))
        
        # Show current session
        if session_manager.current_session:
            current_info = f"Current: {session_manager.current_session.session_id} - {session_manager.current_session.title}"
            console.print(Panel(current_info, style="green"))
        
        # Menu
        session_menu = Table(box=rich.box.ROUNDED, show_header=False)
        session_menu.add_column("Option", style="cyan", width=8)
        session_menu.add_column("Description", style="white")
        
        options = [
            ("1", "📝 Create New Session"),
            ("2", "📂 Load Existing Session"),
            ("3", "� Start Chat with Current Session") if session_manager.current_session else None,
            ("4", "�🗑️  Delete Session"),
            ("5", "📤 Export Session"),
            ("6", "📋 List All Sessions"),
            ("0", "🔙 Back to Main Menu"),
        ]
        
        # Filter out None options
        options = [(opt, desc) for opt, desc in options if desc is not None]
        
        for option, desc in options:
            session_menu.add_row(option, desc)
        
        console.print(session_menu)
        
        # Build valid choices based on available options
        valid_choices = [opt for opt, _ in options]
        choice = Prompt.ask("Select option", choices=valid_choices, default="0")
        
        if choice == "0":
            break
        elif choice == "1":
            create_new_session(session_manager, config_manager)
        elif choice == "2":
            session_id = show_session_selection(session_manager, console)
            if session_id and session_manager.load_session(session_id):
                console.print(f"✅ Loaded session: {session_id}", style="green")
                
                # Ask if user wants to start chatting immediately
                if Confirm.ask("🚀 Start chatting now?", default=True):
                    console.clear()
                    chat_session = InteractiveChatSession(config_manager, session_manager)
                    chat_session.run()
                    # After chat ends, break out of session management to main menu
                    break
            elif session_id:
                console.print("❌ Failed to load session", style="red")
        elif choice == "3" and session_manager.current_session:
            # Start chat with current session
            console.clear()
            chat_session = InteractiveChatSession(config_manager, session_manager)
            chat_session.run()
            break
        elif choice == "4":
            # Delete session
            sessions = session_manager.list_sessions()
            if not sessions:
                console.print("ℹ️  No sessions to delete", style="blue")
            else:
                console.print("🗑️  Select session to delete:")
                session_id = show_session_selection(session_manager, console)
                if session_id:
                    confirm = Confirm.ask(f"Delete session {session_id}? This cannot be undone!")
                    if confirm and session_manager.delete_session(session_id):
                        console.print("✅ Session deleted", style="green")
                        if session_manager.current_session and session_manager.current_session.session_id == session_id:
                            session_manager.current_session = None
        elif choice == "5":
            # Export session
            sessions = session_manager.list_sessions()
            if not sessions:
                console.print("ℹ️  No sessions to export", style="blue")
            else:
                session_id = show_session_selection(session_manager, console)
                if session_id:
                    export_path = Path(Prompt.ask("Export path", default=f"session_{session_id}.json"))
                    if session_manager.export_session(session_id, export_path):
                        console.print(f"✅ Session exported to {export_path}", style="green")
        elif choice == "6":
            # List sessions
            sessions = session_manager.list_sessions()
            if sessions:
                show_session_selection(session_manager, console)
            else:
                console.print("ℹ️  No sessions found", style="blue")
        
        if choice != "0":
            input("Press Enter to continue...")


def handle_settings(config_manager: ConfigManager, console: Console):
    """Handle settings configuration."""
    console.clear()
    console.print(Panel.fit("⚙️  Settings", style="bold blue"))
    
    # Show current settings
    config = config_manager.config
    
    settings_table = Table(title="Current Settings", box=rich.box.ROUNDED)
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="white")
    
    settings_table.add_row("LLM Provider", config.llm.provider)
    settings_table.add_row("LLM Model", config.llm.model)
    settings_table.add_row("Temperature", str(config.llm.temperature))
    settings_table.add_row("Max Tokens", str(config.llm.max_tokens))
    settings_table.add_row("Auto Save", str(config.session.auto_save))
    settings_table.add_row("Code Execution", str(config.session.enable_code_execution))
    settings_table.add_row("Max History", str(config.session.max_history))
    
    console.print(settings_table)
    
    # Settings menu
    if Confirm.ask("Modify settings?"):
        # Temperature
        new_temp = Prompt.ask(f"Temperature (current: {config.llm.temperature})", default=str(config.llm.temperature))
        try:
            config.llm.temperature = float(new_temp)
        except ValueError:
            pass
        
        # Max tokens
        new_tokens = Prompt.ask(f"Max tokens (current: {config.llm.max_tokens})", default=str(config.llm.max_tokens))
        try:
            config.llm.max_tokens = int(new_tokens)
        except ValueError:
            pass
        
        # Auto save
        config.session.auto_save = Confirm.ask(f"Auto save (current: {config.session.auto_save})", default=config.session.auto_save)
        
        # Code execution
        config.session.enable_code_execution = Confirm.ask(f"Enable code execution (current: {config.session.enable_code_execution})", default=config.session.enable_code_execution)
        
        config_manager.save_config()
        console.print("✅ Settings saved!", style="green")
    
    input("Press Enter to continue...")


def show_session_statistics(session_manager: SessionManager, console: Console):
    """Show session statistics."""
    console.clear()
    console.print(Panel.fit("📊 Session Statistics", style="bold blue"))
    
    sessions = session_manager.list_sessions()
    
    if not sessions:
        console.print("ℹ️  No sessions found", style="blue")
        input("Press Enter to continue...")
        return
    
    # Overall statistics
    total_sessions = len(sessions)
    total_messages = sum(s["total_messages"] for s in sessions)
    
    providers = {}
    for session in sessions:
        provider = session["llm_provider"]
        providers[provider] = providers.get(provider, 0) + 1
    
    # Statistics table
    stats_table = Table(title="Overall Statistics", box=rich.box.ROUNDED)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="white")
    
    stats_table.add_row("Total Sessions", str(total_sessions))
    stats_table.add_row("Total Messages", str(total_messages))
    stats_table.add_row("Avg Messages/Session", f"{total_messages/total_sessions:.1f}" if total_sessions > 0 else "0")
    
    for provider, count in providers.items():
        stats_table.add_row(f"Sessions ({provider})", str(count))
    
    console.print(stats_table)
    
    # Recent sessions
    recent_table = Table(title="Recent Sessions", box=rich.box.ROUNDED)
    recent_table.add_column("ID", style="green")
    recent_table.add_column("Title", style="white")
    recent_table.add_column("Messages", style="yellow")
    recent_table.add_column("Provider", style="cyan")
    recent_table.add_column("Updated", style="blue")
    
    for session in sessions[:5]:  # Show last 5 sessions
        updated = session["updated_at"][:16].replace("T", " ")
        recent_table.add_row(
            session["session_id"],
            session["title"][:30],
            str(session["total_messages"]),
            session["llm_provider"],
            updated
        )
    
    console.print(recent_table)
    input("Press Enter to continue...")


class RichHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter that uses Rich for beautiful help output."""
    
    def format_help(self):
        console = Console()
        
        # Create beautiful help display
        console.print(create_header())
        
        # Description
        desc_panel = Panel(
            "🤖 Interactive LLM Chat with Code Execution\n"
            "🚀 Supports multiple LLM providers (OpenAI, Anthropic, Google)\n"
            "💬 Session management and chat history\n"
            "🔧 Live code execution and debugging\n"
            "🎨 Rich terminal interface",
            title="📋 Description",
            style="blue"
        )
        console.print(desc_panel)
        
        # Usage
        usage_table = Table(title="🎯 Usage", box=rich.box.ROUNDED)
        usage_table.add_column("Command", style="cyan")
        usage_table.add_column("Description", style="white")
        
        usage_table.add_row(
            "python -m orionai.cli.main",
            "Start interactive menu (default)"
        )
        usage_table.add_row(
            "python -m orionai.cli.main --help",
            "Show this help message"
        )
        usage_table.add_row(
            "python -m orionai.cli.main --version",
            "Show version information"
        )
        
        console.print(usage_table)
        
        # Options
        options_table = Table(title="⚙️ Options", box=rich.box.ROUNDED)
        options_table.add_column("Option", style="green")
        options_table.add_column("Description", style="white")
        
        options_table.add_row(
            "--config-dir DIR",
            "Custom configuration directory path"
        )
        options_table.add_row(
            "--no-interactive",
            "Disable interactive mode (for scripting)"
        )
        options_table.add_row(
            "--version",
            "Show version and exit"
        )
        options_table.add_row(
            "-h, --help",
            "Show this help message and exit"
        )
        
        console.print(options_table)
        
        # Features
        features_table = Table(title="✨ Features", box=rich.box.ROUNDED)
        features_table.add_column("Feature", style="yellow")
        features_table.add_column("Description", style="white")
        
        features_table.add_row("🚀 Interactive Chat", "Real-time conversations with AI")
        features_table.add_row("📝 Session Management", "Save and resume chat sessions")
        features_table.add_row("🤖 Multi-LLM Support", "OpenAI, Anthropic, Google models")
        features_table.add_row("🔌 MCP Protocol", "Model Context Protocol integration")
        features_table.add_row("🖥️ Local Models", "Run AI models locally")
        features_table.add_row("💻 Live Code Editor", "Execute and debug code in real-time")
        features_table.add_row("🎨 Visual Outputs", "Rich graphics and visualizations")
        
        console.print(features_table)
        
        # Footer
        footer_text = Text()
        footer_text.append("Made with ", style="white")
        footer_text.append("❤️", style="red")
        footer_text.append(" by OrionAI Team", style="white")
        
        console.print(Panel(Align.center(footer_text), style="green"))
        
        return ""  # Return empty string since we've already printed everything


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="OrionAI - Interactive LLM Chat with Code Execution",
        formatter_class=RichHelpFormatter,
        add_help=False  # We'll handle help manually
    )
    
    parser.add_argument(
        "--version", 
        action="store_true",
        help="Show version information"
    )
    
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Show this help message"
    )
    
    parser.add_argument(
        "--config-dir",
        type=str,
        help="Custom configuration directory path"
    )
    
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable interactive mode (for scripting)"
    )
    
    return parser.parse_args()


def show_version():
    """Show version information with rich UI."""
    console = Console()
    
    # Create version display
    version_text = Text()
    version_text.append("🚀 ", style="bold yellow")
    version_text.append("OrionAI CLI ", style="bold blue")
    version_text.append("v1.0.0", style="bold green")
    
    version_panel = Panel(
        Align.center(version_text),
        title="📦 Version Information",
        style="blue"
    )
    
    console.print(version_panel)
    
    # Additional info
    info_table = Table(box=rich.box.ROUNDED, show_header=False)
    info_table.add_column("Item", style="cyan")
    info_table.add_column("Value", style="white")
    
    info_table.add_row("🔧 Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    info_table.add_row("📁 Platform", sys.platform)
    info_table.add_row("🏠 Repository", "https://github.com/AIMLDev726/OrionAI")
    
    console.print(info_table)


def main_cli():
    """Main CLI entry point."""
    try:
        # Parse arguments first
        args = parse_args()
        
        console = Console()
        
        # Handle version flag
        if args.version:
            show_version()
            return
        
        # Handle help flag
        if args.help:
            parser = argparse.ArgumentParser(formatter_class=RichHelpFormatter)
            parser.print_help()
            return
        
        # Initialize managers
        config_manager = ConfigManager()
        session_manager = SessionManager(config_manager)
        
        # If non-interactive mode, just show status and exit
        if args.no_interactive:
            console.print("OrionAI CLI - Non-interactive mode")
            console.print(f"Config directory: {config_manager.config_dir}")
            return
        
        # Check if this is first run
        if not config_manager.config_file.exists():
            console.print(Panel.fit(
                "🎉 Welcome to OrionAI!\n"
                "This appears to be your first time running OrionAI.\n"
                "Let's set up your LLM provider.",
                style="bold green"
            ))
            
            if not show_llm_selection(config_manager):
                console.print("❌ Setup cancelled. Exiting.", style="red")
                return
        
        # Show main menu
        show_main_menu(config_manager, session_manager)
        
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="yellow")
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        console.print_exception()


if __name__ == "__main__":
    main_cli()
