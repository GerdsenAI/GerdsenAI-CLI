"""
Confirmation Dialog System for GerdsenAI CLI.

This module implements sophisticated confirmation dialogs for high-risk operations,
including operation previews, diff displays, and undo capability.
"""

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations requiring confirmation."""

    FILE_DELETE = "file_delete"
    FILE_EDIT = "file_edit"
    FILE_MOVE = "file_move"
    BATCH_EDIT = "batch_edit"
    DATABASE_DROP = "database_drop"
    DATA_DELETE = "data_delete"
    MAJOR_REFACTOR = "major_refactor"
    ARCHITECTURE_CHANGE = "architecture_change"
    DESTRUCTIVE_COMMAND = "destructive_command"


class ConfirmationResponse(Enum):
    """User's response to confirmation dialog."""

    APPROVED = "approved"
    DENIED = "denied"
    PREVIEW_ONLY = "preview_only"


@dataclass
class FileChange:
    """Represents a change to a file."""

    path: str
    operation: str  # "create", "modify", "delete", "move"
    old_content: str | None = None
    new_content: str | None = None
    new_path: str | None = None  # For move operations
    lines_added: int = 0
    lines_removed: int = 0
    estimated_impact: str = "low"  # "low", "medium", "high"


@dataclass
class OperationPreview:
    """Preview of an operation before execution."""

    operation_type: OperationType
    description: str
    risk_level: str  # From ComplexityAnalysis
    affected_files: list[FileChange]
    estimated_time: int  # minutes
    reversible: bool
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    requires_backup: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UndoSnapshot:
    """Snapshot for undo capability."""

    snapshot_id: str
    operation_type: OperationType
    description: str
    timestamp: str
    affected_files: list[dict[str, Any]]  # Serialized FileChange objects
    backup_path: str  # Path to backup directory
    expires_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ConfirmationEngine:
    """Manages confirmation dialogs and undo capability."""

    def __init__(self, data_dir: Path | None = None):
        """
        Initialize confirmation engine.

        Args:
            data_dir: Directory for storing undo snapshots (default: ~/.gerdsenai)
        """
        self.data_dir = data_dir or Path.home() / ".gerdsenai"
        self.undo_dir = self.data_dir / "undo"
        self.undo_dir.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.undo_retention_hours = 24
        self.max_undo_snapshots = 50
        self.always_confirm_patterns = [
            r"\bdelete\b.*\ball\b",
            r"\bremove\b.*\beverything\b",
            r"\bdrop\b.*\b(database|table)\b",
            r"\btruncate\b",
            r"\bpurge\b",
        ]

        # Load existing snapshots
        self.snapshots: list[UndoSnapshot] = []
        self._load_snapshots()
        self._cleanup_expired_snapshots()

    def should_confirm(
        self,
        operation_type: OperationType,
        complexity_analysis: Any | None = None,
        user_input: str | None = None,
    ) -> bool:
        """
        Determine if operation requires confirmation.

        Args:
            operation_type: Type of operation
            complexity_analysis: Optional ComplexityAnalysis result
            user_input: Optional user input text

        Returns:
            True if confirmation required
        """
        # Always confirm destructive operations
        destructive_types = [
            OperationType.FILE_DELETE,
            OperationType.DATABASE_DROP,
            OperationType.DATA_DELETE,
            OperationType.DESTRUCTIVE_COMMAND,
        ]

        if operation_type in destructive_types:
            return True

        # Check complexity analysis
        if complexity_analysis:
            if hasattr(complexity_analysis, "requires_confirmation"):
                if complexity_analysis.requires_confirmation:
                    return True

            if hasattr(complexity_analysis, "risk_level"):
                risk_level = complexity_analysis.risk_level
                # Import RiskLevel enum from complexity module
                from .complexity import RiskLevel

                if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    return True

        # Check user input for always-confirm patterns
        if user_input:
            import re

            for pattern in self.always_confirm_patterns:
                if re.search(pattern, user_input.lower()):
                    return True

        # Confirm major refactors and architecture changes
        if operation_type in [
            OperationType.MAJOR_REFACTOR,
            OperationType.ARCHITECTURE_CHANGE,
        ]:
            return True

        return False

    def create_preview(
        self,
        operation_type: OperationType,
        description: str,
        affected_files: list[FileChange],
        complexity_analysis: Any | None = None,
    ) -> OperationPreview:
        """
        Create operation preview.

        Args:
            operation_type: Type of operation
            description: Human-readable description
            affected_files: List of file changes
            complexity_analysis: Optional complexity analysis

        Returns:
            Operation preview
        """
        # Extract info from complexity analysis
        risk_level = "medium"
        estimated_time = 10
        reversible = True
        warnings = []
        recommendations = []

        if complexity_analysis:
            if hasattr(complexity_analysis, "risk_level"):
                risk_level = complexity_analysis.risk_level.value

            if hasattr(complexity_analysis, "resource_estimate"):
                estimated_time = (
                    complexity_analysis.resource_estimate.estimated_time_minutes
                )

            if hasattr(complexity_analysis, "factors"):
                reversible = complexity_analysis.factors.reversibility > 0.7

            if hasattr(complexity_analysis, "warnings"):
                warnings = complexity_analysis.warnings

            if hasattr(complexity_analysis, "recommendations"):
                recommendations = complexity_analysis.recommendations

        # Determine if backup needed
        requires_backup = (
            operation_type
            in [
                OperationType.FILE_DELETE,
                OperationType.FILE_EDIT,
                OperationType.BATCH_EDIT,
                OperationType.MAJOR_REFACTOR,
            ]
            or not reversible
        )

        return OperationPreview(
            operation_type=operation_type,
            description=description,
            risk_level=risk_level,
            affected_files=affected_files,
            estimated_time=estimated_time,
            reversible=reversible,
            warnings=warnings,
            recommendations=recommendations,
            requires_backup=requires_backup,
        )

    def create_file_change(
        self,
        path: str,
        operation: str,
        old_content: str | None = None,
        new_content: str | None = None,
    ) -> FileChange:
        """
        Create FileChange object with diff analysis.

        Args:
            path: File path
            operation: Operation type (create, modify, delete, move)
            old_content: Original content (for modify/delete)
            new_content: New content (for create/modify)

        Returns:
            FileChange object
        """
        lines_added = 0
        lines_removed = 0
        estimated_impact = "low"

        if operation == "modify" and old_content and new_content:
            old_lines = old_content.splitlines()
            new_lines = new_content.splitlines()

            # Simple diff calculation
            lines_added = len(new_lines) - len(old_lines)
            if lines_added < 0:
                lines_removed = abs(lines_added)
                lines_added = 0
            else:
                lines_removed = 0

            # Count actual changes (approximate)
            common_lines = min(len(old_lines), len(new_lines))
            changed_lines = sum(
                1 for i in range(common_lines) if old_lines[i] != new_lines[i]
            )

            # Estimate impact
            total_changes = lines_added + lines_removed + changed_lines
            if total_changes > 100:
                estimated_impact = "high"
            elif total_changes > 20:
                estimated_impact = "medium"
            else:
                estimated_impact = "low"

        elif operation == "delete":
            estimated_impact = "high"
            if old_content:
                lines_removed = len(old_content.splitlines())

        elif operation == "create":
            estimated_impact = "low"
            if new_content:
                lines_added = len(new_content.splitlines())

        return FileChange(
            path=path,
            operation=operation,
            old_content=old_content,
            new_content=new_content,
            lines_added=lines_added,
            lines_removed=lines_removed,
            estimated_impact=estimated_impact,
        )

    def create_snapshot(
        self, preview: OperationPreview, backup_files: bool = True
    ) -> UndoSnapshot:
        """
        Create undo snapshot before operation.

        Args:
            preview: Operation preview
            backup_files: Whether to backup affected files

        Returns:
            Undo snapshot
        """
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        timestamp = datetime.now().isoformat()
        expires_at = (
            datetime.now() + timedelta(hours=self.undo_retention_hours)
        ).isoformat()

        # Create backup directory
        backup_path = self.undo_dir / snapshot_id
        backup_path.mkdir(parents=True, exist_ok=True)

        # Backup files if requested
        if backup_files:
            for file_change in preview.affected_files:
                if file_change.old_content and Path(file_change.path).exists():
                    try:
                        # Create subdirectory structure in backup
                        rel_path = Path(file_change.path)
                        backup_file = backup_path / rel_path.name

                        # Copy file
                        shutil.copy2(file_change.path, backup_file)
                        logger.info(f"Backed up {file_change.path} to {backup_file}")

                    except Exception as e:
                        logger.error(f"Failed to backup {file_change.path}: {e}")

        # Serialize file changes
        serialized_files = [
            {
                "path": fc.path,
                "operation": fc.operation,
                "old_content": fc.old_content,
                "new_content": fc.new_content,
                "new_path": fc.new_path,
                "lines_added": fc.lines_added,
                "lines_removed": fc.lines_removed,
                "estimated_impact": fc.estimated_impact,
            }
            for fc in preview.affected_files
        ]

        snapshot = UndoSnapshot(
            snapshot_id=snapshot_id,
            operation_type=preview.operation_type,
            description=preview.description,
            timestamp=timestamp,
            affected_files=serialized_files,
            backup_path=str(backup_path),
            expires_at=expires_at,
            metadata={
                "risk_level": preview.risk_level,
                "estimated_time": preview.estimated_time,
                "reversible": preview.reversible,
            },
        )

        # Save snapshot
        self.snapshots.append(snapshot)
        self._save_snapshots()

        logger.info(f"Created undo snapshot: {snapshot_id}")
        return snapshot

    def undo_last_operation(self) -> tuple[bool, str]:
        """
        Undo the last operation.

        Returns:
            Tuple of (success, message)
        """
        if not self.snapshots:
            return False, "No operations to undo"

        # Get most recent snapshot
        snapshot = self.snapshots[-1]

        # Check if expired
        expires_at = datetime.fromisoformat(snapshot.expires_at)
        if datetime.now() > expires_at:
            return (
                False,
                f"Undo snapshot expired (retention: {self.undo_retention_hours}h)",
            )

        # Restore files from backup
        backup_path = Path(snapshot.backup_path)
        if not backup_path.exists():
            return False, f"Backup directory not found: {backup_path}"

        restored_files = []
        failed_files = []

        for file_data in snapshot.affected_files:
            file_path = Path(file_data["path"])
            backup_file = backup_path / file_path.name

            try:
                if file_data["operation"] == "delete":
                    # Restore deleted file
                    if backup_file.exists():
                        shutil.copy2(backup_file, file_path)
                        restored_files.append(str(file_path))

                elif file_data["operation"] in ["modify", "create"]:
                    # Restore previous version
                    if backup_file.exists():
                        shutil.copy2(backup_file, file_path)
                        restored_files.append(str(file_path))
                    elif file_data["operation"] == "create":
                        # Delete newly created file
                        if file_path.exists():
                            file_path.unlink()
                            restored_files.append(str(file_path))

            except Exception as e:
                failed_files.append(f"{file_path}: {e}")
                logger.error(f"Failed to restore {file_path}: {e}")

        # Remove snapshot
        self.snapshots.remove(snapshot)
        self._save_snapshots()

        # Build result message
        if failed_files:
            message = (
                f"Partially restored {len(restored_files)} file(s). "
                f"Failed: {', '.join(failed_files)}"
            )
            return len(restored_files) > 0, message
        else:
            message = f"Successfully restored {len(restored_files)} file(s) from snapshot {snapshot.snapshot_id}"
            return True, message

    def list_undo_snapshots(self) -> list[UndoSnapshot]:
        """
        List available undo snapshots.

        Returns:
            List of snapshots (most recent first)
        """
        self._cleanup_expired_snapshots()
        return sorted(self.snapshots, key=lambda s: s.timestamp, reverse=True)

    def clear_undo_history(self) -> tuple[int, int]:
        """
        Clear all undo snapshots.

        Returns:
            Tuple of (snapshots_cleared, bytes_freed)
        """
        count = len(self.snapshots)
        bytes_freed = 0

        # Calculate size of undo directory
        for snapshot in self.snapshots:
            backup_path = Path(snapshot.backup_path)
            if backup_path.exists():
                for file in backup_path.rglob("*"):
                    if file.is_file():
                        bytes_freed += file.stat().st_size

        # Remove all backups
        if self.undo_dir.exists():
            shutil.rmtree(self.undo_dir)
            self.undo_dir.mkdir(parents=True, exist_ok=True)

        # Clear snapshots
        self.snapshots = []
        self._save_snapshots()

        return count, bytes_freed

    def _load_snapshots(self) -> None:
        """Load snapshots from disk."""
        snapshots_file = self.data_dir / "undo_snapshots.json"

        if not snapshots_file.exists():
            return

        try:
            with open(snapshots_file) as f:
                data = json.load(f)

            self.snapshots = [
                UndoSnapshot(
                    snapshot_id=s["snapshot_id"],
                    operation_type=OperationType(s["operation_type"]),
                    description=s["description"],
                    timestamp=s["timestamp"],
                    affected_files=s["affected_files"],
                    backup_path=s["backup_path"],
                    expires_at=s["expires_at"],
                    metadata=s.get("metadata", {}),
                )
                for s in data
            ]

            logger.info(f"Loaded {len(self.snapshots)} undo snapshot(s)")

        except Exception as e:
            logger.error(f"Failed to load undo snapshots: {e}")
            self.snapshots = []

    def _save_snapshots(self) -> None:
        """Save snapshots to disk."""
        snapshots_file = self.data_dir / "undo_snapshots.json"

        try:
            data = [
                {
                    "snapshot_id": s.snapshot_id,
                    "operation_type": s.operation_type.value,
                    "description": s.description,
                    "timestamp": s.timestamp,
                    "affected_files": s.affected_files,
                    "backup_path": s.backup_path,
                    "expires_at": s.expires_at,
                    "metadata": s.metadata,
                }
                for s in self.snapshots
            ]

            with open(snapshots_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self.snapshots)} undo snapshot(s)")

        except Exception as e:
            logger.error(f"Failed to save undo snapshots: {e}")

    def _cleanup_expired_snapshots(self) -> None:
        """Remove expired snapshots."""
        now = datetime.now()
        expired = []

        for snapshot in self.snapshots:
            expires_at = datetime.fromisoformat(snapshot.expires_at)
            if now > expires_at:
                expired.append(snapshot)

        if expired:
            for snapshot in expired:
                # Remove backup directory
                backup_path = Path(snapshot.backup_path)
                if backup_path.exists():
                    shutil.rmtree(backup_path)

                # Remove from list
                self.snapshots.remove(snapshot)

            self._save_snapshots()
            logger.info(f"Cleaned up {len(expired)} expired snapshot(s)")

        # Enforce max snapshots limit
        if len(self.snapshots) > self.max_undo_snapshots:
            # Remove oldest snapshots
            sorted_snapshots = sorted(self.snapshots, key=lambda s: s.timestamp)
            to_remove = sorted_snapshots[: -self.max_undo_snapshots]

            for snapshot in to_remove:
                # Remove backup directory
                backup_path = Path(snapshot.backup_path)
                if backup_path.exists():
                    shutil.rmtree(backup_path)

                # Remove from list
                self.snapshots.remove(snapshot)

            self._save_snapshots()
            logger.info(
                f"Removed {len(to_remove)} old snapshot(s) to maintain limit of {self.max_undo_snapshots}"
            )
