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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator

from rich.console import Console

from ..config.settings import Settings
from ..utils.display import show_error, show_info, show_success, show_warning
from .context_manager import ProjectContext
from .file_editor import EditOperation, FileEditor
from .llm_client import ChatMessage, LLMClient
from .planner import TaskPlanner

logger = logging.getLogger(__name__)
console = Console()

# Intent detection system prompt for LLM-based natural language understanding
INTENT_DETECTION_PROMPT = """You are an intent classifier for a coding assistant CLI.

Analyze the user's query and determine their intent. Respond ONLY with valid JSON.

Available actions:
- read_and_explain: User wants to read/understand specific files
- whole_repo_analysis: User wants overview of entire project
- iterative_search: User wants to find code/patterns across files
- edit_files: User wants to modify existing files
- create_files: User wants to create new files
- chat: General conversation or questions

Project files (first 100):
{file_list}

User query: {user_query}

Respond with JSON only (no other text):
{{
  "action": "<action_type>",
  "files": ["<file_paths>"],
  "reasoning": "<brief explanation>",
  "scope": "<single_file|whole_repo|search|specific_files>",
  "confidence": <0.0-1.0>
}}"""


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
    parameters: dict[str, Any] = field(default_factory=dict)
    reasoning: str | None = None
    requires_confirmation: bool = False

    def __post_init__(self):
        """Initialize computed properties."""
        # File operations require confirmation by default
        if self.action_type in {
            ActionType.EDIT_FILE,
            ActionType.CREATE_FILE,
            ActionType.DELETE_FILE,
        }:
            self.requires_confirmation = True


@dataclass
class ConversationContext:
    """Maintains conversation state and context."""

    messages: list[ChatMessage] = field(default_factory=list)
    project_context_built: bool = False
    last_action: ActionIntent | None = None
    pending_edits: list[str] = field(default_factory=list)
    session_metadata: dict[str, Any] = field(default_factory=dict)


