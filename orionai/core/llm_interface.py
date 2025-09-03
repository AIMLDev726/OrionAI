"""
LLM Interface for OrionAI
=========================

Provides pluggable interface for different LLM providers (OpenAI, Anthropic, Google, Local Models)
with the specific prompt structure designed for safe code generation and MCP integration.
"""

import json
import logging
import configparser
from typing import Any, Dict, Optional, Protocol, List
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    """Protocol for LLM providers."""
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
        ...


class OpenAIProvider:
    """OpenAI GPT provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        # Lazy import to prevent blocking on module load
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0),  # Deterministic by default
                max_tokens=kwargs.get("max_tokens", 1000)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise


class AnthropicProvider:
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("anthropic package required for AnthropicProvider")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 1000),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise


class GoogleProvider:
    """Google Gemini provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-pro"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Configure safety settings to be less restrictive
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            self.model = genai.GenerativeModel(
                model_name=model,
                safety_settings=safety_settings
            )
            self.model_name = model
        except ImportError:
            raise ImportError("google-generativeai package required for GoogleProvider")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Google Gemini API."""
        try:
            generation_config = {
                "temperature": kwargs.get("temperature", 0.7),
                "max_output_tokens": kwargs.get("max_tokens", 2000),
                "top_k": 40,
                "top_p": 0.95,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Handle cases where response is blocked or empty
            if not response.candidates:
                return "I apologize, but I couldn't generate a response. Please try rephrasing your request."
            
            candidate = response.candidates[0]
            
            # Check if content was blocked
            if candidate.finish_reason.name in ["SAFETY", "RECITATION"]:
                return "I apologize, but I cannot generate this content due to safety policies. Please try a different request."
            
            # Check if we have valid content
            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                return candidate.content.parts[0].text
            else:
                return "I apologize, but I couldn't generate a proper response. Please try again."
                
        except Exception as e:
            logger.error(f"Google API error: {str(e)}")
            # Return a more user-friendly error message
            if "finish_reason" in str(e):
                return "I apologize, but the content was filtered by safety policies. Please try rephrasing your request."
            return f"I encountered an error: {str(e)}. Please try again."


class LocalModelProvider:
    """Local AI model provider wrapper."""
    
    def __init__(self, provider_name: str = "ollama", model: str = "llama3"):
        try:
            from .local_models import LocalModelManager
            self.local_manager = LocalModelManager()
            self.provider_name = provider_name
            self.model = model
            
            # Get the actual provider
            if provider_name in self.local_manager.providers:
                self.provider = self.local_manager.providers[provider_name]
            elif provider_name in self.local_manager.custom_providers:
                self.provider = self.local_manager.custom_providers[provider_name]
            else:
                raise ValueError(f"Local provider '{provider_name}' not found")
            
            # Set model
            self.provider.model = model
            
            if not self.provider.available:
                raise ValueError(f"Local provider '{provider_name}' is not available")
                
        except ImportError:
            raise ImportError("Local models module required for LocalModelProvider")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using local model."""
        try:
            response = self.provider.generate(prompt, **kwargs)
            return response
        except Exception as e:
            logger.error(f"Local model error: {str(e)}")
            raise


