"""
Code Approval and Package Manager
=================================

Handles code execution approval and automatic package installation.
"""

import re
import subprocess
import sys
from typing import List, Set, Tuple, Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
import rich.box


class CodeApprovalManager:
    """Manages code execution approval and package installation."""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.trusted_packages = {
            'numpy', 'pandas', 'matplotlib', 'seaborn', 'plotly',
            'scikit-learn', 'scipy', 'requests', 'beautifulsoup4',
            'pillow', 'opencv-python', 'nltk', 'networkx'
        }
        self.dangerous_patterns = [
            r'import\s+os',
            r'import\s+subprocess',
            r'import\s+shutil',
            r'from\s+os\s+import',
            r'exec\s*\(',
            r'eval\s*\(',
            r'__import__',
            r'open\s*\(',
            r'file\s*\(',
            r'input\s*\(',
            r'raw_input\s*\(',
            r'compile\s*\(',
        ]
    
    def extract_imports(self, code: str) -> Set[str]:
        """Extract package imports from code."""
        imports = set()
        
        # Match import statements
        import_patterns = [
            r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import',
        ]
        
        for line in code.split('\n'):
            line = line.strip()
            for pattern in import_patterns:
                match = re.match(pattern, line)
                if match:
                    package = match.group(1)
                    imports.add(package)
        
        return imports
    
    def check_package_availability(self, packages: Set[str]) -> Tuple[Set[str], Set[str]]:
        """Check which packages are available and which need installation."""
        available = set()
        missing = set()
        
        for package in packages:
            try:
                __import__(package)
                available.add(package)
            except ImportError:
                missing.add(package)
        
        return available, missing
    
    def analyze_code_safety(self, code: str) -> Tuple[bool, List[str]]:
        """Analyze code for potentially dangerous operations."""
        warnings = []
        is_safe = True
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                warnings.append(f"Potentially dangerous operation: {pattern}")
                is_safe = False
        
        # Check for suspicious file operations
        if 'open(' in code and ('w' in code or 'a' in code):
            warnings.append("File write operations detected")
            is_safe = False
        
        # Check for network operations
        if any(keyword in code.lower() for keyword in ['urllib', 'requests', 'socket', 'http']):
            warnings.append("Network operations detected")
        
        # Check for system commands
        if any(keyword in code for keyword in ['os.system', 'subprocess', 'shell=True']):
            warnings.append("System command execution detected")
            is_safe = False
        
        return is_safe, warnings
    
    def show_code_preview(self, code: str, title: str = "Code to Execute"):
        """Show code preview with syntax highlighting."""
        self.console.print(Panel(
            Syntax(code, "python", theme="monokai", line_numbers=True),
            title=f"📝 {title}",
            border_style="blue"
        ))
    
    def show_package_info(self, missing_packages: Set[str], available_packages: Set[str]):
        """Show package installation information."""
        if available_packages:
            table = Table(title="✅ Available Packages", box=rich.box.ROUNDED)
            table.add_column("Package", style="green")
            table.add_column("Status", style="cyan")
            
            for pkg in sorted(available_packages):
                status = "✅ Trusted" if pkg in self.trusted_packages else "⚠️  Third-party"
                table.add_row(pkg, status)
            
            self.console.print(table)
        
        if missing_packages:
            table = Table(title="📦 Missing Packages", box=rich.box.ROUNDED)
            table.add_column("Package", style="yellow")
            table.add_column("Trust Level", style="cyan")
            table.add_column("Install Command", style="white")
            
            for pkg in sorted(missing_packages):
                trust = "✅ Trusted" if pkg in self.trusted_packages else "⚠️  Third-party"
                table.add_row(pkg, trust, f"pip install {pkg}")
            
            self.console.print(table)
    
    def install_packages(self, packages: Set[str]) -> bool:
        """Install missing packages with user confirmation."""
        if not packages:
            return True
        
        self.console.print(f"📦 Installing {len(packages)} packages...")
        
        for package in packages:
            try:
                self.console.print(f"Installing {package}...", style="yellow")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    self.console.print(f"✅ {package} installed successfully", style="green")
                else:
                    self.console.print(f"❌ Failed to install {package}: {result.stderr}", style="red")
                    return False
                    
            except subprocess.TimeoutExpired:
                self.console.print(f"❌ Installation of {package} timed out", style="red")
                return False
            except Exception as e:
                self.console.print(f"❌ Error installing {package}: {e}", style="red")
                return False
        
        return True
    
    def get_user_approval(self, code: str, auto_approve_safe: bool = False) -> Tuple[bool, str]:
        """
        Get user approval for code execution.
        
        Returns:
            Tuple of (approved, final_code)
        """
        # Show code preview
        self.show_code_preview(code)
        
        # Extract and check packages
        imports = self.extract_imports(code)
        available_pkgs, missing_pkgs = self.check_package_availability(imports)
        
        if imports:
            self.show_package_info(missing_pkgs, available_pkgs)
        
        # Analyze code safety
        is_safe, warnings = self.analyze_code_safety(code)
        
        if warnings:
            self.console.print(Panel(
                "\n".join([f"⚠️  {warning}" for warning in warnings]),
                title="🚨 Security Warnings",
                border_style="red"
            ))
        
        # Auto-approve safe code if enabled
        if auto_approve_safe and is_safe and not missing_pkgs:
            self.console.print("✅ Auto-approving safe code", style="green")
            return True, code
        
        # Get user decision
        approval_choices = [
            ("r", "🚀 Run as-is"),
            ("e", "✏️  Edit code"),
            ("i", "📦 Install packages and run"),
            ("c", "❌ Cancel"),
        ]
        
        if missing_pkgs:
            self.console.print("📦 Missing packages need to be installed before execution.", style="yellow")
        
        choice_text = " | ".join([f"{k}={v}" for k, v in approval_choices])
        choice = Prompt.ask(f"Choose action: {choice_text}", choices=["r", "e", "i", "c"], default="c")
        
        if choice == "c":
            return False, code
        
        elif choice == "e":
            # Edit code
            edited_code = self.edit_code_interactive(code)
            if edited_code != code:
                self.console.print("📝 Code edited, reviewing changes...", style="blue")
                return self.get_user_approval(edited_code, auto_approve_safe)
            else:
                return False, code
        
        elif choice == "i":
            # Install packages and run
            if missing_pkgs:
                if self.install_packages(missing_pkgs):
                    self.console.print("✅ All packages installed successfully!", style="green")
                    return True, code
                else:
                    self.console.print("❌ Package installation failed", style="red")
                    return False, code
            else:
                return True, code
        
        elif choice == "r":
            if missing_pkgs:
                self.console.print("⚠️  Running with missing packages may cause errors", style="yellow")
                if not Confirm.ask("Continue anyway?"):
                    return False, code
            return True, code
        
        return False, code
    
    def edit_code_interactive(self, code: str) -> str:
        """Interactive code editor."""
        self.console.print(Panel(
            "🖊️  **Interactive Code Editor**\n\n"
            "• Type line numbers to edit specific lines\n"
            "• Type 'add' to add new lines\n"
            "• Type 'delete X' to delete line X\n"
            "• Type 'view' to see current code\n"
            "• Type 'done' to finish editing",
            title="📝 Code Editor Help",
            border_style="blue"
        ))
        
        lines = code.split('\n')
        
        while True:
            # Show current code with line numbers
            self.show_code_with_line_numbers(lines)
            
            command = Prompt.ask("Editor command").strip().lower()
            
            if command == "done":
                break
            elif command == "view":
                continue
            elif command == "add":
                new_line = Prompt.ask("Enter new line")
                position = Prompt.ask("Insert at line number (or 'end')", default="end")
                
                if position == "end":
                    lines.append(new_line)
                else:
                    try:
                        pos = int(position) - 1
                        lines.insert(max(0, pos), new_line)
                    except ValueError:
                        self.console.print("❌ Invalid line number", style="red")
            
            elif command.startswith("delete "):
                try:
                    line_num = int(command.split()[1]) - 1
                    if 0 <= line_num < len(lines):
                        deleted = lines.pop(line_num)
                        self.console.print(f"🗑️  Deleted: {deleted}", style="yellow")
                    else:
                        self.console.print("❌ Invalid line number", style="red")
                except (ValueError, IndexError):
                    self.console.print("❌ Invalid delete command", style="red")
            
            else:
                # Try to parse as line number
                try:
                    line_num = int(command) - 1
                    if 0 <= line_num < len(lines):
                        current = lines[line_num]
                        self.console.print(f"Current line {line_num + 1}: {current}")
                        new_content = Prompt.ask("New content", default=current)
                        lines[line_num] = new_content
                    else:
                        self.console.print("❌ Invalid line number", style="red")
                except ValueError:
                    self.console.print("❌ Unknown command. Type 'done' to finish.", style="red")
        
        return '\n'.join(lines)
    
    def show_code_with_line_numbers(self, lines: List[str]):
        """Show code with line numbers."""
        code_text = Text()
        for i, line in enumerate(lines, 1):
            code_text.append(f"{i:3d} | ", style="dim cyan")
            code_text.append(f"{line}\n")
        
        self.console.print(Panel(
            code_text,
            title="📝 Current Code",
            border_style="blue"
        ))
