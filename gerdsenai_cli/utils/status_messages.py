"""
Sophisticated status messages for the GerdsenAI CLI.

This module provides elevated, scholarly vocabulary for displaying
the AI's internal processes, making operations feel more intelligent
and engaging.
"""

import random
from enum import Enum


class OperationType(Enum):
    """Types of operations the AI can perform."""
    
    THINKING = "thinking"
    READING = "reading"
    ANALYZING = "analyzing"
    WRITING = "writing"
    PLANNING = "planning"
    SEARCHING = "searching"
    PROCESSING = "processing"
    STREAMING = "streaming"
    CONTEXTUALIZING = "contextualizing"
    SYNTHESIZING = "synthesizing"
    EVALUATING = "evaluating"


# Sophisticated status messages organized by operation type
STATUS_MESSAGES = {
    OperationType.THINKING: [
        "Cogitating possibilities",
        "Ruminating on implications",
        "Deliberating optimal pathways",
        "Contemplating semantic nuances",
        "Pondering architectural ramifications",
        "Meditating on solution vectors",
        "Weighing algorithmic trade-offs",
        "Mulling over implementation strategies",
        "Considering epistemic foundations",
        "Reflecting on logical dependencies",
    ],
    
    OperationType.READING: [
        "Parsing lexical structures",
        "Digesting syntactic patterns",
        "Absorbing architectural topology",
        "Ingesting codebase semantics",
        "Assimilating project knowledge",
        "Decoding implementation details",
        "Scrutinizing structural coherence",
        "Examining compositional patterns",
        "Perusing functional relationships",
        "Surveying programmatic landscape",
    ],
    
    OperationType.ANALYZING: [
        "Deconstructing semantic topology",
        "Triangulating logical dependencies",
        "Mapping cognitive architecture",
        "Decomposing functional hierarchies",
        "Identifying emergent patterns",
        "Evaluating systemic coherence",
        "Investigating causal relationships",
        "Assessing structural integrity",
        "Examining paradigmatic frameworks",
        "Discerning underlying principles",
    ],
    
    OperationType.WRITING: [
        "Synthesizing linguistic constructs",
        "Composing programmatic discourse",
        "Architecting solution topology",
        "Formulating algorithmic expressions",
        "Orchestrating code choreography",
        "Crafting computational narratives",
        "Articulating technical specifications",
        "Manifesting abstract concepts",
        "Materializing logical structures",
        "Rendering implementational blueprints",
    ],
    
    OperationType.PLANNING: [
        "Strategizing execution vectors",
        "Blueprinting operational sequence",
        "Orchestrating task dependencies",
        "Choreographing workflow dynamics",
        "Designing procedural roadmaps",
        "Mapping strategic trajectories",
        "Structuring tactical frameworks",
        "Organizing methodological approach",
        "Sequencing operational phases",
        "Prioritizing implementation pipeline",
    ],
    
    OperationType.SEARCHING: [
        "Scouring semantic manifolds",
        "Traversing knowledge graphs",
        "Exploring conceptual territories",
        "Navigating symbolic landscapes",
        "Investigating lexical domains",
        "Prospecting pattern repositories",
        "Surveying implementation corpus",
        "Canvassing functional spaces",
        "Scanning architectural substrate",
        "Mining cognitive archives",
    ],
    
    OperationType.PROCESSING: [
        "Synthesizing contextual tributaries",
        "Integrating knowledge domains",
        "Consolidating semantic threads",
        "Amalgamating conceptual fragments",
        "Harmonizing logical constructs",
        "Reconciling paradigmatic tensions",
        "Coalescing analytical insights",
        "Unifying disparate elements",
        "Converging solution pathways",
        "Crystallizing understanding",
    ],
    
    OperationType.STREAMING: [
        "Channeling cognitive flow",
        "Transmitting thought vectors",
        "Broadcasting semantic stream",
        "Projecting ideational cascade",
        "Emitting linguistic artifacts",
        "Radiating conceptual momentum",
        "Propagating solution trajectory",
        "Conducting neural impulses",
        "Diffusing knowledge particles",
        "Cascading logical progression",
    ],
    
    OperationType.CONTEXTUALIZING: [
        "Situating within epistemic framework",
        "Establishing relational context",
        "Grounding in project semantics",
        "Anchoring to architectural schema",
        "Embedding in knowledge topology",
        "Positioning within cognitive map",
        "Orienting to functional landscape",
        "Calibrating to domain vocabulary",
        "Aligning with systemic patterns",
        "Attuning to codebase zeitgeist",
    ],
    
    OperationType.SYNTHESIZING: [
        "Fusing conceptual boundaries",
        "Melding logical paradigms",
        "Blending analytical perspectives",
        "Merging solution architectures",
        "Combining strategic approaches",
        "Uniting disparate insights",
        "Integrating knowledge streams",
        "Weaving semantic tapestry",
        "Composing holistic understanding",
        "Forging unified framework",
    ],
    
    OperationType.EVALUATING: [
        "Assessing solution viability",
        "Gauging implementation efficacy",
        "Measuring architectural soundness",
        "Validating logical consistency",
        "Verifying semantic coherence",
        "Testing conceptual boundaries",
        "Appraising methodological rigor",
        "Judging paradigmatic fitness",
        "Critiquing structural elegance",
        "Reviewing strategic alignment",
    ],
}


