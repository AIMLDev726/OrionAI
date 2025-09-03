"""
Interactive Chat Session with Code Execution
===========================================

Rich CLI interface for interactive LLM chat with real-time code execution.
"""

import sys
import io
import contextlib
import logging
import traceback
import subprocess
import re
from pathlib import Path
from typing import  Optional, Tuple, List
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.llm_interface import LLMInterface, OpenAIProvider, AnthropicProvider, GoogleProvider
from .session import SessionManager, CodeExecution
from .config import ConfigManager
from .code_approval import CodeApprovalManager
from ..mcp.manager import MCPManager

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Handles safe code execution with output capture."""
    
    def __init__(self, session_manager: SessionManager, config_manager: ConfigManager):
        self.session_manager = session_manager
        self.config_manager = config_manager
        self.code_approval = CodeApprovalManager()
        self.globals_dict = {
            '__builtins__': __builtins__,
        }
        # Don't setup heavy imports in constructor - do it lazily when needed
        self._environment_setup = False
    
    def setup_environment(self):
        """Setup the execution environment with common imports using lazy loading."""
        if self._environment_setup:
            return
            
        try:
            # Add basic modules first
            import json
            import os
            import sys
            from pathlib import Path
            from datetime import datetime
            
            self.globals_dict.update({
                'json': json,
                'os': os,
                'sys': sys,
                'Path': Path,
                'datetime': datetime,
            })
            
            # Try to add matplotlib with fallback
            try:
                import matplotlib
                matplotlib.use('Agg')  # Set backend for non-interactive use
                import matplotlib.pyplot as plt
                self.globals_dict['plt'] = plt
            except ImportError:
                pass  # Matplotlib will be added on demand
            
            # Mark as setup
            self._environment_setup = True
            
        except Exception as e:
            print(f"Warning: Could not setup basic environment: {e}")
    
    def _add_module_on_demand(self, module_name: str):
        """Add a module to globals on demand."""
        if module_name in self.globals_dict:
            return
            
        try:
            if module_name == 'np':
                from ..python.lazy_imports import get_numpy
                self.globals_dict['np'] = get_numpy()
            elif module_name == 'pd':
                from ..python.lazy_imports import get_pandas
                self.globals_dict['pd'] = get_pandas()
            elif module_name == 'plt':
                from ..python.lazy_imports import get_matplotlib
                plt = get_matplotlib()
                plt.switch_backend('Agg')
                self.globals_dict['plt'] = plt
            elif module_name == 'sns':
                from ..python.lazy_imports import get_seaborn
                self.globals_dict['sns'] = get_seaborn()
        except Exception as e:
            print(f"Warning: Could not import {module_name}: {e}")
    
    def execute_code(self, code: str) -> CodeExecution:
        """Execute Python code safely and capture output."""
        # First, get approval from user before executing code
        approved, final_code = self.code_approval.get_user_approval(code)
        
        if not approved:
            return CodeExecution(
                code=code,
                output="",
                error="Code execution was not approved by user",
                execution_time=0.0
            )
        
        # Use the potentially modified code from approval process
        # final_code is already set from the approval process above
        
        # Setup basic environment first
        self.setup_environment()
        
        # Check for common imports and add them on demand
        if 'np.' in final_code or 'numpy' in final_code:
            self._add_module_on_demand('np')
        if 'pd.' in final_code or 'pandas' in final_code:
            self._add_module_on_demand('pd')
        if 'plt.' in final_code or 'matplotlib' in final_code:
            self._add_module_on_demand('plt')
        if 'sns.' in final_code or 'seaborn' in final_code:
            self._add_module_on_demand('sns')
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        start_time = datetime.now()
        execution_error = None
        files_created = []
        
        try:
            # Get current working directory files before execution
            session_dir = self.config_manager.get_session_dir(
                self.session_manager.current_session.session_id
            )
            image_dir = self.config_manager.get_image_dir(
                self.session_manager.current_session.session_id
            )
            
            # Set up paths in global environment
            self.globals_dict['session_dir'] = str(session_dir)
            self.globals_dict['image_dir'] = str(image_dir)
            
            # Clear any existing figures before execution
            plt_module = self.globals_dict.get('plt')
            if plt_module:
                plt_module.close('all')
            
            before_files = set(image_dir.glob("*")) if image_dir.exists() else set()
            
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                
                # Clean and prepare code for execution
                modified_code = final_code.strip()
                
                # Replace plt.show() with plt.savefig() and save path info
                if 'plt.show()' in modified_code:
                    # Remove plt.show() calls as we'll handle saving automatically
                    modified_code = re.sub(r'plt\.show\(\)', '', modified_code)
                
                # Fix the __main__ issue - LLM often generates code with if __name__ == "__main__": 
                # which doesn't work with exec(). Replace it to ensure the code runs.
                if 'if __name__ == "__main__":' in modified_code:
                    modified_code = modified_code.replace('if __name__ == "__main__":', 'if True:')
                
                # Fix common indentation issues
                lines = modified_code.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Skip empty lines that might cause issues
                    if line.strip():
                        cleaned_lines.append(line)
                    elif cleaned_lines:  # Only add empty lines if not at start
                        cleaned_lines.append('')
                
                modified_code = '\n'.join(cleaned_lines)
                
                # Execute the code
                exec(modified_code, self.globals_dict)
                
                # Check if any figures were created
                plt_module = self.globals_dict.get('plt')
                if plt_module and plt_module.get_fignums():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Save all open figures
                    for i, fig_num in enumerate(plt_module.get_fignums()):
                        fig = plt_module.figure(fig_num)
                        if len(fig.get_axes()) > 0:  # Only save if figure has content
                            filename = f"plot_{timestamp}_{i+1}.png"
                            filepath = image_dir / filename
                            
                            # Ensure directory exists
                            filepath.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Save the figure
                            fig.savefig(filepath, dpi=150, bbox_inches='tight', 
                                      facecolor='white', edgecolor='none')
                            files_created.append(str(filepath))
                            
                    # Close all figures after saving
                    plt_module.close('all')
            
            # Check for any other new files created
            after_files = set(image_dir.glob("*")) if image_dir.exists() else set()
            new_files = after_files - before_files
            for new_file in new_files:
                if str(new_file) not in files_created:
                    files_created.append(str(new_file))
            
        except Exception as e:
            execution_error = traceback.format_exc()
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        output = stdout_capture.getvalue()
        error_output = stderr_capture.getvalue()
        
        if error_output and not execution_error:
            execution_error = error_output
        
        return CodeExecution(
            code=final_code,  # Use the final approved/modified code
            output=output,
            error=execution_error,
            execution_time=execution_time,
            files_created=files_created
        )
    
    def install_package(self, package: str) -> bool:
        """Install a Python package."""
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            return True
        except subprocess.CalledProcessError:
            return False


class InteractiveChatSession:
    """Interactive chat session with LLM and code execution."""
    
    def __init__(self, config_manager: ConfigManager, session_manager: SessionManager):
        self.config_manager = config_manager
        self.session_manager = session_manager
        self.console = Console()
        self.llm_interface = None
        self.code_executor = None
        self.mcp_manager = None
        self._llm_setup_attempted = False
        
        # Initialize MCP if enabled
        if config_manager.config.session.enable_mcp and config_manager.config.mcp.enabled:
            try:
                self.mcp_manager = MCPManager(config_manager.config_dir)
                if config_manager.config.mcp.auto_connect:
                    self.mcp_manager.connect_all_servers()
            except Exception as e:
                self.console.print(f"⚠️  MCP initialization warning: {e}", style="yellow")
    
    def setup_llm(self):
        """Setup LLM provider based on configuration (lazy initialization)."""
        if self._llm_setup_attempted:
            return self.llm_interface is not None
            
        self._llm_setup_attempted = True
        config = self.config_manager.config.llm
        api_key = self.config_manager.get_api_key()

        if not api_key:
            self.console.print("❌ No API key found. Please run setup first.", style="red")
            return False

        try:
            if config.provider == "openai":
                provider = OpenAIProvider(api_key=api_key, model=config.model)
            elif config.provider == "anthropic":
                provider = AnthropicProvider(api_key=api_key, model=config.model)
            elif config.provider == "google":
                provider = GoogleProvider(api_key=api_key, model=config.model)
            else:
                self.console.print(f"❌ Unknown provider: {config.provider}", style="red")
                return False
            
            self.llm_interface = LLMInterface(provider, self.mcp_manager)
            self.code_executor = CodeExecutor(self.session_manager, self.config_manager)
            return True
        except Exception as e:
            self.console.print(f"❌ Error setting up LLM: {e}", style="red")
            return False
    
    def extract_code_blocks(self, text: str) -> List[str]:
        """Extract Python code blocks from text."""
        # More robust pattern to match various code block formats
        patterns = [
            r'```python\s*\n(.*?)\n```',  # ```python
            r'```\s*\n(.*?)\n```',       # ``` (generic)
        ]
        
        code_blocks = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            code_blocks.extend(matches)
        
        # Remove duplicates and clean up the code blocks
        seen = set()
        cleaned_blocks = []
        for code in code_blocks:
            # Clean and normalize the code
            cleaned_code = self._clean_code_block(code)
            
            if cleaned_code and len(cleaned_code) > 10:  # Ignore tiny fragments
                # Basic syntax validation - check for balanced quotes and brackets
                try:
                    # Try to compile the code to check for basic syntax errors
                    compile(cleaned_code, '<string>', 'exec')
                    
                    # Use a hash to avoid duplicates
                    code_hash = hash(cleaned_code)
                    if code_hash not in seen:
                        seen.add(code_hash)
                        cleaned_blocks.append(cleaned_code)
                except SyntaxError as e:
                    # Try to fix common issues and retry
                    fixed_code = self._try_fix_syntax_errors(cleaned_code)
                    if fixed_code:
                        try:
                            compile(fixed_code, '<string>', 'exec')
                            code_hash = hash(fixed_code)
                            if code_hash not in seen:
                                seen.add(code_hash)
                                cleaned_blocks.append(fixed_code)
                                self.console.print(f"⚠️  Fixed syntax error in code block", style="yellow")
                        except SyntaxError:
                            self.console.print(f"⚠️  Skipping malformed code block: {e}", style="yellow")
                            continue
                    else:
                        self.console.print(f"⚠️  Skipping malformed code block: {e}", style="yellow")
                        continue
        
        return cleaned_blocks
    
    def _clean_code_block(self, code: str) -> str:
        """Clean and normalize a code block."""
        # Remove leading/trailing whitespace
        code = code.strip()
        
        # Split into lines for processing
        lines = code.split('\n')
        cleaned_lines = []
        
        # Remove empty lines at start and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        # Process each line
        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _try_fix_syntax_errors(self, code: str) -> Optional[str]:
        """Try to fix common syntax errors in code."""
        try:
            lines = code.split('\n')
            fixed_lines = []
            
            for i, line in enumerate(lines):
                # Skip empty lines
                if not line.strip():
                    if fixed_lines:  # Only add empty lines if not at start
                        fixed_lines.append('')
                    continue
                
                # Fix common indentation issues
                if line.strip().endswith(':'):
                    # This is a statement that requires indentation
                    fixed_lines.append(line)
                    # Check if next line is properly indented
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if next_line.strip() and not next_line.startswith('    '):
                            # Next line should be indented but isn't
                            continue  # Skip this problematic structure
                else:
                    fixed_lines.append(line)
            
            if fixed_lines:
                return '\n'.join(fixed_lines)
        except Exception:
            pass
        
        return None
    
    def _enhance_prompt_for_code(self, user_input: str, search_context: str = "") -> str:
        """Enhance user prompt with specific instructions for code generation."""
        # Keywords that suggest code is needed
        code_keywords = [
            'plot', 'graph', 'chart', 'visualize', 'generate', 'create', 'code', 'python',
            'script', 'function', 'calculate', 'compute', 'data', 'analysis', 'model'
        ]
        
        needs_code = any(keyword in user_input.lower() for keyword in code_keywords)
        
        if needs_code:
            enhanced_prompt = f"""{user_input}

{search_context}

IMPORTANT INSTRUCTIONS FOR CODE GENERATION:
- When providing Python code, ensure it is properly formatted and syntactically correct
- Use proper indentation (4 spaces for each level)
- Place code in ```python code blocks
- Ensure all if/else/for/while statements have proper indentation after the colon
- Test that the code is complete and executable
- Include necessary imports at the top
- Use meaningful variable names
- Add brief comments to explain key steps
- If web search results are provided above, incorporate that current information

Please provide working Python code that can be executed directly."""
            return enhanced_prompt
        
        # For non-code queries, still include search context if available
        if search_context:
            enhanced_prompt = f"""{user_input}

{search_context}

IMPORTANT: Based on the web search results above, provide a comprehensive and helpful response. 
Summarize the key information from the search results and answer the user's question directly. 
Do not just repeat the search results - synthesize them into a useful answer."""
            return enhanced_prompt
        
        return user_input
        
        return user_input
    
    def _needs_web_search(self, query: str) -> bool:
        """Dynamically determine if query needs web search using LLM decision."""
        
        # Quick hardcoded check for explicit search requests
        explicit_search = ['search for', 'google', 'web search', 'search the web', 'find online']
        if any(term in query.lower() for term in explicit_search):
            return True
        
        # Quick hardcoded check for obvious calculations (priority)
        calc_patterns = ['2+2', '3+5', '10*5', 'calculate', 'what is', 'solve']
        if any(pattern in query.lower() for pattern in calc_patterns):
            # Check if it's a simple math problem
            import re
            math_pattern = r'\b\d+\s*[\+\-\*\/]\s*\d+'
            if re.search(math_pattern, query):
                return False  # Use MCP tools for calculations
        
        # Use LLM to dynamically decide
        return self._llm_decide_web_search(query)
    
    def _llm_decide_web_search(self, query: str) -> bool:
        """Use LLM to dynamically decide if web search is needed."""
        try:
            decision_prompt = f"""
Analyze this user query and determine if it requires web search or can be handled with internal tools.

User Query: "{query}"

Consider these factors:
- Does it need current/real-time information (news, weather, stock prices, sports scores)?
- Does it ask about recent events or current status of something?
- Does it ask about specific people, places, or organizations that might have current info?
- Is it asking for factual information that changes over time?
- Does it explicitly request web search?

DO NOT use web search for:
- Simple calculations (2+2, math problems)
- General programming questions
- Code generation requests
- Basic definitions that don't change
- Personal requests or conversations

Respond with only "YES" if web search is needed, or "NO" if internal tools can handle it.

Decision:"""

            # Use a simple LLM call for decision
            if self.llm_interface:
                try:
                    response = self.llm_interface.generate_chat_response(
                        decision_prompt,
                        conversation_history=[],
                        temperature=0.1,  # Low temperature for consistent decisions
                        max_tokens=10
                    )
                    
                    decision = response.strip().upper()
                    if "YES" in decision:
                        return True
                    elif "NO" in decision:
                        return False
                        
                except Exception as e:
                    logger.error(f"LLM decision error: {e}")
            
            # Fallback to basic heuristics if LLM fails
            return self._fallback_search_decision(query)
            
        except Exception as e:
            logger.error(f"Error in LLM web search decision: {e}")
            return self._fallback_search_decision(query)
    
    def _fallback_search_decision(self, query: str) -> bool:
        """Fallback decision logic if LLM is unavailable."""
        query_lower = query.lower()
        
        # Current info indicators
        current_indicators = [
            'latest', 'recent', 'current', 'today', 'news', 'now',
            'weather', 'temperature', 'stock', 'price', 'score'
        ]
        
        # Location-based
        location_indicators = ['in ', 'at ', 'weather in', 'time in']
        
        # Check for current info needs
        if any(indicator in query_lower for indicator in current_indicators):
            return True
            
        # Check for location-based queries
        if any(indicator in query_lower for indicator in location_indicators):
            return True
        
        # Default: no web search needed - use MCP servers instead
        return False
    
    def _perform_web_search(self, query: str) -> str:
        """Web search now handled by MCP servers."""
        self.console.print("ℹ️  Web search is now available through MCP servers.", style="blue")
        self.console.print("💡 Install web search MCP servers using CLI menu option 5.", style="dim")
        return ""
    
    def process_llm_response(self, response: str) -> Tuple[str, List[str]]:
        """Process LLM response and extract code blocks or handle tool calls."""
        
        # First check if this is a tool call (JSON response)
        if self._is_tool_call(response):
            tool_result = self._handle_tool_call(response)
            if tool_result:
                # Return the tool result as the response
                return tool_result, []
        
        # If not a tool call, process normally for code blocks
        code_blocks = self.extract_code_blocks(response)
        
        # Remove code blocks from response for display - use better approach
        text_without_code = response
        
        # Remove all code block patterns
        patterns_to_remove = [
            r'```python\s*\n.*?\n```',
            r'```\s*\n.*?\n```'
        ]
        
        for pattern in patterns_to_remove:
            text_without_code = re.sub(pattern, '', text_without_code, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up extra whitespace
        text_without_code = re.sub(r'\n\s*\n\s*\n', '\n\n', text_without_code)
        
        return text_without_code.strip(), code_blocks
    
    def _is_tool_call(self, response: str) -> bool:
        """Check if response contains a tool call (JSON with action: use_tool)."""
        try:
            # Look for JSON patterns in the response
            import json
            
            # Try to find JSON in the response using brace counting
            json_found = False
            
            # Quick check for JSON patterns
            if '"action"' in response and '"use_tool"' in response:
                # Look for opening brace
                for i, char in enumerate(response):
                    if char == '{':
                        # Check if this contains our action
                        remaining = response[i:]
                        if '"action"' in remaining and '"use_tool"' in remaining:
                            json_found = True
                            break
            
            if json_found:
                return True
            
            # Also try to parse the entire response as JSON
            response_clean = response.strip()
            if response_clean.startswith('{') and response_clean.endswith('}'):
                try:
                    parsed = json.loads(response_clean)
                    if isinstance(parsed, dict) and parsed.get('action') == 'use_tool':
                        return True
                except:
                    pass
            
            # Check for incomplete JSON (missing opening brace)
            if '"action"' in response and '"use_tool"' in response:
                return True
                    
            return False
            
        except Exception:
            return False
    
    def _handle_tool_call(self, response: str) -> Optional[str]:
        """Handle tool call from LLM response."""
        try:
            import json
            
            # Extract JSON from response
            json_match = None
            
            # First try parsing entire response as JSON
            response_clean = response.strip()
            if response_clean.startswith('{') and response_clean.endswith('}'):
                try:
                    json.loads(response_clean)  # Test if valid
                    json_match = response_clean
                except:
                    pass
            
            # If not found, look for JSON pattern using brace counting
            if not json_match:
                # Find JSON start
                json_start = -1
                for i, char in enumerate(response):
                    if char == '{':
                        # Check if this looks like our JSON
                        remaining = response[i:]
                        if '"action"' in remaining and '"use_tool"' in remaining:
                            json_start = i
                            break
                
                if json_start >= 0:
                    # Count braces to find the end
                    brace_count = 0
                    json_end = -1
                    
                    for i in range(json_start, len(response)):
                        if response[i] == '{':
                            brace_count += 1
                        elif response[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > json_start:
                        json_match = response[json_start:json_end]
            
            # Handle case where JSON is missing opening brace or closing braces
            if not json_match and '"action"' in response and '"use_tool"' in response:
                # Try to reconstruct the JSON
                response_lines = response.strip().split('\n')
                json_lines = []
                in_json = False
                
                for line in response_lines:
                    if '"action"' in line or in_json:
                        in_json = True
                        json_lines.append(line.strip())
                        if line.strip().endswith('}'):
                            break
                
                if json_lines:
                    json_text = '\n'.join(json_lines)
                    
                    # Add opening brace if missing
                    if not json_text.startswith('{'):
                        json_text = '{' + json_text
                    
                    # Count and balance braces
                    open_braces = json_text.count('{')
                    close_braces = json_text.count('}')
                    
                    # Add missing closing braces
                    while close_braces < open_braces:
                        json_text += '}'
                        close_braces += 1
                    
                    json_match = json_text
            
            if not json_match:
                return None
            
            # Parse the JSON
            try:
                tool_call = json.loads(json_match)
            except json.JSONDecodeError as e:
                self.console.print(f"❌ Invalid JSON in tool call: {e}", style="red")
                self.console.print(f"JSON attempted: {json_match}", style="yellow")
                return None
            
            # Validate tool call structure
            if not isinstance(tool_call, dict) or tool_call.get('action') != 'use_tool':
                return None
            
            # Check if MCP is available
            if not self.mcp_manager:
                return "❌ MCP tools are not enabled. Please enable MCP in settings."
            
            # Extract tool information
            tool_name = tool_call.get('tool_name') or tool_call.get('arguments', {}).get('tool_name')
            arguments = tool_call.get('arguments', {})
            
            # Handle different argument structures
            if 'expression' in arguments:
                # Calculator tool
                tool_name = 'calculate'
                calc_args = {'expression': arguments['expression']}
            elif 'query' in arguments:
                # Search tool  
                tool_name = 'web_search'
                calc_args = {'query': arguments['query']}
            else:
                calc_args = arguments
            
            if not tool_name:
                return "❌ No tool name specified in tool call."
            
            self.console.print(f"🔧 Using MCP tool: {tool_name}", style="cyan")
            
            # Call the MCP tool
            try:
                result = self.mcp_manager.call_tool(tool_name, calc_args)
                
                # Format the result nicely
                if isinstance(result, dict):
                    if 'result' in result:
                        formatted_result = f"✅ Tool result: {result['result']}"
                    else:
                        formatted_result = f"✅ Tool result: {json.dumps(result, indent=2)}"
                else:
                    formatted_result = f"✅ Tool result: {result}"
                
                return formatted_result
                
            except Exception as e:
                error_msg = f"❌ Tool execution failed: {str(e)}"
                self.console.print(error_msg, style="red")
                return error_msg
            
        except Exception as e:
            self.console.print(f"❌ Error handling tool call: {e}", style="red")
            return f"❌ Error processing tool call: {str(e)}"
    
    def display_message(self, content: str, role: str = "assistant", message_type: str = "text"):
        """Display a message with proper formatting."""
        if role == "user":
            style = "blue"
            prefix = "🙋 You"
        elif role == "assistant":
            style = "green"
            prefix = "🤖 OrionAI"
        else:
            style = "yellow"
            prefix = "ℹ️  System"
        
        if message_type == "markdown":
            self.console.print(Panel(Markdown(content), title=prefix, title_align="left"))
        elif message_type == "code":
            self.console.print(Panel(
                Syntax(content, "python", theme="monokai"), 
                title=f"{prefix} (Code)", 
                title_align="left"
            ))
        else:
            self.console.print(Panel(content, title=prefix, title_align="left", style=style))
    
    def display_code_execution(self, execution: CodeExecution):
        """Display code execution results."""
        # Show the code
        self.console.print(Panel(
            Syntax(execution.code, "python", theme="monokai"), 
            title="🔧 Executing Code", 
            title_align="left"
        ))
        
        # Show output
        if execution.output:
            self.console.print(Panel(
                execution.output, 
                title="📤 Output", 
                title_align="left", 
                style="green"
            ))
        
        # Show error if any
        if execution.error:
            self.console.print(Panel(
                execution.error, 
                title="❌ Error", 
                title_align="left", 
                style="red"
            ))
        
        # Show files created
        if execution.files_created:
            files_text = "\n".join(execution.files_created)
            self.console.print(Panel(
                files_text, 
                title="📁 Files Created", 
                title_align="left", 
                style="cyan"
            ))
            
            # For image files, offer to open them
            image_files = [f for f in execution.files_created if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
            if image_files:
                self.console.print("🖼️  Image files created! Opening the first one...", style="blue")
                try:
                    import os
                    import sys
                    first_image = image_files[0]
                    
                    # Try to open the image file
                    if sys.platform.startswith('win'):
                        os.startfile(first_image)
                    elif sys.platform.startswith('darwin'):  # macOS
                        import subprocess
                        subprocess.run(['open', first_image])
                    else:  # Linux
                        import subprocess
                        subprocess.run(['xdg-open', first_image])
                    
                    self.console.print(f"📂 Opened: {Path(first_image).name}", style="green")
                except Exception as e:
                    self.console.print(f"⚠️  Could not open image: {e}", style="yellow")
                    self.console.print(f"💡 Please manually open: {first_image}", style="blue")
        
        # Show execution time
        self.console.print(f"⏱️  Execution time: {execution.execution_time:.2f}s")
    
    def handle_code_execution_error(self, execution: CodeExecution, original_query: str) -> bool:
        """Handle code execution error by asking LLM to fix it."""
        if not execution.error:
            return True
        
        self.console.print("\n🔄 Code execution failed. Asking LLM to fix it...")
        
        # Create fix prompt
        fix_prompt = f"""
The following Python code failed with a syntax or execution error. Please analyze the error and provide ONLY the corrected Python code.

Original User Request: {original_query}

Failed Code:
```python
{execution.code}
```

Error Details:
{execution.error}

INSTRUCTIONS FOR THE FIX:
1. Analyze the specific error and identify the root cause
2. Provide ONLY valid, executable Python code in a ```python code block
3. Ensure proper indentation (4 spaces per level)
4. Make sure all control structures (if/else/for/while) are properly formatted
5. Include all necessary imports
6. Test that the code logic is complete and correct
7. Do not include explanations outside the code block

