"""
File Editor for GerdsenAI CLI.

This module handles safe file modifications with diff previews, user confirmation,
backup management, and rollback capabilities.
"""

import asyncio
import difflib
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.text import Text

from ..utils.display import show_error, show_info, show_success, show_warning

logger = logging.getLogger(__name__)
console = Console()


class EditOperation(Enum):
    """Types of edit operations."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class FileEdit:
    """Represents a single file edit operation."""
    operation: EditOperation
    target_path: Path
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    backup_path: Optional[Path] = None
    timestamp: datetime = field(default_factory=datetime.now)
    applied: bool = False
    
    def __post_init__(self):
        """Initialize computed properties."""
        if self.operation == EditOperation.CREATE and self.original_content is None:
            self.original_content = ""


@dataclass
class EditSession:
    """Represents a session of related file edits."""
    session_id: str
    edits: List[FileEdit] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    applied_edits: int = 0
    failed_edits: int = 0
    
    def add_edit(self, edit: FileEdit) -> None:
        """Add an edit to this session."""
        self.edits.append(edit)
    
    def get_pending_edits(self) -> List[FileEdit]:
        """Get edits that haven't been applied yet."""
        return [edit for edit in self.edits if not edit.applied]
    
    def get_applied_edits(self) -> List[FileEdit]:
        """Get edits that have been applied."""
        return [edit for edit in self.edits if edit.applied]


class DiffGenerator:
    """Generates and formats diffs for file changes."""
    
    @staticmethod
    def generate_unified_diff(
        original: str, 
        modified: str, 
        filename: str = "file",
        original_timestamp: Optional[datetime] = None,
        modified_timestamp: Optional[datetime] = None
    ) -> str:
        """Generate unified diff between two text contents."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        original_label = f"{filename} (original)"
        modified_label = f"{filename} (modified)"
        
        if original_timestamp:
            original_label += f" {original_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        if modified_timestamp:
            modified_label += f" {modified_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        diff_lines = list(difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=original_label,
            tofile=modified_label,
            lineterm=''
        ))
        
        return ''.join(diff_lines)
    
    @staticmethod
    def generate_side_by_side_diff(
        original: str, 
        modified: str,
        width: int = 80
    ) -> str:
        """Generate side-by-side diff representation."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        # Use difflib.SequenceMatcher for more detailed comparison
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
        
        result_lines = []
        col_width = width // 2 - 2
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for i, line in enumerate(original_lines[i1:i2]):
                    left = line[:col_width].ljust(col_width)
                    right = modified_lines[j1 + i][:col_width].ljust(col_width)
                    result_lines.append(f"  {left} | {right}")
            
            elif tag == 'delete':
                for line in original_lines[i1:i2]:
                    left = line[:col_width].ljust(col_width)
                    right = "".ljust(col_width)
                    result_lines.append(f"- {left} | {right}")
            
            elif tag == 'insert':
                for line in modified_lines[j1:j2]:
                    left = "".ljust(col_width)
                    right = line[:col_width].ljust(col_width)
                    result_lines.append(f"+ {left} | {right}")
            
            elif tag == 'replace':
                max_lines = max(i2 - i1, j2 - j1)
                for i in range(max_lines):
                    left_line = original_lines[i1 + i] if i < (i2 - i1) else ""
                    right_line = modified_lines[j1 + i] if i < (j2 - j1) else ""
                    
                    left = left_line[:col_width].ljust(col_width)
                    right = right_line[:col_width].ljust(col_width)
                    
                    if i < (i2 - i1) and i < (j2 - j1):
                        result_lines.append(f"~ {left} | {right}")
                    elif i < (i2 - i1):
                        result_lines.append(f"- {left} | {right}")
                    else:
                        result_lines.append(f"+ {left} | {right}")
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def format_diff_for_display(
        diff_text: str,
        syntax_theme: str = "monokai",
        show_line_numbers: bool = True
    ) -> Syntax:
        """Format diff text for rich display."""
        return Syntax(
            diff_text,
            "diff",
            theme=syntax_theme,
            line_numbers=show_line_numbers,
            word_wrap=True
        )


