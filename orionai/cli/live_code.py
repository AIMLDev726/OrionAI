"""
Live Code Interface - Enhanced with AI Suggestions
=================================================

Simple, clean code editor with AI-powered tab completions and suggestions.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.text import Text

try:
    from ..cli.config import ConfigManager
    from ..core.llm_interface import LLMInterface
except ImportError:
    from cli.config import ConfigManager
    from core.llm_interface import LLMInterface

console = Console()


class SimpleCodeEditor:
    """Enhanced code editor with AI suggestions."""
    
    def __init__(self, llm_interface=None):
        self.code_lines: List[str] = []
        self.filename = "untitled.py"
        self.modified = False
        self.llm_interface: Optional[LLMInterface] = llm_interface
        
        # Only try to create new interface if none provided and config exists
        if not self.llm_interface:
            self._init_ai()
    
    def _init_ai(self):
        """Initialize AI interface for suggestions."""
        try:
            config_manager = ConfigManager()
            api_key = config_manager.get_api_key()
            
            if api_key and hasattr(config_manager.config, 'llm') and config_manager.config.llm.provider:
                # Create LLM interface with proper configuration
                from ..core.llm_interface import LLMInterface, OpenAIProvider, AnthropicProvider, GoogleProvider
                
                provider_classes = {
                    "openai": OpenAIProvider,
                    "anthropic": AnthropicProvider,
                    "google": GoogleProvider
                }
                
                provider_class = provider_classes.get(config_manager.config.llm.provider)
                if provider_class:
                    provider = provider_class(
                        api_key=api_key,
                        model=config_manager.config.llm.model if hasattr(config_manager.config.llm, 'model') else None
                    )
                    self.llm_interface = LLMInterface(provider=provider)
                    console.print("[dim green]🤖 AI suggestions enabled[/dim green]")
                else:
                    self.llm_interface = None
                    console.print("[dim yellow]⚠️  Unknown LLM provider[/dim yellow]")
            else:
                self.llm_interface = None
                if not api_key:
                    console.print("[dim yellow]⚠️  No API key found - AI suggestions disabled[/dim yellow]")
                else:
                    console.print("[dim yellow]⚠️  No LLM provider configured - AI suggestions disabled[/dim yellow]")
        except Exception as e:
            # Silently disable AI if initialization fails
            self.llm_interface = None
            console.print(f"[dim red]⚠️  AI initialization failed: {str(e)}[/dim red]")
    
    def show_editor(self):
        """Show the simple code editor interface."""
        console.clear()
        console.print(Panel.fit(
            "🔥 Live Code Editor - Simple & Clean",
            style="bold blue"
        ))
        
        while True:
            # Show current code if any
            if self.code_lines:
                code_text = "\n".join(self.code_lines)
                console.print(Panel(
                    Syntax(code_text, "python", theme="monokai", line_numbers=True),
                    title=f"📄 {self.filename}",
                    title_align="left"
                ))
            else:
                console.print(Panel(
                    "[dim]Empty file - start typing your Python code...[/dim]",
                    title=f"📄 {self.filename}",
                    title_align="left"
                ))
            
            # Show menu
            console.print("\n📝 Editor Actions:")
            console.print("1. ✏️  Add/Edit Code")
            console.print("2. ▶️  Run Code")
            console.print("3. 🤖 AI Code Suggestions")
            console.print("4. 💾 Save File")
            console.print("5. 📂 Load File")
            console.print("6. 🗑️  Clear All")
            console.print("7. 🔙 Back to Main Menu")
            
            choice = Prompt.ask("\nSelect action", choices=["1", "2", "3", "4", "5", "6", "7"], default="1")
            
            if choice == "1":
                self.edit_code()
            elif choice == "2":
                self.run_code()
            elif choice == "3":
                self.ai_suggestions()
            elif choice == "4":
                self.save_file()
            elif choice == "5":
                self.load_file()
            elif choice == "6":
                self.clear_all()
            elif choice == "7":
                break
    
    def edit_code(self):
        """Enhanced code editing with AI suggestions and ESC+Enter functionality."""
        console.print("\n✏️  Code Editor")
        console.print("[dim]Type your Python code. Type 'done' or 'exit' on a new line to finish.[/dim]")
        if self.llm_interface:
            console.print("[dim]🤖 AI suggestions enabled - end line with '?' for suggestion, or use ESC+Enter![/dim]")
        else:
            console.print("[dim yellow]⚠️  AI suggestions not available - LLM not configured[/dim yellow]")
        
        if self.code_lines:
            console.print("\nCurrent code:")
            for i, line in enumerate(self.code_lines, 1):
                console.print(f"{i:3d} | {line}")
            
            if Confirm.ask("\nKeep existing code and add more?"):
                new_lines = self.code_lines.copy()
            else:
                new_lines = []
        else:
            new_lines = []
        
        console.print("\nEnter code (type 'done' to finish):")
        
        # Interactive editing
        line_num = len(new_lines) + 1
        
        while True:
            try:
                # Get input with enhanced handling
                result = self._get_enhanced_input_with_suggestion(f"{line_num:3d} | ", new_lines)
                
                if isinstance(result, dict):
                    # Handle AI suggestion accepted case
                    if result.get('original_input'):
                        new_lines.append(result['original_input'])
                        line_num += 1
                    if result.get('suggestion'):
                        new_lines.append(result['suggestion'])
                        line_num += 1
                    continue
                
                user_input = result
                
                # Handle exit commands
                if user_input.strip().lower() in ['done', 'exit', 'quit']:
                    break
                    
                # Handle empty lines
                if user_input.strip() == '':
                    new_lines.append("")
                    line_num += 1
                    continue
                
                # Add the line
                new_lines.append(user_input)
                line_num += 1
                
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️  Line cancelled. Type 'done' to finish editing[/yellow]")
                continue
            except EOFError:
                break
        
        self.code_lines = new_lines
        self.modified = True
        console.print("✅ Code updated!")
    
    def _get_enhanced_input_with_suggestion(self, prompt: str, current_lines: List[str]):
        """Enhanced input handling that preserves original input when AI suggestion is accepted."""
        user_input = input(prompt)
        
        # Check for AI suggestion trigger (end with ?)
        if user_input.endswith('?') and self.llm_interface:
            base_input = user_input[:-1].strip()
            if base_input:  # Only suggest if there's actual content
                suggestion = self._get_ai_suggestion(current_lines + [base_input])
                if suggestion:
                    console.print(f"[dim cyan]💡 AI suggestion: {suggestion}[/dim cyan]")
                    choice = Confirm.ask("Use AI suggestion as additional line?", default=False)
                    if choice:
                        return {
                            'original_input': base_input,
                            'suggestion': suggestion
                        }
                    else:
                        return base_input
                return base_input
            else:
                return ""
        
        # Check for immediate AI suggestion for longer lines
        if self.llm_interface and len(user_input.strip()) > 5:
            suggestion = self._get_ai_suggestion(current_lines + [user_input])
            if suggestion and suggestion != user_input:
                console.print(f"[dim cyan]💡 AI suggestion: {suggestion}[/dim cyan]")
                choice = Confirm.ask("Use AI suggestion as additional line?", default=False)
                if choice:
                    return {
                        'original_input': user_input,
                        'suggestion': suggestion
                    }
        
        return user_input
    
    def _get_enhanced_input(self, prompt: str, current_lines: List[str]) -> str:
        """Enhanced input handling with AI suggestion support."""
        # Simple implementation for Windows compatibility
        user_input = input(prompt)
        
        # Check for AI suggestion trigger (end with ?)
        if user_input.endswith('?') and self.llm_interface:
            base_input = user_input[:-1].strip()
            if base_input:  # Only suggest if there's actual content
                suggestion = self._get_ai_suggestion(current_lines + [base_input])
                if suggestion:
                    console.print(f"[dim cyan]💡 AI suggestion: {suggestion}[/dim cyan]")
                    if Confirm.ask("Use AI suggestion?", default=False):
                        return suggestion
                return base_input
            else:
                return ""
        
        # Check for immediate AI suggestion for longer lines
        if self.llm_interface and len(user_input.strip()) > 5:
            suggestion = self._get_ai_suggestion(current_lines + [user_input])
            if suggestion and suggestion != user_input:
                console.print(f"[dim cyan]💡 AI suggestion: {suggestion}[/dim cyan]")
                if Confirm.ask("Use AI suggestion instead?", default=False):
                    return suggestion
        
        return user_input
    
    def _get_inline_suggestion(self, current_code: List[str]) -> str:
        """Get inline AI suggestion for current typing context."""
        if not self.llm_interface:
            return ""
        
        try:
            # Get context of current code
            code_context = "\n".join(current_code[:-1]) if len(current_code) > 1 else ""
            current_line = current_code[-1] if current_code else ""
            
            # Create a focused prompt for completion
            prompt = f"""Complete this Python code line. Provide only the completion part (what comes after the current text), no explanations:

Previous code:
```python
{code_context}
```

Current line to complete: `{current_line}`

Completion (only the missing part):"""
            
            response = self.llm_interface.generate_chat_response(
                prompt,
                temperature=0.2,
                max_tokens=30
            )
            
            # Clean and extract the suggestion
            suggestion = response.strip()
            
            # Remove any markdown or extra formatting
            if "```" in suggestion:
                lines = suggestion.split('\n')
                for line in lines:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith('```'):
                        suggestion = clean_line
                        break
            
            # Remove quotes if present
            suggestion = suggestion.strip('"\'`')
            
            # Make sure suggestion doesn't repeat the current line
            if suggestion.startswith(current_line):
                suggestion = suggestion[len(current_line):]
            
            return suggestion.strip()[:50]  # Limit suggestion length
            
        except Exception:
            return ""
    
    def _get_ai_suggestion(self, current_code: List[str]) -> Optional[str]:
        """Get AI suggestion for next line of code."""
        if not self.llm_interface:
            return None
        
        try:
            code_context = "\n".join(current_code) if current_code else "# Starting Python code"
            
            prompt = f"""Given this Python code context, suggest the next logical line of code. 
Provide only ONE line of code, no explanations:

Current code:
```python
{code_context}
```

Next line suggestion:"""
            
            response = self.llm_interface.generate_chat_response(
                prompt, 
                temperature=0.3,
                max_tokens=50
            )
            
            # Extract just the code line
            suggestion = response.strip()
            if "```" in suggestion:
                # Extract from code block
                lines = suggestion.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('```'):
                        suggestion = line.strip()
                        break
            
            # Clean up the suggestion
            suggestion = suggestion.replace('```python', '').replace('```', '').strip()
            
            return suggestion if suggestion else None
            
        except Exception as e:
            console.print(f"⚠️  AI suggestion failed: {e}", style="yellow")
            return None
    
    def ai_suggestions(self):
        """Show AI code suggestions and improvements."""
        if not self.llm_interface:
            console.print("❌ AI suggestions not available - Please configure LLM provider in Settings", style="red")
            console.print("💡 Go to Main Menu → Configure LLM Provider to set up AI", style="blue")
            input("Press Enter to continue...")
            return
        
        if not self.code_lines:
            console.print("❌ No code to analyze", style="red")
            input("Press Enter to continue...")
            return
        
        console.print("\n🤖 AI Code Analysis...", style="blue")
        
        try:
            current_code = "\n".join(self.code_lines)
            
            # Get AI analysis
            prompt = f"""Analyze this Python code and provide suggestions for improvement:

