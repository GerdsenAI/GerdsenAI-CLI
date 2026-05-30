# Phase 9: World-Class Error Handling, NLP, MCP & Universal LLM Support

**Date:** November 17, 2025
**Status:** Planning → Implementation
**Goal:** Make GerdsenAI CLI the most robust, intelligent, and compatible local LLM CLI

---

## 🎯 Objectives

1. **World-Class Error Handling**
   - Graceful degradation on failures
   - Smart retry logic with exponential backoff
   - Context-preserving error recovery
   - User-friendly error messages
   - Detailed logging for debugging

2. **Advanced NLP Capabilities**
   - Multi-model intent detection (fallback chains)
   - Entity extraction (files, functions, classes)
   - Sentiment analysis for user frustration
   - Contextual understanding across turns
   - Ambiguity resolution

3. **MCP Integration**
   - Full Model Context Protocol support
   - Server discovery and management
   - Tool integration via MCP
   - Resource sharing
   - Prompt templates

4. **Universal LLM Provider Support**
   - Ollama (current)
   - vLLM
   - LM Studio
   - Hugging Face (TGI, TEI)
   - LocalAI
   - llama.cpp server
   - text-generation-webui (oobabooga)
   - KoboldAI
   - Auto-detection and configuration

---

## 📋 Implementation Plan

### Part 1: Universal LLM Provider System

#### 1.1 Provider Abstraction Layer

**Create:** `gerdsenai_cli/core/providers/base.py`
```python
class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def detect(self, url: str) -> bool:
        """Detect if this provider is running at URL."""
        pass

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """List available models."""
        pass

    @abstractmethod
    async def chat_completion(self, messages, **kwargs) -> str:
        """Generate chat completion."""
        pass

    @abstractmethod
    async def stream_completion(self, messages, **kwargs) -> AsyncGenerator:
        """Stream chat completion."""
        pass

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider-specific capabilities."""
        pass
```

**Providers to Implement:**
- `OllamaProvider` - Ollama API
- `VLLMProvider` - vLLM OpenAI-compatible API
- `LMStudioProvider` - LM Studio API
- `HuggingFaceProvider` - HF Text Generation Inference
- `LocalAIProvider` - LocalAI
- `LlamaCppProvider` - llama.cpp server
- `TextGenWebUIProvider` - oobabooga
- `KoboldAIProvider` - KoboldAI

#### 1.2 Auto-Detection System

**Create:** `gerdsenai_cli/core/providers/detector.py`
```python
class ProviderDetector:
    """Automatically detect which LLM provider is running."""

    DETECTION_ORDER = [
        OllamaProvider,
        LMStudioProvider,
        VLLMProvider,
        HuggingFaceProvider,
        LocalAIProvider,
        LlamaCppProvider,
        TextGenWebUIProvider,
        KoboldAIProvider,
    ]

    async def detect_provider(self, url: str) -> LLMProvider | None:
        """Try each provider in order until one succeeds."""
        for provider_class in self.DETECTION_ORDER:
            provider = provider_class(url)
            if await provider.detect(url):
                return provider
        return None

    async def scan_common_ports(self) -> list[tuple[str, LLMProvider]]:
        """Scan common ports for LLM providers."""
        common_configs = [
            ("http://localhost:11434", "Ollama"),
            ("http://localhost:1234", "LM Studio"),
            ("http://localhost:8080", "vLLM / LocalAI"),
            ("http://localhost:5000", "text-gen-webui"),
            ("http://localhost:5001", "KoboldAI"),
        ]
        # Scan and detect
```

#### 1.3 Provider-Specific Adapters

Each provider needs specific handling:

**Ollama:**
- Native Ollama API format
- Model tags and versioning
- Pull/delete model support

**vLLM:**
- OpenAI-compatible API
- Multiple LoRA support
- Tensor parallelism awareness

**LM Studio:**
- OpenAI-compatible API
- Local model management
- GGUF format support

**Hugging Face TGI:**
- HF-specific parameters
- Token streaming format
- Grammar constraints

**LocalAI:**
- Multi-backend support
- Voice/image capabilities
- Custom backend detection

---

### Part 2: World-Class Error Handling

#### 2.1 Error Classification System

**Create:** `gerdsenai_cli/core/errors.py`
```python
class ErrorCategory(Enum):
    NETWORK = "network"           # Connection issues
    TIMEOUT = "timeout"           # Request timeout
    AUTH = "authentication"       # Authentication failure
    RATE_LIMIT = "rate_limit"     # Rate limiting
    MODEL_NOT_FOUND = "model_not_found"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_LENGTH = "context_length"  # Context too long
    PROVIDER_ERROR = "provider_error"
    UNKNOWN = "unknown"

class GerdsenAIError(Exception):
    """Base error with rich context."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        recoverable: bool = True,
        suggestion: str | None = None,
        context: dict | None = None
    ):
        self.message = message
        self.category = category
        self.recoverable = recoverable
        self.suggestion = suggestion
        self.context = context or {}
```