# Additional context phrases to append for extra sophistication
CONTEXT_SUFFIXES = [
    "with scholarly precision",
    "through analytical lens",
    "via methodical inquiry",
    "employing systematic rigor",
    "leveraging heuristic wisdom",
    "utilizing cognitive frameworks",
    "applying logical algorithms",
    "engaging deep reasoning",
    "invoking pattern recognition",
    "exercising semantic judgment",
]


def get_status_message(
    operation: OperationType,
    add_context: bool = True,
    add_ellipsis: bool = True,
) -> str:
    """
    Get a sophisticated status message for the given operation.
    
    Args:
        operation: The type of operation being performed
        add_context: Whether to append a context suffix
        add_ellipsis: Whether to add trailing ellipsis
        
    Returns:
        A sophisticated status message string
    """
    messages = STATUS_MESSAGES.get(operation, ["Processing"])
    base_message = random.choice(messages)
    
    # Occasionally add a context suffix for extra sophistication
    if add_context and random.random() < 0.3:  # 30% chance
        suffix = random.choice(CONTEXT_SUFFIXES)
        base_message = f"{base_message} {suffix}"
    
    if add_ellipsis:
        base_message += "..."
    
    return base_message


def get_completion_message(operation: OperationType) -> str:
    """
    Get a completion message for the given operation.
    
    Args:
        operation: The type of operation that completed
        
    Returns:
        A sophisticated completion message
    """
    completions = {
        OperationType.THINKING: "Cogitation complete",
        OperationType.READING: "Absorption complete",
        OperationType.ANALYZING: "Analysis synthesized",
        OperationType.WRITING: "Composition finalized",
        OperationType.PLANNING: "Strategy formulated",
        OperationType.SEARCHING: "Exploration concluded",
        OperationType.PROCESSING: "Integration achieved",
        OperationType.STREAMING: "Transmission complete",
        OperationType.CONTEXTUALIZING: "Context established",
        OperationType.SYNTHESIZING: "Synthesis manifested",
        OperationType.EVALUATING: "Evaluation rendered",
    }
    
    return completions.get(operation, "Operation complete")


# Special combined operations
COMBINED_OPERATIONS = {
    "reading_and_analyzing": [
        "Parsing & deconstructing semantic layers",
        "Absorbing & triangulating knowledge domains",
        "Digesting & mapping cognitive architecture",
        "Ingesting & evaluating structural patterns",
    ],
    "planning_and_executing": [
        "Strategizing & orchestrating execution flow",
        "Blueprinting & materializing solutions",
        "Designing & implementing frameworks",
        "Mapping & traversing operational pathways",
    ],
    "searching_and_synthesizing": [
        "Prospecting & integrating insights",
        "Exploring & coalescing discoveries",
        "Navigating & harmonizing findings",
        "Scanning & crystallizing patterns",
    ],
}


def get_combined_status(operation_pair: str, add_ellipsis: bool = True) -> str:
    """
    Get a status message for combined operations.
    
    Args:
        operation_pair: Combined operation key (e.g., "reading_and_analyzing")
        add_ellipsis: Whether to add trailing ellipsis
        
    Returns:
        A sophisticated combined status message
    """
    messages = COMBINED_OPERATIONS.get(operation_pair, ["Processing"])
    base_message = random.choice(messages)
    
    if add_ellipsis:
        base_message += "..."
    
    return base_message


# Progress indicators for long operations
PROGRESS_INDICATORS = [
    "Engaging deep contemplation",
    "Consulting internal knowledge base",
    "Cross-referencing architectural patterns",
    "Validating against best practices",
    "Optimizing solution vectors",
    "Refining conceptual model",
    "Calibrating response parameters",
    "Fine-tuning semantic precision",
]


def get_progress_indicator() -> str:
    """Get a random progress indicator for long-running operations."""
    return random.choice(PROGRESS_INDICATORS) + "..."