Please provide the corrected code:
"""
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Fixing code...", total=None)
                response = self.llm_interface.generate_chat_response(fix_prompt)
            
            # Extract and execute fixed code
            text_response, code_blocks = self.process_llm_response(response)
            
            if code_blocks:
                self.console.print("\n🛠️  LLM provided a fix:")
                self.display_message(text_response, "assistant", "markdown")
                
                # Execute the fixed code
                for code in code_blocks:
                    execution = self.code_executor.execute_code(code)
                    self.display_code_execution(execution)
                    
                    # Add to session
                    self.session_manager.add_code_execution(execution)
                    
                    if not execution.error:
                        self.console.print("✅ Code fixed and executed successfully!")
                        return True
                
                # If still failing, ask user what to do
                retry = Confirm.ask("Code still failing. Try another fix?")
                if retry:
                    return self.handle_code_execution_error(execution, original_query)
            
        except Exception as e:
            self.console.print(f"❌ Error getting fix from LLM: {e}", style="red")
        
        return False
    
    def process_user_input(self, user_input: str):
        """Process user input and generate LLM response."""
        # Add user message to session
        self.session_manager.add_message("user", user_input)
        
        # Display user message
        self.display_message(user_input, "user")
        
        # Prepare conversation history for LLM
        conversation_history = []
        history = self.session_manager.get_conversation_history(limit=10)
        
        for msg in history[:-1]:  # Exclude the current message
            if msg.role in ["user", "assistant"]:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        try:
            # Check if web search is needed
            search_context = ""
            if self._needs_web_search(user_input):
                search_context = self._perform_web_search(user_input)
            
            # Enhance the prompt for better code generation
            enhanced_prompt = self._enhance_prompt_for_code(user_input, search_context)
            
            # Get LLM response using flexible chat method
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Thinking...", total=None)
                response = self.llm_interface.generate_chat_response(
                    enhanced_prompt, 
                    conversation_history=conversation_history
                )
            
            # Process response
            text_response, code_blocks = self.process_llm_response(response)
            
            # Display text response
            if text_response:
                self.display_message(text_response, "assistant", "markdown")
                self.session_manager.add_message("assistant", text_response, "markdown")
            
            # Execute code blocks
            for code in code_blocks:
                if self.config_manager.config.session.enable_code_execution:
                    execution = self.code_executor.execute_code(code)
                    self.display_code_execution(execution)
                    
                    # Add to session
                    self.session_manager.add_code_execution(execution)
                    
                    # Handle errors
                    if execution.error:
                        self.handle_code_execution_error(execution, user_input)
                else:
                    self.display_message(code, "assistant", "code")
        
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.console.print(f"❌ {error_msg}", style="red")
            self.session_manager.add_message("system", error_msg, "error")
    
    def show_session_info(self):
        """Display current session information."""
        if not self.session_manager.current_session:
            self.console.print("❌ No active session", style="red")
            return
        
        stats = self.session_manager.get_session_stats()
        
        table = Table(title="📊 Session Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Session ID", stats["session_id"])
        table.add_row("Title", stats["title"])
        table.add_row("Created", stats["created_at"])
        table.add_row("Messages", str(stats["total_messages"]))
        table.add_row("Code Executions", str(stats["total_code_executions"]))
        table.add_row("LLM Provider", stats["llm_provider"])
        table.add_row("LLM Model", stats["llm_model"])
        
        self.console.print(table)
    
    def show_help(self):
        """Display help information."""
        help_text = """
# OrionAI Interactive Chat Commands

## Basic Commands
- **exit** or **quit**: Exit the chat session
- **help**: Show this help message
- **info**: Show current session information
- **clear**: Clear the screen
- **save**: Save current session
- **history**: Show conversation history

## Code Execution
- Code blocks in responses are automatically executed
- Images and plots are saved to the session folder
- Errors are automatically sent back to LLM for fixing

## Session Management
- Sessions are auto-saved in `~/.orionai/sessions/{session_id}/`
- Images saved in `images/` subfolder
- Reports saved in `reports/` subfolder

## Tips
- Ask for data analysis, visualizations, or any Python task
- Request modifications to previous code
- Ask for explanations of generated code
- Request specific file formats or outputs
"""
        self.console.print(Panel(Markdown(help_text), title="📖 Help", title_align="left"))
    
    def run(self):
        """Run the interactive chat session."""
        # Setup LLM on demand
        if not self.setup_llm():
            self.console.print("❌ LLM not configured. Please run setup first.", style="red")
            return

        # Welcome message
        self.console.print(Panel.fit(
            "🚀 Welcome to OrionAI Interactive Chat!\n"
            f"Session: {self.session_manager.current_session.session_id}\n"
            f"LLM: {self.config_manager.config.llm.provider} ({self.config_manager.config.llm.model})\n"
            "Type 'help' for commands, 'exit' to quit.",
            style="bold blue"
        ))
        
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]", console=self.console).strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ["exit", "quit"]:
                    self.console.print("👋 Goodbye!", style="yellow")
                    break
                elif user_input.lower() == "help":
                    self.show_help()
                    continue
                elif user_input.lower() == "info":
                    self.show_session_info()
                    continue
                elif user_input.lower() == "clear":
                    self.console.clear()
                    continue
                elif user_input.lower() == "save":
                    self.session_manager.save_session()
                    self.console.print("💾 Session saved!", style="green")
                    continue
                elif user_input.lower() == "history":
                    history = self.session_manager.get_conversation_history(limit=10)
                    for msg in history:
                        role_emoji = "🙋" if msg.role == "user" else "🤖"
                        self.console.print(f"{role_emoji} [{msg.timestamp}] {msg.content[:100]}...")
                    continue
                
                # Process normal input
                self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n👋 Goodbye!", style="yellow")
                break
            except Exception as e:
                self.console.print(f"❌ Unexpected error: {e}", style="red")