#### 2.2 Retry Logic with Exponential Backoff

**Create:** `gerdsenai_cli/core/retry.py`
```python
class RetryStrategy:
    """Intelligent retry with exponential backoff."""

    DEFAULT_RETRIES = {
        ErrorCategory.NETWORK: 3,
        ErrorCategory.TIMEOUT: 2,
        ErrorCategory.RATE_LIMIT: 5,
        ErrorCategory.CONTEXT_LENGTH: 0,  # Don't retry
        ErrorCategory.MODEL_NOT_FOUND: 0,
    }

    async def execute_with_retry(
        self,
        operation: Callable,
        category: ErrorCategory,
        max_retries: int | None = None,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0
    ) -> Any:
        """Execute operation with smart retry."""
        retries = max_retries or self.DEFAULT_RETRIES.get(category, 1)

        for attempt in range(retries + 1):
            try:
                return await operation()
            except Exception as e:
                if attempt == retries:
                    raise

                # Calculate backoff
                delay = initial_delay * (backoff_factor ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
                await asyncio.sleep(delay)
```

#### 2.3 Context-Preserving Error Recovery

**Enhance:** `gerdsenai_cli/core/agent.py`
```python
class Agent:
    async def process_user_input_stream(
        self,
        user_input: str,
        status_callback: Callable | None = None
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Stream with error recovery."""

        try:
            # Main processing
            async for chunk, full in self._stream_response(user_input):
                yield chunk, full

        except ContextLengthError as e:
            # Automatic context compression
            logger.warning("Context too long, compressing...")
            compressed_input = await self._compress_context(user_input)

            # Retry with compressed context
            async for chunk, full in self._stream_response(compressed_input):
                yield chunk, full

        except NetworkError as e:
            # Show user-friendly message
            yield f"\n⚠️  Connection lost. Retrying...\n", ""

            # Wait and retry
            await asyncio.sleep(2)
            async for chunk, full in self._stream_response(user_input):
                yield chunk, full

        except ProviderError as e:
            # Provider-specific recovery
            if e.can_fallback:
                yield f"\n⚠️  Provider error. Trying alternative...\n", ""
                # Try alternative provider or model
```

---

### Part 3: Advanced NLP Capabilities

#### 3.1 Multi-Model Intent Detection

**Enhance:** `gerdsenai_cli/core/smart_router.py`
```python
class EnhancedIntentParser:
    """Multi-strategy intent detection with fallbacks."""

    async def detect_intent(
        self,
        user_input: str,
        project_files: list[str]
    ) -> ActionIntent:
        """Detect intent with fallback chain."""

        # Strategy 1: LLM-based (best accuracy)
        try:
            intent = await self._llm_based_detection(user_input, project_files)
            if intent.confidence >= 0.85:
                return intent
        except Exception as e:
            logger.warning(f"LLM intent detection failed: {e}")

        # Strategy 2: Pattern matching (fast, reliable)
        intent = await self._pattern_based_detection(user_input, project_files)
        if intent.confidence >= 0.70:
            return intent

        # Strategy 3: Keyword-based (fallback)
        return await self._keyword_based_detection(user_input, project_files)
```

#### 3.2 Entity Extraction

**Create:** `gerdsenai_cli/core/nlp/entity_extractor.py`
```python
class EntityExtractor:
    """Extract structured entities from natural language."""

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract files, classes, functions, etc."""
        return {
            "files": self._extract_files(text),
            "classes": self._extract_classes(text),
            "functions": self._extract_functions(text),
            "variables": self._extract_variables(text),
            "imports": self._extract_imports(text),
        }

    def _extract_files(self, text: str) -> list[str]:
        """Extract file paths with confidence scores."""
        patterns = [
            r"[\w/.-]+\.(?:py|js|ts|java|cpp|h|md|txt|json|yaml|toml)",
            r"(?:file|module|script):\s*([\w/.-]+)",
            r"in\s+([\w/.-]+\.[\w]+)",
        ]
        # Return unique matches with context
```

#### 3.3 Contextual Understanding

**Create:** `gerdsenai_cli/core/nlp/context_analyzer.py`
```python
class ContextAnalyzer:
    """Understand conversation context across turns."""

    def __init__(self):
        self.conversation_memory = []
        self.topic_stack = []
        self.entity_references = {}

    def analyze_turn(
        self,
        user_input: str,
        ai_response: str
    ) -> ContextState:
        """Analyze conversation turn for context."""

        # Detect topic shifts
        current_topic = self._detect_topic(user_input)
        if current_topic != self.topic_stack[-1]:
            self.topic_stack.append(current_topic)

        # Resolve references ("it", "that", "the file")
        resolved_entities = self._resolve_references(user_input)

        # Track user intent patterns
        intent_pattern = self._detect_intent_pattern()

        return ContextState(
            topic=current_topic,
            entities=resolved_entities,
            intent_pattern=intent_pattern
        )
```