class LLMInterface:
    """
    Main LLM interface that implements the OrionAI prompt structure.
    """
    
    # Core system prompt for object-based operations
    SYSTEM_PROMPT = """You are OrionAI, an AI coding assistant.
Your role is to translate user queries into SAFE Python code snippets
that operate on the provided object context. 

RULES:
1. Always return VALID Python code inside triple backticks.
2. Never invent column names, methods, or functions.
3. Use only the provided object context.
4. If the query cannot be answered, reply with: "Not possible with current object."
5. Output format must include:
   - `explanation`: short description of what code does.
   - `code`: the Python code (inside ```python).
   - `expected_output`: structured description of what user will see.

Return your response in JSON format:
{
  "explanation": "...",
  "code": "```python\\n...\\n```",
  "expected_output": "..."
}"""

    # General chat prompt for flexible interactions with MCP support
    CHAT_PROMPT = """You are OrionAI, a helpful AI coding assistant with access to external tools via Model Context Protocol (MCP) and web search capabilities.

You can help with:
- Writing Python code for any task
- Explaining programming concepts
- Debugging and fixing code issues
- Data analysis and visualization
- General programming questions
- Using MCP tools for calculations and data operations
- Web search for current/real-time information

DECISION LOGIC:
1. For CALCULATIONS and MATH: Always use MCP tools (calculate, add, multiply, etc.)
2. For CURRENT/REAL-TIME INFO: Use web search (weather, news, prices, scores, recent events)
3. For PROGRAMMING: Provide code solutions
4. For GENERAL KNOWLEDGE: Use your training data

IMPORTANT: When the user asks for calculations, dates, or other operations that can be done with MCP tools, ALWAYS use the tools instead of writing code or searching the web.

Available MCP tools include:
- calculate: For mathematical calculations (arguments: {"expression": "math expression"})
- add: Add two numbers (arguments: {"a": number, "b": number})
- multiply: Multiply two numbers (arguments: {"a": number, "b": number})
- current_time: Get current date and time (arguments: {})
- timestamp: Get Unix timestamp (arguments: {})
- format_date: Format timestamp (arguments: {"timestamp": number})

To use an MCP tool, respond with a JSON object:
{
  "action": "use_tool",
  "tool_name": "calculate",
  "arguments": {"expression": "2 + 2"},
  "reasoning": "User asked for a calculation"
}

Examples of MCP tool usage:
- "What is 2+2?" → Use calculate tool with {"expression": "2 + 2"}
- "Calculate 15 * 23" → Use calculate tool
- "What's 50 + 75?" → Use calculate tool
- "Add 25 and 30" → Use add tool or calculate tool

DO NOT use web search for:
- Simple math calculations (2+2, 15*23, etc.)
- Basic programming questions
- Code generation requests
- General definitions

For web search situations (handled automatically by the system):
- Current weather, stock prices, news
- Recent events or developments
- Real-time information that changes frequently

When providing code examples:
1. Use proper Python syntax
2. Include helpful comments
3. Provide complete, runnable code
4. Explain what the code does

If the user asks for code, provide it in Python code blocks using ```python syntax.
Be helpful, accurate, and educational in your responses."""
    
    def __init__(self, provider: Optional[LLMProvider] = None, mcp_manager=None):
        """
        Initialize LLM interface.
        
        Args:
            provider: LLM provider instance (defaults to auto-detection based on config)
            mcp_manager: MCP manager for tool access
        """
        if provider:
            self.provider = provider
        else:
            # Auto-detect provider from config
            try:
                from ..cli.config import ConfigManager
                config_manager = ConfigManager()
                api_key = config_manager.get_api_key()
                
                if api_key and config_manager.config.llm.provider:
                    provider_classes = {
                        "openai": OpenAIProvider,
                        "anthropic": AnthropicProvider,
                        "google": GoogleProvider
                    }
                    
                    provider_class = provider_classes.get(config_manager.config.llm.provider, OpenAIProvider)
                    self.provider = provider_class(
                        api_key=api_key,
                        model=config_manager.config.llm.model
                    )
                else:
                    # Fallback to OpenAI with no key (will fail gracefully)
                    self.provider = OpenAIProvider()
            except Exception:
                # Ultimate fallback
                self.provider = OpenAIProvider()
                
        self.mcp_manager = mcp_manager
        
        # Load configuration
        self._load_config()
        
        logger.info(f"LLMInterface initialized with {type(self.provider).__name__}")
        
        if self.mcp_manager:
            logger.info("MCP integration enabled")
    
    def _load_config(self):
        """Load configuration from config file."""
        config = configparser.ConfigParser()
        config_path = Path(__file__).parent.parent / "config" / "prompts.ini"
        
        if config_path.exists():
            config.read(config_path)
            self.CHAT_PROMPT = config.get('PROMPTS', 'CHAT_PROMPT', fallback=self.CHAT_PROMPT)
        else:
            logger.warning(f"Config file not found: {config_path}")
    
    def _build_mcp_context(self) -> str:
        """Build MCP context information for the LLM."""
        if not self.mcp_manager:
            return ""
        
        try:
            # Get available tools
            tools = self.mcp_manager.get_available_tools()
            if not tools:
                return ""
            
            context_parts = ["\n--- Available MCP Tools ---"]
            
            for tool in tools[:10]:  # Limit to first 10 tools
                context_parts.append(f"• {tool['name']}: {tool['description']}")
                
                # Add input schema info
                schema = tool.get('input_schema', {})
                properties = schema.get('properties', {})
                if properties:
                    required = schema.get('required', [])
                    params = []
                    for prop, info in properties.items():
                        prop_type = info.get('type', 'string')
                        is_req = " (required)" if prop in required else ""
                        params.append(f"{prop}: {prop_type}{is_req}")
                    
                    if params:
                        context_parts.append(f"  Parameters: {', '.join(params[:3])}")  # First 3 params
            
            if len(tools) > 10:
                context_parts.append(f"... and {len(tools) - 10} more tools available")
            
            context_parts.append("--- End MCP Tools ---\n")
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.warning(f"Failed to build MCP context: {e}")
            return ""
    
    def _try_execute_mcp_tool(self, response: str, original_query: str = "") -> tuple[bool, str]:
        """
        Try to execute MCP tool if response contains tool usage.
        
        Args:
            response: LLM response
            original_query: Original user query (for extracting missing arguments)
            
        Returns:
            Tuple of (tool_executed, final_response)
        """
        if not self.mcp_manager:
            return False, response
        
        try:
            # Try to parse JSON tool usage
            response_stripped = response.strip()
            if response_stripped.startswith('{') and response_stripped.endswith('}'):
                try:
                    tool_request = json.loads(response_stripped)
                    
                    if (tool_request.get('action') == 'use_tool' and 
                        'tool_name' in tool_request):
                        
                        tool_name = tool_request['tool_name']
                        arguments = tool_request.get('arguments', {})
                        reasoning = tool_request.get('reasoning', '')
                        
                        # Handle common cases where arguments are missing or tool names need fixing
                        if tool_name == 'calculator':
                            tool_name = 'calculate'  # Fix tool name
                            if not arguments or 'expression' not in arguments:
                                # Try to extract expression from original query first, then reasoning
                                import re
                                math_patterns = [
                                    r'(\d+\s*[\+\-\*\/]\s*\d+)',  # Simple expressions like "2+2" or "15 * 23"
                                    r'calculate\s+(.+)',  # "calculate 2+2"
                                    r'what\s+is\s+(.+\?)',  # "what is 2+2?"
                                ]
                                
                                expression = None
                                for pattern in math_patterns:
                                    match = re.search(pattern, original_query, re.IGNORECASE)
                                    if match:
                                        expression = match.group(1).strip('?').strip()
                                        break
                                
                                if not expression:
                                    # Fallback to reasoning patterns
                                    if '2+2' in reasoning or '2 + 2' in reasoning:
                                        expression = '2 + 2'
                                    elif 'current date' in reasoning.lower():
                                        # User wanted date, not calculator
                                        tool_name = 'current_time'
                                        arguments = {}
                                        expression = None
                                
                                if expression:
                                    arguments = {'expression': expression}
                                elif tool_name == 'calculate':
                                    return True, f"❌ Tool '{tool_name}' requires an expression argument. Please specify what to calculate."
                        
                        elif tool_name == 'datetime-tools':
                            tool_name = 'current_time'  # Fix tool name
                            arguments = {}
                        
                        elif tool_name in ['current_time', 'timestamp', 'format_date'] and not arguments:
                            # These tools can work with empty arguments
                            arguments = {}
                        
                        elif tool_name == 'web_search':
                            # Handle web search tool
                            if not arguments or 'query' not in arguments:
                                # Try to extract query from original query or reasoning
                                search_query = original_query
                                if search_query:
                                    arguments = {'query': search_query}
                                else:
                                    return True, f"❌ Tool '{tool_name}' requires a query argument."
                        
                        logger.info(f"Executing MCP tool: {tool_name} with args: {arguments}")
                        
                        # Handle built-in tools vs MCP tools
                        if tool_name == 'web_search':
                            # Web search now handled by MCP servers
                            return True, "ℹ️  Web search is now available through MCP servers. Please install web search MCP servers using CLI menu option 5."
                            
                        else:
                            # Execute MCP tool
                            result = self.mcp_manager.call_tool(tool_name, arguments)
                        
                        # Return just the tool result for the LLM to process
                        if result:
                            if isinstance(result, dict) and 'content' in result:
                                # Extract content from MCP response
                                content = result['content']
                                if isinstance(content, list) and content:
                                    tool_output = content[0].get('text', str(result))
                                else:
                                    tool_output = str(content)
                            else:
                                tool_output = str(result)
                            
                            return True, tool_output
                        else:
                            return True, "Tool executed but returned no result"
                            
                except json.JSONDecodeError:
                    pass  # Not a JSON tool request
            
            # Check for tool usage in text format (fallback)
            import re
            tool_pattern = r'Error calling tool (\w+): (.+)'
            match = re.search(tool_pattern, response)
            
            if match:
                tool_name = match.group(1)
                error_msg = match.group(2)
                
                # Try to execute the tool that failed
                logger.info(f"Retrying failed tool: {tool_name}")
                
                # Simple argument extraction for common tools
                if tool_name == 'calculator':
                    # Try to find expression in original response
                    expr_match = re.search(r'(\d+\s*[\+\-\*/]\s*\d+)', response)
                    if expr_match:
                        expression = expr_match.group(1)
                        try:
                            result = self.mcp_manager.call_tool(tool_name, {'expression': expression})
                            if result and 'content' in result:
                                content = result['content']
                                if isinstance(content, list) and content:
                                    tool_output = content[0].get('text', str(result))
                                    return True, f"🔧 **Calculator Result**: {tool_output}"
                        except Exception as e:
                            logger.error(f"Tool retry failed: {e}")
                
                return True, f"❌ Error executing tool: {error_msg}"
            
            return False, response
            
        except Exception as e:
            logger.error(f"Error in MCP tool execution: {e}")
            return False, response
    
    def generate_chat_response(self, query: str, conversation_history: List[Dict[str, str]] = None, **kwargs) -> str:
        """
        Generate a chat response for general queries with MCP support.
        
        Args:
            query: User's query
            conversation_history: Previous conversation messages
            **kwargs: Additional parameters for LLM
            
        Returns:
            LLM response text with potential MCP tool execution
        """
        # Build conversation context
        messages = []
        
        # Add system message with MCP context
        system_prompt = self.CHAT_PROMPT
        mcp_context = self._build_mcp_context()
        if mcp_context:
            system_prompt += f"\n{mcp_context}"
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append(msg)
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        # Build prompt for providers that don't support messages
        if isinstance(self.provider, GoogleProvider):
            # Google provider needs a single prompt
            prompt_parts = [system_prompt]
            
            if conversation_history:
                prompt_parts.append("\nConversation History:")
                for msg in conversation_history[-5:]:
                    role = "Human" if msg["role"] == "user" else "Assistant"
                    prompt_parts.append(f"{role}: {msg['content']}")
            
            prompt_parts.append(f"\nHuman: {query}")
            prompt_parts.append("\nAssistant:")
            
            prompt = "\n".join(prompt_parts)
        else:
            # For OpenAI and Anthropic, use the query with system context
            prompt = f"{system_prompt}\n\nUser: {query}\n\nAssistant:"
        
        try:
            # Initial LLM response
            response = self.provider.generate(prompt, **kwargs)
            logger.debug(f"Initial LLM response: {response}")
            
            # Check if LLM requested a tool
            tool_executed, tool_result = self._try_execute_mcp_tool(response, query)
            logger.debug(f"Tool execution result: executed={tool_executed}, result={tool_result}")
            
            if tool_executed:
                if not tool_result:
                    logger.warning("Tool was executed but returned empty result")
                    return "Tool was executed but no result was returned."
                
                # LLM requested a tool, continue the conversation with the tool result
                # Build follow-up prompt to get a natural response incorporating the tool result
                follow_up_prompt_parts = [
                    f"User asked: {query}",
                    f"You used a tool and got this result: {tool_result}",
                    "Now provide a helpful, natural response to the user incorporating this result. Do not show the raw tool output or JSON."
                ]
                
                if isinstance(self.provider, GoogleProvider):
                    # Google provider needs a single prompt
                    follow_up_parts = [system_prompt.replace("To use an MCP tool, respond with a JSON object:", "")]
                    
                    if conversation_history:
                        follow_up_parts.append("\nConversation History:")
                        for msg in conversation_history[-3:]:  # Reduced to avoid token limits
                            role = "Human" if msg["role"] == "user" else "Assistant"
                            follow_up_parts.append(f"{role}: {msg['content']}")
                    
                    follow_up_parts.extend([
                        f"\nHuman: {query}",
                        f"Tool Result: {tool_result}",
                        "Assistant: "
                    ])
                    
                    follow_up_prompt = "\n".join(follow_up_parts)
                else:
                    # For OpenAI and Anthropic
                    follow_up_prompt = f"{system_prompt.replace('To use an MCP tool, respond with a JSON object:', '')}\n\n" + "\n".join(follow_up_prompt_parts) + "\n\nAssistant:"
                
                # Get final response from LLM with modified parameters to encourage natural response
                final_kwargs = kwargs.copy()
                final_kwargs.setdefault('temperature', 0.7)  # Slightly higher temperature for more natural responses
                
                final_response = self.provider.generate(follow_up_prompt, **final_kwargs)
                logger.debug(f"Final LLM response: {final_response}")
                
                # Clean up any residual JSON or tool references
                if final_response.strip().startswith('{') and final_response.strip().endswith('}'):
                    # If LLM still returns JSON, extract a natural response
                    return f"Based on the calculation result: {tool_result}"
                
                return final_response
            else:
                # No tool was used, return the original response
                return response
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    
    def generate_code(self, query: str, context: Dict[str, Any], **kwargs) -> str:
        """
        Generate Python code for the given query and context.
        
        Args:
            query: User's natural language query
            context: Object metadata and context
            **kwargs: Additional parameters for LLM
            
        Returns:
            JSON string with explanation, code, and expected output
        """
        prompt = self._build_prompt(query, context)
        
        try:
            response = self.provider.generate(prompt, **kwargs)
            logger.debug(f"LLM response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            # Return fallback response
            return json.dumps({
                "explanation": "Error occurred during code generation",
                "code": "```python\\n# Error: Could not generate code\\npass\\n```",
                "expected_output": "Error message"
            })
    
    def explain_object(self, metadata: Dict[str, Any]) -> str:
        """
        Generate explanation of object structure and content.
        
        Args:
            metadata: Object metadata
            
        Returns:
            Human-readable explanation
        """
        prompt = f"""Explain the following object in simple terms:

Object Type: {metadata.get('type', 'Unknown')}
Metadata: {json.dumps(metadata, indent=2)}

Provide a clear, concise explanation of what this object contains and what operations might be useful."""
        
        try:
            return self.provider.generate(prompt, temperature=0.3)
        except Exception as e:
            logger.error(f"Error explaining object: {str(e)}")
            return f"Unable to explain {metadata.get('type', 'object')} due to error."
    
    def _build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """
        Build the complete prompt following OrionAI template.
        
        Args:
            query: User query
            context: Context dictionary
            
        Returns:
            Complete prompt string
        """
        # Extract metadata
        object_metadata = context.get("object_metadata", {})
        previous_queries = context.get("previous_queries", [])
        
        # Build context section
        context_section = f"""Object Type: {object_metadata.get('type', 'Unknown')}
Object Metadata: {json.dumps(object_metadata, indent=2)}"""
        
        # Add previous queries if available
        if previous_queries:
            history = "\\n".join([
                f"- {q['query']} -> {q['explanation']}" 
                for q in previous_queries[-3:]  # Last 3 queries
            ])
            context_section += f"\\n\\nPrevious Queries:\\n{history}"
        
        # Complete prompt
        prompt = f"""{self.SYSTEM_PROMPT}

User Query:
{query}

Context:
{context_section}

Instruction:
Translate user request into safe Python code operating ONLY on the given context.
Use 'obj' as the variable name for the main object.

Return in JSON format as specified above."""
        
        return prompt
