# Changelog

All notable changes to GerdsenAI CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Phase 8d: Advanced Intelligence Systems (Complete)

#### Phase 8d-7: Proactive Suggestions System (2025-11-18)
- Added `/suggest` command for context-aware code improvement recommendations
- Implemented 13 suggestion types: refactoring, testing, documentation, security, performance, planning, clarification, confirmation, and more
- Added 4 priority levels with color-coded UI: CRITICAL (red), HIGH (yellow), MEDIUM (cyan), LOW (white)
- Implemented pattern-based code analysis detecting:
  - Missing tests and documentation
  - Security vulnerabilities (eval/exec, hardcoded credentials, shell=True)
  - Error handling gaps
  - Performance optimization opportunities
- Integrated with Complexity Detector for task-specific suggestions
- Added non-intrusive UI with compact table view and detailed panel displays
- Created `ProactiveSuggestor` class with intelligence system integration
- Added 28 comprehensive tests with 89% coverage
- Commands: `/suggest file <path>`, `/suggest project`, `/suggest task <description>`

#### Phase 8d-6: Confirmation Dialogs & Undo System (2025-11-17)
- Added `/undo` command for reverting recent operations
- Implemented automatic snapshot creation before risky operations
- Integrated with Complexity Detector to determine confirmation requirements
- Added file system backup and restoration capabilities
- Created confirmation dialogs for high-risk operations (deletions, overwrites, bulk changes)
- Added snapshot management: list, clear, and restore operations
- Implemented 24 comprehensive tests with 92% coverage
- Commands: `/undo`, `/undo list`, `/undo clear`

#### Phase 8d-5: Complexity Detection System (2025-11-16)
- Added `/complexity` command for task analysis
- Implemented multi-dimensional complexity scoring:
  - Temporal complexity (time estimates)
  - Structural complexity (file/dependency counts)
  - Risk assessment (impact analysis)
  - Resource estimation (steps, files, commands)
- Added 4 complexity levels: trivial, low, medium, high
- Created `ComplexityDetector` class with pattern-based task analysis
- Integrated with planning and confirmation systems
- Added 49 comprehensive tests with 97% coverage
- Commands: `/complexity <task>`, `/complexity stats`, `/complexity threshold <value>`

#### Phase 8d-4: Clarifying Questions Engine (2025-11-15)
- Added `/clarify` command for ambiguity detection
- Implemented automatic clarifying question generation
- Added interpretation tracking and uncertainty analysis
- Created pattern-based ambiguity detection for technical terms
- Added learning from user clarifications
- Integrated with agent conversation flow
- Added 20 comprehensive tests
- Commands: `/clarify stats`, `/clarify threshold <value>`, `/clarify reset`

#### Phase 8d-1: Status Bar Messages (2025-11-14)
- Enhanced status messages with contextual information
- Added operation type indicators
- Improved user feedback during long-running operations

### Fixed

#### Critical Fixes (2025-11-18)
- Fixed syntax error in `test_clarification.py` (import statement)
- Added missing LICENSE file (MIT License)
- Fixed `show_suggestion_details()` priority display bug in console.py
- Updated `SuggestCommand` and `UndoCommand` to comply with `BaseCommand` interface

### Changed

#### Documentation Updates (2025-11-18)
- Updated README.md with Phase 8d Advanced Intelligence Systems section
- Updated TODO.md to mark Phase 8d as COMPLETE (100% feature parity)
- Created comprehensive documentation for all Phase 8d subsystems:
  - PHASE_8D4_CLARIFYING_QUESTIONS.md
  - PHASE_8D5_COMPLEXITY_DETECTION.md
  - PHASE_8D6_CONFIRMATION_DIALOGS.md
  - PHASE_8D7_PROACTIVE_SUGGESTIONS.md

#### Architecture Improvements
- Enhanced `ProactiveSuggestor` with backwards compatibility for string/enum types
- Integrated all Phase 8d intelligence systems with agent core
- Added comprehensive error handling across all intelligence components
- Improved UI consistency with Rich library integration

### Infrastructure

#### Testing (2025-11-18)
- Added 121+ new tests across Phase 8d systems
- Achieved 89-97% coverage for individual intelligence modules
- Fixed test infrastructure issues
- All Phase 8d tests passing

#### Build & Dependencies
- Maintained compatibility with Python 3.11+
- All dependencies up to date in pyproject.toml
- Build system: hatchling
- Development tools configured: pytest, mypy, ruff, black

---

## [0.1.0] - 2024-XX-XX

### Initial Release
- Core agent functionality
- Local LLM integration
- File operations (read, write, edit, search)
- Context management
- Plugin system foundation
- Rich terminal UI with syntax highlighting
- Session persistence
- Multiple model support

### Commands
- File operations: `/read`, `/edit`, `/create`, `/search`, `/files`
- Agent control: `/chat`, `/reset`, `/refresh`, `/status`
- Model management: `/model`, `/model-info`, `/model-stats`
- System: `/help`, `/exit`, `/config`, `/debug`, `/about`

---

[Unreleased]: https://github.com/GerdsenAI/GerdsenAI-CLI/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/GerdsenAI/GerdsenAI-CLI/releases/tag/v0.1.0