---

### Part 4: MCP Integration

#### 4.1 MCP Client Implementation

**Create:** `gerdsenai_cli/core/mcp/client.py`
```python
class MCPClient:
    """Model Context Protocol client."""

    async def discover_servers(self) -> list[MCPServer]:
        """Discover available MCP servers."""
        # Check config
        # Scan local network
        # Check well-known paths

    async def connect_server(self, server: MCPServer) -> MCPConnection:
        """Connect to MCP server."""
        # Establish connection
        # Negotiate capabilities
        # Initialize tools

    async def list_tools(self, connection: MCPConnection) -> list[MCPTool]:
        """List available tools from server."""
        pass

    async def call_tool(
        self,
        connection: MCPConnection,
        tool: MCPTool,
        parameters: dict
    ) -> MCPResult:
        """Call MCP tool with parameters."""
        pass
```

#### 4.2 MCP Tool Registry

**Create:** `gerdsenai_cli/core/mcp/registry.py`
```python
class MCPToolRegistry:
    """Registry of MCP tools from all connected servers."""

    def __init__(self):
        self.servers: dict[str, MCPConnection] = {}
        self.tools: dict[str, MCPTool] = {}

    async def register_server(self, server_url: str):
        """Register and connect to MCP server."""
        connection = await self.mcp_client.connect_server(server_url)
        tools = await self.mcp_client.list_tools(connection)

        for tool in tools:
            self.tools[tool.name] = tool

        self.servers[server_url] = connection

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict
    ) -> MCPResult:
        """Execute MCP tool by name."""
        tool = self.tools.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool {tool_name} not found")

        # Find server connection
        connection = self.servers[tool.server_url]

        # Execute tool
        return await self.mcp_client.call_tool(connection, tool, parameters)
```

#### 4.3 Agent Integration

**Enhance:** `gerdsenai_cli/core/agent.py`
```python
class Agent:
    def __init__(self, ...):
        # ... existing init ...
        self.mcp_registry = MCPToolRegistry()

    async def initialize(self):
        # ... existing initialization ...

        # Load MCP servers from config
        if self.settings.mcp_servers:
            for server_url in self.settings.mcp_servers:
                await self.mcp_registry.register_server(server_url)

    async def _check_for_tool_calls(self, llm_response: str) -> list[ToolCall]:
        """Check if LLM response contains tool calls."""
        # Parse response for tool call syntax
        # Example: [[TOOL:read_file(path="main.py")]]
        pass

    async def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> str:
        """Execute MCP tool calls."""
        results = []
        for call in tool_calls:
            result = await self.mcp_registry.execute_tool(
                call.tool_name,
                call.parameters
            )
            results.append(result)
        return self._format_tool_results(results)
```

---

## 🔧 Implementation Priority

### Week 1: Universal LLM Providers
- [x] Create provider abstraction layer
- [ ] Implement OllamaProvider (enhance existing)
- [ ] Implement VLLMProvider
- [ ] Implement LMStudioProvider
- [ ] Implement HuggingFaceProvider
- [ ] Add provider auto-detection
- [ ] Test with each provider

### Week 2: Error Handling
- [ ] Create error classification system
- [ ] Implement retry logic
- [ ] Add context-preserving recovery
- [ ] Enhanced user feedback
- [ ] Comprehensive logging

### Week 3: Advanced NLP
- [ ] Multi-strategy intent detection
- [ ] Entity extraction system
- [ ] Contextual understanding
- [ ] Ambiguity resolution
- [ ] Reference resolution

### Week 4: MCP Integration
- [ ] MCP client implementation
- [ ] Server discovery
- [ ] Tool registry
- [ ] Agent integration
- [ ] Example MCP servers

---

## 📊 Success Metrics

### Provider Support
- [ ] Support 8+ LLM providers
- [ ] Auto-detection accuracy >95%
- [ ] Fallback chain works reliably

### Error Handling
- [ ] Recovery rate >90% for transient errors
- [ ] User-friendly error messages 100%
- [ ] No unhandled exceptions in production

### NLP Quality
- [ ] Intent detection accuracy >95%
- [ ] Entity extraction precision >90%
- [ ] Context preservation >85%

### MCP Integration
- [ ] Connect to 3+ MCP servers
- [ ] Tool execution success rate >95%
- [ ] Tool discovery automatic

---

## 🚀 Next Actions

1. **Start with Provider System** (highest impact)
2. **Parallel: Error Handling** (critical for stability)
3. **Then: Advanced NLP** (improves UX)
4. **Finally: MCP** (extends capabilities)

Let me know which area to prioritize, or I'll start with the Universal LLM Provider system!
