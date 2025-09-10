"""
Helper utility functions for GerdsenAI CLI.

This module contains general utility functions used throughout the application.
"""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path object pointing to the project root
    """
    # Start from the current file and work up to find the project root
    current_file = Path(__file__)
    
    # Go up from gerdsenai_cli/utils/helpers.py to the project root
    project_root = current_file.parent.parent.parent
    
    return project_root


def validate_url(url: str) -> bool:
    """
    Validate if a string is a proper URL.
    
    Args:
        url: The URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url.strip())
        # Check if scheme and netloc are present
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except Exception:
        return False


def validate_port(port: str) -> bool:
    """
    Validate if a string represents a valid port number.
    
    Args:
        port: The port string to validate
        
    Returns:
        True if valid port, False otherwise
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized


def parse_server_url(url: str) -> Optional[tuple[str, int]]:
    """
    Parse a server URL to extract host and port.
    
    Args:
        url: The server URL to parse
        
    Returns:
        Tuple of (host, port) if valid, None otherwise
    """
    try:
        parsed = urlparse(url.strip())
        
        if not parsed.netloc:
            return None
            
        # Extract host and port
        if ':' in parsed.netloc:
            host, port_str = parsed.netloc.rsplit(':', 1)
            port = int(port_str)
        else:
            host = parsed.netloc
            port = 443 if parsed.scheme == 'https' else 80
            
        return host, port
        
    except (ValueError, AttributeError):
        return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and size_index < len(size_names) - 1:
        size /= 1024.0
        size_index += 1
    
    return f"{size:.1f} {size_names[size_index]}"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix
