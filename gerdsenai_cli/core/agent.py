"""
Agent Logic for GerdsenAI CLI.

This module implements the core agent that processes user prompts, parses LLM responses
for action intents, and orchestrates context-aware operations like file editing and
project analysis.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from .context_manager import ProjectContext
from .file_editor import FileEditor, EditOperation
from .llm_client import LLMClient, ChatMessage
from ..config.settings import Settings
from ..utils.display import show_error, show_info, show_success, show_warning

logger = logging.getLogger(__name__)
console = Console()


class ActionType(Enum):
    """Types of actions the agent can perform."""
    CHAT = "chat"
    ANALYZE_PROJECT = "analyze_project"
    EDIT_FILE = "edit_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    READ_FILE = "read_file"
    SEARCH_FILES = "search_files"
    EXPLAIN_CODE = "explain_code"
    EXECUTE_COMMAND = "execute_command"
    NONE = "none"


@dataclass
class ActionIntent:
    """Represents an action intent parsed from LLM response."""
    action_type: ActionType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None
    requires_confirmation: bool = False
    
    def __post_init__(self):
        """Initialize computed properties."""
        # File operations require confirmation by default
        if self.action_type in {ActionType.EDIT_FILE, ActionType.CREATE_FILE, ActionType.DELETE_FILE}:
            self.requires_confirmation = True


@dataclass
class ConversationContext:
    """Maintains conversation state and context."""
    messages: List[ChatMessage] = field(default_factory=list)
    project_context_built: bool = False
    last_action: Optional[ActionIntent] = None
    pending_edits: List[str] = field(default_factory=list)
    session_metadata: Dict[str, Any] = field(default_factory=dict)


class IntentParser:
    """Parses LLM responses for action intents."""
    
    def __init__(self):
        """Initialize intent parser with patterns and keywords."""
        # Patterns for detecting different intent types
        self.file_patterns = {
            'edit': [
                r'(?:edit|modify|change|update|fix)\s+(?:the\s+)?file\s+([^\s\n]+)',
                r'(?:make\s+changes?\s+to|update)\s+([^\s\n]+)',
                r'(?:in\s+)?file\s+([^\s\n]+).*(?:change|edit|modify)',
            ],
            'create': [
                r'create\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+)?([^\s\n]+)',
                r'(?:make|add)\s+(?:a\s+)?(?:new\s+)?file\s+([^\s\n]+)',
                r'(?:write|generate)\s+(?:a\s+)?file\s+([^\s\n]+)',
            ],
            'read': [
                r'(?:read|show|display|examine)\s+(?:the\s+)?file\s+([^\s\n]+)',
                r'(?:what\'?s\s+in|contents?\s+of)\s+(?:the\s+)?file\s+([^\s\n]+)',
                r'(?:look\s+at|check)\s+(?:the\s+)?file\s+([^\s\n]+)',
            ],
            'delete': [
                r'(?:delete|remove)\s+(?:the\s+)?file\s+([^\s\n]+)',
                r'(?:get\s+rid\s+of|eliminate)\s+(?:the\s+)?file\s+([^\s\n]+)',
            ]
        }
        
        self.analysis_keywords = {
            'project_structure', 'analyze', 'overview', 'summary', 'architecture',
            'codebase', 'project', 'structure', 'organization', 'files'
        }
        
        self.search_keywords = {
            'find', 'search', 'locate', 'look for', 'grep', 'where is'
        }
    
    def parse_intent(self, llm_response: str, user_query: str = "") -> ActionIntent:
        """Parse LLM response to determine action intent."""
        response_lower = llm_response.lower()
        query_lower = user_query.lower()
        
        # Try to detect file operations first
        file_intent = self._parse_file_intent(llm_response, user_query)
        if file_intent.action_type != ActionType.NONE:
            return file_intent
        
        # Check for project analysis intent
        if self._contains_keywords(response_lower + " " + query_lower, self.analysis_keywords):
            return ActionIntent(
                action_type=ActionType.ANALYZE_PROJECT,
                confidence=0.8,
                reasoning="Request appears to be asking for project analysis"
            )
        
        # Check for search intent
        if self._contains_keywords(response_lower + " " + query_lower, self.search_keywords):
            search_term = self._extract_search_term(user_query)
            return ActionIntent(
                action_type=ActionType.SEARCH_FILES,
                confidence=0.7,
                parameters={"query": search_term} if search_term else {},
                reasoning="Request appears to be searching for something"
            )
        
        # Check for code explanation intent
        if any(keyword in response_lower for keyword in ['explain', 'how does', 'what does', 'understand']):
            return ActionIntent(
                action_type=ActionType.EXPLAIN_CODE,
                confidence=0.6,
                reasoning="Request appears to be asking for code explanation"
            )
        
        # Default to chat
        return ActionIntent(
            action_type=ActionType.CHAT,
            confidence=0.9,
            reasoning="Standard conversational response"
        )
    
    def _parse_file_intent(self, response: str, query: str) -> ActionIntent:
        """Parse for file-specific intents."""
        combined_text = response + " " + query
        
        # Try each file operation type
        for operation, patterns in self.file_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    file_path = match.group(1).strip('"`\'')
                    
                    action_type_map = {
                        'edit': ActionType.EDIT_FILE,
                        'create': ActionType.CREATE_FILE,
                        'read': ActionType.READ_FILE,
                        'delete': ActionType.DELETE_FILE
                    }
                    
                    return ActionIntent(
                        action_type=action_type_map[operation],
                        confidence=0.9,
                        parameters={"file_path": file_path},
                        reasoning=f"Detected {operation} operation on file: {file_path}"
                    )
        
        return ActionIntent(action_type=ActionType.NONE, confidence=0.0)
    
    def _contains_keywords(self, text: str, keywords: set) -> bool:
        """Check if text contains any of the specified keywords."""
        return any(keyword in text for keyword in keywords)
    
    def _extract_search_term(self, query: str) -> Optional[str]:
        """Extract search term from query."""
        # Simple extraction - look for quoted terms or after "for"
        quoted_match = re.search(r'["\']([^"\']+)["\']', query)
        if quoted_match:
            return quoted_match.group(1)
        
        for_match = re.search(r'(?:for|find)\s+([^\s\n]+)', query, re.IGNORECASE)
        if for_match:
            return for_match.group(1)
        
        return None


class Agent:
    """Main agent that orchestrates AI-driven actions."""
    
    def __init__(
        self,
        llm_client: LLMClient,
        settings: Settings,
        project_root: Optional[Path] = None
    ):
        """Initialize the agent with required components."""
        self.llm_client = llm_client
        self.settings = settings
        
        # Initialize core components
        self.context_manager = ProjectContext(project_root)
        self.file_editor = FileEditor()
        self.intent_parser = IntentParser()
        
        # Conversation state
        self.conversation = ConversationContext()
        
        # Agent settings
        self.max_context_length = settings.get_preference("max_context_length", 4000)
        self.auto_analyze_project = True
        self.confirm_destructive_actions = True
        
        # Performance tracking
        self.actions_performed = 0
        self.files_modified = 0
        self.context_builds = 0
    
    async def initialize(self) -> bool:
        """Initialize the agent and optionally analyze the project."""
        try:
            show_info("Initializing AI agent...")
            
            # Perform initial project scan if enabled
            if self.auto_analyze_project:
                await self._analyze_project_structure()
            
            show_success("AI agent initialized and ready!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            show_error(f"Failed to initialize agent: {e}")
            return False
    
    async def process_user_input(self, user_input: str) -> str:
        """Process user input and return agent response."""
        try:
            # Add user message to conversation
            user_message = ChatMessage(role="user", content=user_input)
            self.conversation.messages.append(user_message)
            
            # Build context for LLM if needed
            context_prompt = ""
            if not self.conversation.project_context_built:
                context_prompt = await self._build_project_context(user_input)
                self.conversation.project_context_built = True
            
            # Prepare messages for LLM
            llm_messages = self._prepare_llm_messages(user_input, context_prompt)
            
            # Get LLM response
            with console.status("[bold green]Thinking...", spinner="dots"):
                llm_response = await self.llm_client.chat(llm_messages)
            
            if not llm_response:
                return "I apologize, but I'm having trouble connecting to the AI model. Please try again."
            
            # Add assistant response to conversation
            assistant_message = ChatMessage(role="assistant", content=llm_response)
            self.conversation.messages.append(assistant_message)
            
            # Parse intent and potentially perform actions
            intent = self.intent_parser.parse_intent(llm_response, user_input)
            self.conversation.last_action = intent
            
            # Execute action if needed
            action_result = await self._execute_action(intent, user_input, llm_response)
            
            # Combine LLM response with action results
            final_response = self._format_final_response(llm_response, action_result, intent)
            
            self.actions_performed += 1
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return f"I encountered an error while processing your request: {e}"
    
    async def _analyze_project_structure(self) -> None:
        """Analyze the current project structure."""
        try:
            show_info("Analyzing project structure...")
            
            await self.context_manager.scan_directory(
                max_depth=10,
                include_hidden=False,
                respect_gitignore=True
            )
            
            stats = self.context_manager.get_project_stats()
            show_success(f"Project analysis complete: {stats.total_files} files found")
            
            self.context_builds += 1
            
        except Exception as e:
            logger.error(f"Failed to analyze project: {e}")
            show_warning(f"Could not analyze project structure: {e}")
    
    async def _build_project_context(self, user_query: str = "") -> str:
        """Build project context for LLM."""
        try:
            if not self.context_manager.files:
                await self._analyze_project_structure()
            
            context = await self.context_manager.build_context_prompt(
                query=user_query,
                include_file_contents=True,
                max_context_length=self.max_context_length
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to build context: {e}")
            return ""
    
    def _prepare_llm_messages(self, user_input: str, context_prompt: str = "") -> List[ChatMessage]:
        """Prepare messages for LLM with appropriate context."""
        messages = []
        
        # Add system message with context
        system_content = self._build_system_prompt()
        if context_prompt:
            system_content += f"\n\n# Current Project Context\n{context_prompt}"
        
        messages.append(ChatMessage(role="system", content=system_content))
        
        # Add conversation history (limit to recent messages to stay within context)
        recent_messages = self.conversation.messages[-10:]  # Last 10 messages
        messages.extend(recent_messages)
        
        return messages
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the LLM."""
        return """You are GerdsenAI, an intelligent coding assistant with the ability to understand and modify codebases. You can:

1. **Analyze Projects**: Understand code structure, architecture, and file relationships
2. **Edit Files**: Make precise changes to existing files with proper diff previews
3. **Create Files**: Generate new files with appropriate content
4. **Read Files**: Examine file contents and explain code functionality
5. **Search Code**: Find specific patterns, functions, or content across the project

## Guidelines:
- Always provide clear explanations of what you're doing and why
- When editing files, be precise and explain the changes
- Respect existing code style and conventions
- Ask for confirmation before making destructive changes
- Provide helpful context about the codebase when relevant
- Be concise but thorough in your responses

## Current Capabilities:
- Project structure analysis with intelligent file filtering
- Safe file editing with backup and rollback capabilities
- Context-aware code understanding
- Diff generation and preview for changes

When working with files, I will:
1. Show you exactly what changes I plan to make
2. Ask for your confirmation before applying changes
3. Create backups automatically
4. Provide rollback options if needed

How can I help you with your code today?"""
    
    async def _execute_action(self, intent: ActionIntent, user_input: str, llm_response: str) -> Optional[str]:
        """Execute the determined action and return result description."""
        try:
            if intent.action_type == ActionType.CHAT:
                return None  # No additional action needed
            
            elif intent.action_type == ActionType.ANALYZE_PROJECT:
                return await self._handle_project_analysis()
            
            elif intent.action_type == ActionType.EDIT_FILE:
                return await self._handle_file_edit(intent, llm_response)
            
            elif intent.action_type == ActionType.CREATE_FILE:
                return await self._handle_file_creation(intent, llm_response)
            
            elif intent.action_type == ActionType.READ_FILE:
                return await self._handle_file_read(intent)
            
            elif intent.action_type == ActionType.SEARCH_FILES:
                return await self._handle_file_search(intent)
            
            elif intent.action_type == ActionType.EXPLAIN_CODE:
                return await self._handle_code_explanation(intent, user_input)
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing action {intent.action_type}: {e}")
            return f"Error executing action: {e}"
    
    async def _handle_project_analysis(self) -> str:
        """Handle project analysis request."""
        if not self.context_manager.files:
            await self._analyze_project_structure()
        
        stats = self.context_manager.get_project_stats()
        
        result = f"\n## Project Analysis Results\n\n"
        result += f"**Statistics:**\n"
        result += f"- Total files: {stats.total_files}\n"
        result += f"- Text files: {stats.text_files}\n"
        result += f"- Total size: {self._format_size(stats.total_size)}\n\n"
        
        if stats.languages:
            result += f"**Languages/File Types:**\n"
            sorted_langs = sorted(stats.languages.items(), key=lambda x: x[1], reverse=True)
            for ext, count in sorted_langs[:10]:
                result += f"- {ext}: {count} files\n"
        
        return result
    
    async def _handle_file_edit(self, intent: ActionIntent, llm_response: str) -> str:
        """Handle file editing request."""
        file_path_str = intent.parameters.get("file_path", "")
        if not file_path_str:
            return "No file path specified for editing."
        
        file_path = Path(file_path_str)
        
        # Try to extract new content from LLM response
        new_content = self._extract_code_from_response(llm_response)
        if not new_content:
            return "Could not extract new file content from response."
        
        # Propose the edit
        edit = await self.file_editor.propose_edit(file_path, new_content, EditOperation.MODIFY)
        if not edit:
            return "Failed to propose file edit."
        
        # Apply the edit (will show preview and ask for confirmation)
        success = await self.file_editor.apply_edit(edit)
        
        if success:
            self.files_modified += 1
            return f"Successfully edited file: {file_path}"
        else:
            return f"Failed to edit file: {file_path}"
    
    async def _handle_file_creation(self, intent: ActionIntent, llm_response: str) -> str:
        """Handle file creation request."""
        file_path_str = intent.parameters.get("file_path", "")
        if not file_path_str:
            return "No file path specified for creation."
        
        file_path = Path(file_path_str)
        
        # Extract content from LLM response
        new_content = self._extract_code_from_response(llm_response)
        if not new_content:
            return "Could not extract file content from response."
        
        # Propose the creation
        edit = await self.file_editor.propose_edit(file_path, new_content, EditOperation.CREATE)
        if not edit:
            return "Failed to propose file creation."
        
        # Apply the edit
        success = await self.file_editor.apply_edit(edit)
        
        if success:
            self.files_modified += 1
            return f"Successfully created file: {file_path}"
        else:
            return f"Failed to create file: {file_path}"
    
    async def _handle_file_read(self, intent: ActionIntent) -> str:
        """Handle file reading request."""
        file_path_str = intent.parameters.get("file_path", "")
        if not file_path_str:
            return "No file path specified for reading."
        
        file_path = Path(file_path_str)
        
        # Read file content
        content = await self.context_manager.read_file_content(file_path)
        if content is None:
            return f"Could not read file: {file_path}"
        
        return f"\n## File Contents: {file_path}\n\n```\n{content}\n```"
    
    async def _handle_file_search(self, intent: ActionIntent) -> str:
        """Handle file search request."""
        query = intent.parameters.get("query", "")
        if not query:
            return "No search query specified."
        
        # Search for relevant files
        relevant_files = self.context_manager.get_relevant_files(query=query, max_files=10)
        
        if not relevant_files:
            return f"No files found matching query: {query}"
        
        result = f"\n## Search Results for '{query}':\n\n"
        for file_info in relevant_files:
            result += f"{file_info.relative_path}\n"
        
        return result
    
    async def _handle_code_explanation(self, intent: ActionIntent, user_input: str) -> str:
        """Handle code explanation request."""
        # This is handled by the LLM response itself, just add context
        return "\n*Code explanation provided in the main response above.*"
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract code content from LLM response."""
        # Look for code blocks
        code_block_pattern = r'```(?:\w+)?\n?(.*?)\n?```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            # Return the largest code block
            return max(matches, key=len).strip()
        
        # If no code blocks, look for lines that look like code
        lines = response.split('\n')
        code_lines = []
        in_code_section = False
        
        for line in lines:
            # Simple heuristics for code detection
            if any(char in line for char in ['{', '}', '(', ')', '=', ';']) and len(line.strip()) > 0:
                in_code_section = True
                code_lines.append(line)
            elif in_code_section and line.strip() == '':
                code_lines.append(line)
            elif in_code_section and not any(char in line for char in ['{', '}', '(', ')', '=', ';']):
                break  # End of code section
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        return None
    
    def _format_final_response(self, llm_response: str, action_result: Optional[str], intent: ActionIntent) -> str:
        """Format the final response combining LLM output and action results."""
        response = llm_response
        
        if action_result:
            response += f"\n\n{action_result}"
        
        # Add metadata about the action taken
        if intent.action_type != ActionType.CHAT and intent.action_type != ActionType.NONE:
            response += f"\n\n*Action performed: {intent.action_type.value}*"
        
        return response
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics."""
        cache_stats = self.context_manager.get_cache_stats()
        
        return {
            "actions_performed": self.actions_performed,
            "files_modified": self.files_modified,
            "context_builds": self.context_builds,
            "project_files_indexed": len(self.context_manager.files),
            "conversation_length": len(self.conversation.messages),
            "cache_performance": cache_stats,
            "last_action": self.conversation.last_action.action_type.value if self.conversation.last_action else None
        }
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation = ConversationContext()
        show_info("Conversation history cleared")
    
    async def refresh_project_context(self) -> None:
        """Refresh project context by rescanning the directory."""
        show_info("Refreshing project context...")
        self.conversation.project_context_built = False
        await self._analyze_project_structure()
        show_success("Project context refreshed")