class BackupManager:
    """Manages file backups and restoration."""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """Initialize backup manager with optional custom backup directory."""
        if backup_dir:
            self.backup_dir = backup_dir
        else:
            # Use system temp directory with application-specific subdirectory
            self.backup_dir = Path(tempfile.gettempdir()) / "gerdsenai_cli_backups"
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean old backups on init
        self._cleanup_old_backups()
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of the specified file."""
        try:
            if not file_path.exists():
                return None
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_name = f"{file_path.name}_{timestamp}.backup"
            backup_path = self.backup_dir / backup_name
            
            # Copy file to backup location
            shutil.copy2(file_path, backup_path)
            
            logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            show_error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore a file from backup."""
        try:
            if not backup_path.exists():
                show_error(f"Backup file not found: {backup_path}")
                return False
            
            # Create target directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy backup to target location
            shutil.copy2(backup_path, target_path)
            
            logger.info(f"Restored file from backup: {backup_path} -> {target_path}")
            show_success(f"File restored from backup: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_path}: {e}")
            show_error(f"Failed to restore backup: {e}")
            return False
    
    def _cleanup_old_backups(self, max_age_days: int = 7, max_count: int = 100) -> None:
        """Clean up old backup files."""
        try:
            if not self.backup_dir.exists():
                return
            
            backup_files = list(self.backup_dir.glob("*.backup"))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            current_time = datetime.now().timestamp()
            removed_count = 0
            
            for i, backup_file in enumerate(backup_files):
                file_age_days = (current_time - backup_file.stat().st_mtime) / (24 * 3600)
                
                # Remove if too old or beyond count limit
                if file_age_days > max_age_days or i >= max_count:
                    try:
                        backup_file.unlink()
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove old backup {backup_file}: {e}")
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old backup files")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def list_backups(self, file_pattern: Optional[str] = None) -> List[Tuple[Path, datetime]]:
        """List available backups, optionally filtered by file pattern."""
        try:
            if not self.backup_dir.exists():
                return []
            
            pattern = f"*{file_pattern}*.backup" if file_pattern else "*.backup"
            backup_files = list(self.backup_dir.glob(pattern))
            
            # Return list of (path, modification_time) tuples
            backups = []
            for backup_file in backup_files:
                mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append((backup_file, mod_time))
            
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []


class FileEditor:
    """Main file editor with safety features and user interaction."""
    
    def __init__(self, backup_manager: Optional[BackupManager] = None):
        """Initialize file editor with optional backup manager."""
        self.backup_manager = backup_manager or BackupManager()
        self.current_session: Optional[EditSession] = None
        self.sessions: Dict[str, EditSession] = {}
        self.auto_backup = True
        self.require_confirmation = True
        self.max_diff_lines = 100
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new edit session."""
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = EditSession(session_id=session_id)
        self.sessions[session_id] = session
        self.current_session = session
        
        logger.info(f"Started edit session: {session_id}")
        show_info(f"Started edit session: {session_id}")
        
        return session_id
    
    def end_session(self) -> None:
        """End the current edit session."""
        if self.current_session:
            session_id = self.current_session.session_id
            self.current_session = None
            logger.info(f"Ended edit session: {session_id}")
            show_info(f"Ended edit session: {session_id}")
    
    async def propose_edit(
        self,
        file_path: Union[str, Path],
        new_content: str,
        operation: EditOperation = EditOperation.MODIFY
    ) -> Optional[FileEdit]:
        """Propose a file edit for user review."""
        file_path = Path(file_path)
        
        try:
            # Read current content if file exists
            original_content = ""
            if file_path.exists() and operation != EditOperation.CREATE:
                try:
                    original_content = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    # Try with different encodings
                    for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
                        try:
                            original_content = file_path.read_text(encoding=encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        show_error(f"Cannot read file {file_path} - unsupported encoding")
                        return None
            
            # Create edit object
            edit = FileEdit(
                operation=operation,
                target_path=file_path,
                original_content=original_content,
                new_content=new_content
            )
            
            # Add to current session
            if not self.current_session:
                self.start_session()
            
            self.current_session.add_edit(edit)
            
            return edit
            
        except Exception as e:
            logger.error(f"Failed to propose edit for {file_path}: {e}")
            show_error(f"Failed to propose edit: {e}")
            return None
    
    async def preview_edit(self, edit: FileEdit, show_full_diff: bool = False) -> None:
        """Preview a file edit with diff display."""
        try:
            console.print()
            
            # Create header panel
            header_text = f"📝 File Edit Preview: {edit.operation.value.title()}"
            if edit.operation == EditOperation.CREATE:
                header_text += f" - {edit.target_path}"
            else:
                header_text += f" - {edit.target_path}"
            
            console.print(Panel(header_text, style="bold cyan"))
            
            if edit.operation == EditOperation.CREATE:
                # Show new file content
                console.print("\n📄 [bold green]New file content:[/bold green]")
                
                # Syntax highlight based on file extension
                file_ext = edit.target_path.suffix.lower()
                language = self._get_language_from_extension(file_ext)
                
                syntax = Syntax(
                    edit.new_content,
                    language,
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True
                )
                console.print(syntax)
                
            elif edit.operation == EditOperation.DELETE:
                console.print(f"\n🗑️  [bold red]File will be deleted:[/bold red] {edit.target_path}")
                
            elif edit.operation == EditOperation.MODIFY:
                # Show diff
                if edit.original_content == edit.new_content:
                    console.print("\n ℹ️  [yellow]No changes detected[/yellow]")
                    return
                
                console.print("\n🔍 [bold yellow]Changes:[/bold yellow]")
                
                # Generate diff
                diff_text = DiffGenerator.generate_unified_diff(
                    edit.original_content or "",
                    edit.new_content or "",
                    str(edit.target_path),
                    original_timestamp=edit.timestamp,
                    modified_timestamp=datetime.now()
                )
                
                # Limit diff size for display
                diff_lines = diff_text.split('\n')
                if not show_full_diff and len(diff_lines) > self.max_diff_lines:
                    truncated_diff = '\n'.join(diff_lines[:self.max_diff_lines])
                    truncated_diff += f"\n... (showing first {self.max_diff_lines} lines, {len(diff_lines) - self.max_diff_lines} more lines truncated)"
                    diff_text = truncated_diff
                
                # Display formatted diff
                if diff_text.strip():
                    diff_syntax = DiffGenerator.format_diff_for_display(diff_text)
                    console.print(diff_syntax)
                else:
                    console.print("  [dim]No differences to display[/dim]")
            
            console.print()
            
        except Exception as e:
            logger.error(f"Failed to preview edit: {e}")
            show_error(f"Failed to preview edit: {e}")
    
    async def apply_edit(self, edit: FileEdit, force: bool = False) -> bool:
        """Apply a file edit after confirmation."""
        try:
            # Skip if already applied
            if edit.applied:
                show_warning(f"Edit already applied: {edit.target_path}")
                return True
            
            # Show preview if confirmation required
            if self.require_confirmation and not force:
                await self.preview_edit(edit)
                
                if not Confirm.ask(f"Apply this edit to {edit.target_path}?"):
                    show_info("Edit cancelled by user")
                    return False
            
            # Create backup if file exists and auto_backup is enabled
            if self.auto_backup and edit.target_path.exists():
                backup_path = self.backup_manager.create_backup(edit.target_path)
                edit.backup_path = backup_path
                
                if backup_path:
                    show_info(f"Backup created: {backup_path.name}")
            
            # Apply the edit based on operation type
            success = await self._execute_edit(edit)
            
            if success:
                edit.applied = True
                if self.current_session:
                    self.current_session.applied_edits += 1
                
                show_success(f"Applied edit: {edit.operation.value} {edit.target_path}")
                return True
            else:
                if self.current_session:
                    self.current_session.failed_edits += 1
                return False
                
        except Exception as e:
            logger.error(f"Failed to apply edit: {e}")
            show_error(f"Failed to apply edit: {e}")
            if self.current_session:
                self.current_session.failed_edits += 1
            return False
    
    async def _execute_edit(self, edit: FileEdit) -> bool:
        """Execute the actual file operation."""
        try:
            if edit.operation == EditOperation.CREATE or edit.operation == EditOperation.MODIFY:
                # Ensure parent directory exists
                edit.target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write new content
                edit.target_path.write_text(edit.new_content, encoding='utf-8')
                return True
                
            elif edit.operation == EditOperation.DELETE:
                if edit.target_path.exists():
                    edit.target_path.unlink()
                return True
                
            elif edit.operation == EditOperation.RENAME:
                # For rename operations, new_content should contain the new path
                if edit.new_content:
                    new_path = Path(edit.new_content)
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    edit.target_path.rename(new_path)
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to execute edit operation: {e}")
            show_error(f"Failed to execute edit: {e}")
            return False
    
    async def rollback_edit(self, edit: FileEdit) -> bool:
        """Rollback a previously applied edit."""
        try:
            if not edit.applied:
                show_warning("Edit was not applied, cannot rollback")
                return False
            
            if edit.operation == EditOperation.CREATE:
                # Remove created file
                if edit.target_path.exists():
                    edit.target_path.unlink()
                    show_success(f"Removed created file: {edit.target_path}")
                    
            elif edit.operation == EditOperation.DELETE:
                # Restore from backup
                if edit.backup_path and edit.backup_path.exists():
                    success = self.backup_manager.restore_backup(edit.backup_path, edit.target_path)
                    if success:
                        show_success(f"Restored deleted file: {edit.target_path}")
                        return True
                    
            elif edit.operation == EditOperation.MODIFY:
                # Restore from backup or original content
                if edit.backup_path and edit.backup_path.exists():
                    success = self.backup_manager.restore_backup(edit.backup_path, edit.target_path)
                    if success:
                        show_success(f"Restored modified file: {edit.target_path}")
                        return True
                elif edit.original_content is not None:
                    edit.target_path.write_text(edit.original_content, encoding='utf-8')
                    show_success(f"Restored original content: {edit.target_path}")
                    return True
            
            edit.applied = False
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback edit: {e}")
            show_error(f"Failed to rollback edit: {e}")
            return False
    
    def _get_language_from_extension(self, file_ext: str) -> str:
        """Get syntax highlighting language from file extension."""
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'zsh',
            '.ps1': 'powershell',
            '.dockerfile': 'dockerfile',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'ini',
        }
        
        return language_map.get(file_ext.lower(), 'text')
    
    async def apply_session_edits(self, session_id: Optional[str] = None, force: bool = False) -> Tuple[int, int]:
        """Apply all pending edits in a session."""
        session = self.sessions.get(session_id) if session_id else self.current_session
        
        if not session:
            show_error("No session found to apply edits")
            return 0, 0
        
        pending_edits = session.get_pending_edits()
        
        if not pending_edits:
            show_info("No pending edits to apply")
            return 0, 0
        
        show_info(f"Applying {len(pending_edits)} pending edits...")
        
        applied_count = 0
        failed_count = 0
        
        for edit in pending_edits:
            success = await self.apply_edit(edit, force=force)
            if success:
                applied_count += 1
            else:
                failed_count += 1
        
        show_info(f"Edit session complete: {applied_count} applied, {failed_count} failed")
        return applied_count, failed_count
    
    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of edit session."""
        session = self.sessions.get(session_id) if session_id else self.current_session
        
        if not session:
            return {}
        
        return {
            "session_id": session.session_id,
            "total_edits": len(session.edits),
            "applied_edits": session.applied_edits,
            "failed_edits": session.failed_edits,
            "pending_edits": len(session.get_pending_edits()),
            "created_at": session.created_at,
            "edit_operations": {
                op.value: len([e for e in session.edits if e.operation == op])
                for op in EditOperation
            }
        }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all edit sessions."""
        return [self.get_session_summary(session_id) for session_id in self.sessions.keys()]