class IntentParser:
    """Parses LLM responses for action intents."""

    def __init__(self):
        """Initialize intent parser with patterns and keywords."""
        # Patterns for detecting different intent types
        self.file_patterns = {
            "edit": [
                r"(?:edit|modify|change|update|fix)\s+(?:the\s+)?file\s+([^\s\n]+)",
                r"(?:make\s+changes?\s+to|update)\s+([^\s\n]+)",
                r"(?:in\s+)?file\s+([^\s\n]+).*(?:change|edit|modify)",
            ],
            "create": [
                r"create\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+)?([^\s\n]+)",
                r"(?:make|add)\s+(?:a\s+)?(?:new\s+)?file\s+([^\s\n]+)",
                r"(?:write|generate)\s+(?:a\s+)?file\s+([^\s\n]+)",
            ],
            "read": [
                r"(?:read|show|display|examine)\s+(?:the\s+)?file\s+([^\s\n]+)",
                r"(?:what\'?s\s+in|contents?\s+of)\s+(?:the\s+)?file\s+([^\s\n]+)",
                r"(?:look\s+at|check)\s+(?:the\s+)?file\s+([^\s\n]+)",
            ],
            "delete": [
                r"(?:delete|remove)\s+(?:the\s+)?file\s+([^\s\n]+)",
                r"(?:get\s+rid\s+of|eliminate)\s+(?:the\s+)?file\s+([^\s\n]+)",
            ],
        }

        self.analysis_keywords = {
            "project_structure",
            "analyze",
            "overview",
            "summary",
            "architecture",
            "codebase",
            "project",
            "structure",
            "organization",
            "files",
        }

        self.search_keywords = {
            "find",
            "search",
            "locate",
            "look for",
            "grep",
            "where is",
        }

    async def detect_intent_with_llm(
        self,
        llm_client: LLMClient,
        user_query: str,
        project_files: list[str],
    ) -> ActionIntent:
        """Use LLM to detect user intent from natural language.
        
        Args:
            llm_client: LLM client for making inference calls
            user_query: The user's natural language query
            project_files: List of project file paths for context
            
        Returns:
            ActionIntent with detected action and parameters
        """
        try:
            # Prepare file list (limit to first 100 for token efficiency)
            file_list = "\n".join(project_files[:100])
            if len(project_files) > 100:
                file_list += f"\n... and {len(project_files) - 100} more files"
            
            # Build intent detection prompt
            prompt = INTENT_DETECTION_PROMPT.format(
                file_list=file_list,
                user_query=user_query
            )
            
            # Create messages for LLM
            messages = [
                ChatMessage(role="system", content=prompt),
                ChatMessage(role="user", content=user_query)
            ]
            
            # Call LLM with timeout (5 seconds max)
            try:
                response = await asyncio.wait_for(
                    llm_client.chat(
                        messages=messages,
                        temperature=0.3,  # Deterministic for intent detection
                        max_tokens=300,   # Keep response short
                    ),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("LLM intent detection timed out after 5 seconds")
                return ActionIntent(
                    action_type=ActionType.NONE,
                    confidence=0.0,
                    reasoning="Intent detection timeout"
                )
            
            if not response:
                return ActionIntent(
                    action_type=ActionType.NONE,
                    confidence=0.0,
                    reasoning="Empty LLM response"
                )
            
            # Parse JSON response
            intent_data = self._parse_intent_json(response)
            if not intent_data:
                return ActionIntent(
                    action_type=ActionType.NONE,
                    confidence=0.0,
                    reasoning="Failed to parse intent JSON"
                )
            
            # Map LLM action to ActionType
            action_map = {
                "read_and_explain": ActionType.READ_FILE,
                "whole_repo_analysis": ActionType.ANALYZE_PROJECT,
                "iterative_search": ActionType.SEARCH_FILES,
                "edit_files": ActionType.EDIT_FILE,
                "create_files": ActionType.CREATE_FILE,
                "chat": ActionType.CHAT,
            }
            
            action_type = action_map.get(
                intent_data.get("action", "chat"),
                ActionType.CHAT
            )
            
            # Extract file paths from detected files
            detected_files = intent_data.get("files", [])
            validated_files = self.extract_file_paths(
                " ".join(detected_files) if detected_files else user_query,
                project_files
            )
            
            # Build parameters
            parameters = {}
            if validated_files:
                parameters["file_path"] = validated_files[0]  # Use first file
                parameters["files"] = validated_files
            if intent_data.get("scope"):
                parameters["scope"] = intent_data["scope"]
            
            return ActionIntent(
                action_type=action_type,
                confidence=float(intent_data.get("confidence", 0.7)),
                parameters=parameters,
                reasoning=intent_data.get("reasoning", "LLM-based intent detection")
            )
            
        except Exception as e:
            logger.error(f"LLM intent detection failed: {e}")
            return ActionIntent(
                action_type=ActionType.NONE,
                confidence=0.0,
                reasoning=f"Error: {e}"
            )
    
    def _parse_intent_json(self, response: str) -> dict[str, Any] | None:
        """Parse JSON from LLM response.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try to extract JSON from response (may have markdown code blocks)
        json_patterns = [
            r"```json\s*\n?(.*?)\n?```",  # JSON in code block
            r"```\s*\n?(.*?)\n?```",      # Generic code block
            r"(\{.*\})",                   # Raw JSON object
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # Try parsing the entire response as JSON
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse intent JSON from response: {response[:100]}")
            return None
    
    def extract_file_paths(
        self,
        text: str,
        project_files: list[str]
    ) -> list[str]:
        """Extract and validate file paths from user input.
        
        Args:
            text: Text containing potential file paths
            project_files: List of known project file paths
            
        Returns:
            List of validated file paths that exist in the project
        """
        # Patterns for detecting file paths
        path_patterns = [
            r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']',  # Quoted paths with extensions
            r'`([^`]+\.[a-zA-Z0-9]+)`',             # Backtick paths
            r'\b([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)\b', # Bare paths with extensions
        ]
        
        detected_paths = set()
        
        # Extract paths using patterns
        for pattern in path_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up the path
                path = match.strip().strip("'\"` ")
                if path:
                    detected_paths.add(path)
        
        # Validate against known project files
        validated = []
        project_files_lower = [f.lower() for f in project_files]
        
        for path in detected_paths:
            path_lower = path.lower()
            
            # Exact match
            if path in project_files:
                validated.append(path)
                continue
            
            # Case-insensitive match
            if path_lower in project_files_lower:
                idx = project_files_lower.index(path_lower)
                validated.append(project_files[idx])
                continue
            
            # Partial match (filename in any directory)
            filename = Path(path).name
            for proj_file in project_files:
                if Path(proj_file).name == filename:
                    validated.append(proj_file)
                    break
        
        return validated

    def parse_intent(self, llm_response: str, user_query: str = "") -> ActionIntent:
        """Parse LLM response to determine action intent."""
        response_lower = llm_response.lower()
        query_lower = user_query.lower()

        # Try to detect file operations first
        file_intent = self._parse_file_intent(llm_response, user_query)
        if file_intent.action_type != ActionType.NONE:
            return file_intent

        # Check for project analysis intent
        if self._contains_keywords(
            response_lower + " " + query_lower, self.analysis_keywords
        ):
            return ActionIntent(
                action_type=ActionType.ANALYZE_PROJECT,
                confidence=0.8,
                reasoning="Request appears to be asking for project analysis",
            )

        # Check for search intent
        if self._contains_keywords(
            response_lower + " " + query_lower, self.search_keywords
        ):
            search_term = self._extract_search_term(user_query)
            return ActionIntent(
                action_type=ActionType.SEARCH_FILES,
                confidence=0.7,
                parameters={"query": search_term} if search_term else {},
                reasoning="Request appears to be searching for something",
            )

        # Check for code explanation intent
        if any(
            keyword in response_lower
            for keyword in ["explain", "how does", "what does", "understand"]
        ):
            return ActionIntent(
                action_type=ActionType.EXPLAIN_CODE,
                confidence=0.6,
                reasoning="Request appears to be asking for code explanation",
            )

        # Default to chat
        return ActionIntent(
            action_type=ActionType.CHAT,
            confidence=0.9,
            reasoning="Standard conversational response",
        )

    def _parse_file_intent(self, response: str, query: str) -> ActionIntent:
        """Parse for file-specific intents."""
        combined_text = response + " " + query

        # Try each file operation type
        for operation, patterns in self.file_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    file_path = match.group(1).strip("\"`'")

                    action_type_map = {
                        "edit": ActionType.EDIT_FILE,
                        "create": ActionType.CREATE_FILE,
                        "read": ActionType.READ_FILE,
                        "delete": ActionType.DELETE_FILE,
                    }

                    return ActionIntent(
                        action_type=action_type_map[operation],
                        confidence=0.9,
                        parameters={"file_path": file_path},
                        reasoning=f"Detected {operation} operation on file: {file_path}",
                    )

        return ActionIntent(action_type=ActionType.NONE, confidence=0.0)

    def _contains_keywords(self, text: str, keywords: set) -> bool:
        """Check if text contains any of the specified keywords."""
        return any(keyword in text for keyword in keywords)

    def _extract_search_term(self, query: str) -> str | None:
        """Extract search term from query."""
        # Simple extraction - look for quoted terms or after "for"
        quoted_match = re.search(r'["\']([^"\']+)["\']', query)
        if quoted_match:
            return quoted_match.group(1)

        for_match = re.search(r"(?:for|find)\s+([^\s\n]+)", query, re.IGNORECASE)
        if for_match:
            return for_match.group(1)

        return None
    
    def detect_complexity(self, user_input: str) -> str:
        """Detect if query is simple, medium, or complex.
        
        Args:
            user_input: User's query
            
        Returns:
            "simple", "medium", or "complex"
        """
        user_lower = user_input.lower()
        
        # Complex task indicators
        complex_keywords = [
            "refactor all", "update all", "add to all", "modify all",
            "migrate", "convert all", "restructure", "rewrite",
            "implement feature", "add system", "create module",
            "integrate", "build", "setup", "configure",
        ]
        
        # Medium complexity indicators
        medium_keywords = [
            "refactor", "update multiple", "create several",
            "modify and test", "implement and test", "add and test",
            "create new", "build a", "add feature",
        ]
        
        # Check for multiple file references
        file_count = len(re.findall(r'\b\w+\.\w+\b', user_input))
        if file_count > 3:
            return "complex"
        elif file_count > 1:
            return "medium"
        
        # Check for complexity keywords
        if any(keyword in user_lower for keyword in complex_keywords):
            return "complex"
        elif any(keyword in user_lower for keyword in medium_keywords):
            return "medium"
        
        # Check length as a simple heuristic
        if len(user_input.split()) > 30:
            return "complex"
        elif len(user_input.split()) > 15:
            return "medium"
        
        return "simple"


class Agent:
    """Main agent that orchestrates AI-driven actions."""

    def __init__(
        self,
        llm_client: LLMClient,
        settings: Settings,
        project_root: Path | None = None,
    ):
        """Initialize the agent with required components."""
        self.llm_client = llm_client
        self.settings = settings

        # Initialize core components
        self.context_manager = ProjectContext(project_root)
        self.file_editor = FileEditor()
        self.intent_parser = IntentParser()
        self.planner = TaskPlanner(llm_client, self)

        # Conversation state
        self.conversation = ConversationContext()
        
        # Planning state
        self.planning_mode = False

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

            # Try LLM-based intent detection first (Phase 8b feature)
            intent = None
            use_llm_intent = self.settings.get_preference("enable_llm_intent_detection", True)
            
            if use_llm_intent:
                try:
                    # Get project file list for context
                    project_files = []
                    if self.context_manager.files:
                        project_files = [
                            str(f.relative_path) for f in self.context_manager.files.values()
                        ]
                    
                    # Attempt LLM-based intent detection
                    intent = await self.intent_parser.detect_intent_with_llm(
                        llm_client=self.llm_client,
                        user_query=user_input,
                        project_files=project_files
                    )
                    
                    # If confidence is high, use LLM intent
                    if intent and intent.confidence >= 0.7:
                        logger.info(
                            f"LLM intent detection: {intent.action_type.value} "
                            f"(confidence: {intent.confidence:.2f})"
                        )
                        
                        # For READ_FILE intent, we can execute directly without full LLM response
                        if intent.action_type == ActionType.READ_FILE:
                            action_result = await self._execute_action(intent, user_input, "")
                            if action_result:
                                return action_result
                        
                        # For ANALYZE_PROJECT intent, execute directly
                        if intent.action_type == ActionType.ANALYZE_PROJECT:
                            action_result = await self._execute_action(intent, user_input, "")
                            if action_result:
                                return action_result
                        
                        # For SEARCH_FILES intent, execute directly
                        if intent.action_type == ActionType.SEARCH_FILES:
                            action_result = await self._execute_action(intent, user_input, "")
                            if action_result:
                                return action_result
                    else:
                        # Low confidence, fall back to regex
                        logger.info(
                            f"LLM intent confidence too low ({intent.confidence:.2f}), "
                            "falling back to regex"
                        )
                        intent = None
                
                except (TimeoutError, asyncio.TimeoutError) as e:
                    logger.warning(f"LLM intent detection timed out: {e}, falling back to regex")
                    intent = None
                except Exception as e:
                    logger.warning(f"LLM intent detection failed: {e}, falling back to regex")
                    intent = None

            # Build context for LLM if needed
            context_prompt = ""
            if not self.conversation.project_context_built:
                context_prompt = await self._build_project_context(user_input)
                self.conversation.project_context_built = True

            # Prepare messages for LLM
            llm_messages = self._prepare_llm_messages(user_input, context_prompt)

            # Decide whether to stream
            streaming_enabled = self.settings.get_preference("streaming", True)
            llm_response = ""

            if streaming_enabled:
                try:
                    console.print("[bold cyan]\nGerdsenAI:[/bold cyan]", end=" ")
                    async for chunk in self.llm_client.stream_chat(llm_messages):
                        if chunk:
                            llm_response += chunk
                            # Print chunk without newline for live feeling
                            console.print(chunk, end="", style="white")
                    console.print()  # Final newline
                except Exception as stream_err:
                    show_warning(
                        f"Streaming failed ({stream_err}); falling back to non-streaming mode."
                    )
                    streaming_enabled = False  # Fallback

            if not streaming_enabled:
                # Non-streaming path with status spinner
                with console.status("[bold green]Thinking...", spinner="dots"):
                    llm_response = await self.llm_client.chat(llm_messages) or ""

            if not llm_response.strip():
                return "I apologize, but I'm having trouble connecting to the AI model. Please try again."

            # Add assistant response to conversation (full aggregated text)
            assistant_message = ChatMessage(role="assistant", content=llm_response)
            self.conversation.messages.append(assistant_message)

            # Parse intent using regex if we don't have LLM intent
            if not intent or intent.action_type == ActionType.NONE:
                intent = self.intent_parser.parse_intent(llm_response, user_input)
            
            self.conversation.last_action = intent

            # Execute action if needed
            action_result = await self._execute_action(intent, user_input, llm_response)

            # Combine LLM response with action results
            final_response = self._format_final_response(
                llm_response, action_result, intent
            )

            self.actions_performed += 1
            return final_response

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return f"I encountered an error while processing your request: {e}"

    async def process_user_input_stream(
        self, user_input: str, status_callback=None
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Process user input and yield streaming response chunks.
        
        Args:
            user_input: User's input message
            status_callback: Optional callback(operation: str) for status updates
            
        Yields:
            Tuples of (chunk, accumulated_response)
        """
        try:
            # Add user message to conversation
            user_message = ChatMessage(role="user", content=user_input)
            self.conversation.messages.append(user_message)

            # Try LLM-based intent detection first
            intent = None
            use_llm_intent = self.settings.get_preference("enable_llm_intent_detection", True)
            
            if use_llm_intent:
                try:
                    # Notify: analyzing intent
                    if status_callback:
                        status_callback("analyzing")
                    
                    project_files = []
                    if self.context_manager.files:
                        project_files = [
                            str(f.relative_path) for f in self.context_manager.files.values()
                        ]
                    
                    intent = await self.intent_parser.detect_intent_with_llm(
                        llm_client=self.llm_client,
                        user_query=user_input,
                        project_files=project_files
                    )
                    
                    # For high-confidence file operations, execute directly
                    if intent and intent.confidence >= 0.7:
                        if intent.action_type in [ActionType.READ_FILE, ActionType.ANALYZE_PROJECT, ActionType.SEARCH_FILES]:
                            # Notify: executing action
                            if status_callback:
                                if intent.action_type == ActionType.READ_FILE:
                                    status_callback("reading")
                                elif intent.action_type == ActionType.SEARCH_FILES:
                                    status_callback("searching")
                                else:
                                    status_callback("processing")
                            
                            action_result = await self._execute_action(intent, user_input, "")
                            if action_result:
                                # Yield complete result as single chunk
                                yield (action_result, action_result)
                                return
                    else:
                        intent = None
                
                except (TimeoutError, asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"LLM intent detection failed: {e}, falling back to regex")
                    intent = None

            # Build context for LLM if needed
            context_prompt = ""
            if not self.conversation.project_context_built:
                # Notify: building context
                if status_callback:
                    status_callback("contextualizing")
                
                context_prompt = await self._build_project_context(user_input)
                self.conversation.project_context_built = True

            # Prepare messages for LLM
            if status_callback:
                status_callback("thinking")
            
            llm_messages = self._prepare_llm_messages(user_input, context_prompt)

            # Stream the response
            llm_response = ""
            async for chunk in self.llm_client.stream_chat(llm_messages):
                if chunk:
                    llm_response += chunk
                    yield (chunk, llm_response)

            if not llm_response.strip():
                error_msg = "I apologize, but I'm having trouble connecting to the AI model. Please try again."
                yield (error_msg, error_msg)
                return

            # Add assistant response to conversation
            assistant_message = ChatMessage(role="assistant", content=llm_response)
            self.conversation.messages.append(assistant_message)

            # Parse intent using regex if we don't have LLM intent
            if not intent or intent.action_type == ActionType.NONE:
                intent = self.intent_parser.parse_intent(llm_response, user_input)
            
            self.conversation.last_action = intent

            # Execute action if needed
            action_result = await self._execute_action(intent, user_input, llm_response)

            # If there's action result, send it as additional chunks
            if action_result:
                final_response = self._format_final_response(
                    llm_response, action_result, intent
                )
                # Send the additional action result
                additional = final_response[len(llm_response):]
                if additional:
                    yield (additional, final_response)

            self.actions_performed += 1

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            error_msg = f"I encountered an error while processing your request: {e}"
            yield (error_msg, error_msg)

    async def _analyze_project_structure(self) -> None:
        """Analyze the current project structure."""
        try:
            show_info("Analyzing project structure...")

            await self.context_manager.scan_directory(
                max_depth=10, include_hidden=False, respect_gitignore=True
            )

            stats = self.context_manager.get_project_stats()
            show_success(f"Project analysis complete: {stats.total_files} files found")

            self.context_builds += 1

        except Exception as e:
            logger.error(f"Failed to analyze project: {e}")
            show_warning(f"Could not analyze project structure: {e}")

    async def _build_project_context(self, user_query: str = "") -> str:
        """Build project context for LLM using Phase 8c dynamic context building."""
        try:
            if not self.context_manager.files:
                await self._analyze_project_structure()

            # Phase 8c: Get model context window and calculate token budget
            model_id = self.settings.get_preference("model", "")
            context_window = self.llm_client.get_model_context_window(model_id)
            
            # Get context window usage preference (default 80%)
            context_usage = self.settings.get_preference("context_window_usage", 0.8)
            
            # Calculate max tokens for context (reserve some for response)
            max_context_tokens = int(context_window * context_usage)
            
            # Get auto-read strategy from settings
            strategy = self.settings.get_preference("auto_read_strategy", "smart")
            
            # Track mentioned files from conversation for prioritization
            mentioned_files = self._extract_mentioned_files()
            
            # Track recent files (last 5 files accessed)
            recent_files = self._get_recent_files()
            
            # Use Phase 8c dynamic context building
            logger.info(
                f"Building dynamic context: model={model_id}, "
                f"context_window={context_window}, strategy={strategy}, "
                f"max_tokens={max_context_tokens}"
            )
            
            context = await self.context_manager.build_dynamic_context(
                query=user_query,
                max_tokens=max_context_tokens,
                strategy=strategy,
                mentioned_files=mentioned_files,
                recent_files=recent_files,
            )

            return context

        except Exception as e:
            logger.error(f"Failed to build dynamic context: {e}")
            # Fallback to old method if dynamic context fails
            try:
                return await self.context_manager.build_context_prompt(
                    query=user_query,
                    include_file_contents=True,
                    max_context_length=self.max_context_length,
                )
            except Exception as fallback_err:
                logger.error(f"Fallback context building also failed: {fallback_err}")
                return ""

    def _prepare_llm_messages(
        self, user_input: str, context_prompt: str = ""
    ) -> list[ChatMessage]:
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

    async def _execute_action(
        self, intent: ActionIntent, user_input: str, llm_response: str
    ) -> str | None:
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

        result = "\n## Project Analysis Results\n\n"
        result += "**Statistics:**\n"
        result += f"- Total files: {stats.total_files}\n"
        result += f"- Text files: {stats.text_files}\n"
        result += f"- Total size: {self._format_size(stats.total_size)}\n\n"

        if stats.languages:
            result += "**Languages/File Types:**\n"
            sorted_langs = sorted(
                stats.languages.items(), key=lambda x: x[1], reverse=True
            )
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
        edit = await self.file_editor.propose_edit(
            file_path, new_content, EditOperation.MODIFY
        )
        if not edit:
            return "Failed to propose file edit."

        # Apply the edit (will show preview and ask for confirmation)
        success = await self.file_editor.apply_edit(edit)

        if success:
            self.files_modified += 1
            return f"Successfully edited file: {file_path}"
        else:
            return f"Failed to edit file: {file_path}"

    async def _handle_file_creation(
        self, intent: ActionIntent, llm_response: str
    ) -> str:
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
        edit = await self.file_editor.propose_edit(
            file_path, new_content, EditOperation.CREATE
        )
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
        relevant_files = self.context_manager.get_relevant_files(
            query=query, max_files=10
        )

        if not relevant_files:
            return f"No files found matching query: {query}"

        result = f"\n## Search Results for '{query}':\n\n"
        for file_info in relevant_files:
            result += f"{file_info.relative_path}\n"

        return result

    async def _handle_code_explanation(
        self, intent: ActionIntent, user_input: str
    ) -> str:
        """Handle code explanation request."""
        # This is handled by the LLM response itself, just add context
        return "\n*Code explanation provided in the main response above.*"

    def _extract_code_from_response(self, response: str) -> str | None:
        """Extract code content from LLM response."""
        # Look for code blocks
        code_block_pattern = r"```(?:\w+)?\n?(.*?)\n?```"
        matches = re.findall(code_block_pattern, response, re.DOTALL)

        if matches:
            # Return the largest code block
            return max(matches, key=len).strip()

        # If no code blocks, look for lines that look like code
        lines = response.split("\n")
        code_lines = []
        in_code_section = False

        for line in lines:
            # Simple heuristics for code detection
            if (
                any(char in line for char in ["{", "}", "(", ")", "=", ";"])
                and len(line.strip()) > 0
            ):
                in_code_section = True
                code_lines.append(line)
            elif in_code_section and line.strip() == "":
                code_lines.append(line)
            elif in_code_section and not any(
                char in line for char in ["{", "}", "(", ")", "=", ";"]
            ):
                break  # End of code section

        if code_lines:
            return "\n".join(code_lines).strip()

        return None

    def _format_final_response(
        self, llm_response: str, action_result: str | None, intent: ActionIntent
    ) -> str:
        """Format the final response combining LLM output and action results."""
        response = llm_response

        if action_result:
            response += f"\n\n{action_result}"

        # Add metadata about the action taken
        if (
            intent.action_type != ActionType.CHAT
            and intent.action_type != ActionType.NONE
        ):
            response += f"\n\n*Action performed: {intent.action_type.value}*"

        return response

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        size: float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def get_agent_stats(self) -> dict[str, Any]:
        """Get agent performance statistics."""
        cache_stats = self.context_manager.get_cache_stats()

        return {
            "actions_performed": self.actions_performed,
            "files_modified": self.files_modified,
            "context_builds": self.context_builds,
            "project_files_indexed": len(self.context_manager.files),
            "conversation_length": len(self.conversation.messages),
            "cache_performance": cache_stats,
            "last_action": self.conversation.last_action.action_type.value
            if self.conversation.last_action
            else None,
        }

    def _extract_mentioned_files(self) -> list[Path]:
        """Extract file paths mentioned in recent conversation."""
        mentioned = []
        
        # Look at last 5 messages for file mentions
        recent_messages = self.conversation.messages[-5:]
        
        for message in recent_messages:
            # Extract file paths from message content
            file_pattern = r'\b([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)\b'
            matches = re.findall(file_pattern, message.content)
            
            for match in matches:
                file_path = Path(match)
                # Check if file exists in project
                if file_path in self.context_manager.files:
                    mentioned.append(file_path)
        
        return list(set(mentioned))  # Remove duplicates
    
    def _get_recent_files(self) -> list[Path]:
        """Get recently modified files from the project."""
        if not self.context_manager.files:
            return []
        
        # Sort files by modification time (most recent first)
        sorted_files = sorted(
            self.context_manager.files.values(),
            key=lambda f: f.modified_time,
            reverse=True
        )
        
        # Return top 5 most recently modified files
        return [f.path for f in sorted_files[:5]]

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