```python
{current_code}
```

Please provide:
1. Code quality improvements
2. Performance optimizations  
3. Bug fixes or potential issues
4. Additional functionality suggestions

Format your response clearly with specific suggestions."""
            
            response = self.llm_interface.generate_chat_response(
                prompt,
                temperature=0.2,
                max_tokens=500
            )
            
            console.print(Panel(
                response,
                title="🤖 AI Code Analysis & Suggestions",
                title_align="left",
                style="cyan"
            ))
            
            if Confirm.ask("\nWould you like AI to rewrite/improve your code?"):
                self._ai_improve_code(current_code)
                
        except Exception as e:
            console.print(f"❌ AI analysis failed: {e}", style="red")
        
        input("\nPress Enter to continue...")
    
    def _ai_improve_code(self, current_code: str):
        """Let AI improve the current code."""
        try:
            prompt = f"""Improve this Python code by fixing issues, optimizing performance, and adding useful features.
Provide ONLY the improved Python code, no explanations:

```python
{current_code}
```

Improved code:"""
            
            response = self.llm_interface.generate_chat_response(
                prompt,
                temperature=0.1,
                max_tokens=800
            )
            
            # Extract code from response
            improved_code = response.strip()
            if "```python" in improved_code:
                # Extract from code block
                start = improved_code.find("```python") + 9
                end = improved_code.find("```", start)
                improved_code = improved_code[start:end].strip()
            elif "```" in improved_code:
                # Handle generic code blocks
                start = improved_code.find("```") + 3
                end = improved_code.find("```", start)
                improved_code = improved_code[start:end].strip()
            
            if improved_code:
                console.print("\n🤖 AI Improved Code:")
                console.print(Panel(
                    Syntax(improved_code, "python", theme="monokai", line_numbers=True),
                    title="✨ Improved Code",
                    title_align="left"
                ))
                
                if Confirm.ask("Replace your code with this improved version?"):
                    self.code_lines = improved_code.splitlines()
                    self.modified = True
                    console.print("✅ Code replaced with AI improvements!", style="green")
            else:
                console.print("❌ Could not generate improved code", style="red")
                
        except Exception as e:
            console.print(f"❌ Code improvement failed: {e}", style="red")
    
    def run_code(self):
        """Run the current code."""
        if not self.code_lines:
            console.print("❌ No code to run!", style="red")
            return
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('\n'.join(self.code_lines))
            temp_file = f.name
        
        try:
            console.print("▶️  Running code...\n", style="blue")
            
            # Run the code
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Show output
            if result.stdout:
                console.print(Panel(
                    result.stdout,
                    title="📤 Output",
                    title_align="left",
                    style="green"
                ))
            
            if result.stderr:
                console.print(Panel(
                    result.stderr,
                    title="❌ Error",
                    title_align="left",
                    style="red"
                ))
            
            if result.returncode == 0:
                console.print("✅ Code executed successfully!", style="green")
            else:
                console.print(f"❌ Code failed with exit code {result.returncode}", style="red")
                
        except subprocess.TimeoutExpired:
            console.print("⏱️  Code execution timed out (30s limit)", style="yellow")
        except Exception as e:
            console.print(f"❌ Execution error: {e}", style="red")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
        
        input("\nPress Enter to continue...")
    
    def save_file(self):
        """Save code to file."""
        if not self.code_lines:
            console.print("❌ No code to save!", style="red")
            return
        
        filename = Prompt.ask("💾 Save as", default=self.filename)
        
        try:
            with open(filename, 'w') as f:
                f.write('\n'.join(self.code_lines))
            
            self.filename = filename
            self.modified = False
            console.print(f"✅ Saved to {filename}", style="green")
        except Exception as e:
            console.print(f"❌ Save failed: {e}", style="red")
    
    def load_file(self):
        """Load code from file."""
        filename = Prompt.ask("📂 Load file")
        
        try:
            with open(filename, 'r') as f:
                self.code_lines = f.read().splitlines()
            
            self.filename = filename
            self.modified = False
            console.print(f"✅ Loaded {filename}", style="green")
        except FileNotFoundError:
            console.print(f"❌ File not found: {filename}", style="red")
        except Exception as e:
            console.print(f"❌ Load failed: {e}", style="red")
    
    def clear_all(self):
        """Clear all code."""
        if self.code_lines and Confirm.ask("🗑️  Clear all code? This cannot be undone!"):
            self.code_lines = []
            self.filename = "untitled.py"
            self.modified = False
            console.print("✅ Code cleared!", style="green")


def show_live_code_menu(llm_interface=None):
    """Show the live code editor."""
    editor = SimpleCodeEditor(llm_interface)
    editor.show_editor()


if __name__ == "__main__":
    show_live_code_menu()
