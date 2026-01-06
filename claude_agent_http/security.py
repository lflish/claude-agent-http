"""
Security utilities for path validation and sanitization.
"""
import os
import re
from typing import Optional, List

from .exceptions import PathSecurityError


def validate_user_id(user_id: str) -> str:
    """
    Validate user_id format.

    Args:
        user_id: User identifier

    Returns:
        Validated user_id

    Raises:
        PathSecurityError: If user_id is invalid
    """
    if not user_id:
        raise PathSecurityError("user_id cannot be empty")

    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        raise PathSecurityError(
            "user_id must contain only alphanumeric characters, underscores, or hyphens"
        )

    if len(user_id) > 64:
        raise PathSecurityError("user_id too long (max 64 characters)")

    return user_id


def validate_subdir(subdir: Optional[str]) -> Optional[str]:
    """
    Validate and sanitize subdir path.

    Args:
        subdir: Subdirectory path (relative)

    Returns:
        Sanitized subdir or None

    Raises:
        PathSecurityError: If subdir is invalid
    """
    if not subdir:
        return None

    # Remove leading/trailing slashes
    subdir = subdir.strip('/')

    if not subdir:
        return None

    # Check for path traversal
    if '..' in subdir:
        raise PathSecurityError("Path traversal (..) not allowed")

    # Check for absolute path
    if subdir.startswith('/'):
        raise PathSecurityError("Absolute path not allowed")

    # Check for null bytes
    if '\x00' in subdir:
        raise PathSecurityError("Null bytes not allowed in path")

    # Check length
    if len(subdir) > 200:
        raise PathSecurityError("subdir too long (max 200 characters)")

    return subdir


def build_cwd(user_id: str, subdir: Optional[str], base_dir: str) -> str:
    """
    Build and validate the full cwd path.

    Args:
        user_id: User identifier
        subdir: Optional subdirectory (relative)
        base_dir: Base directory for all users

    Returns:
        Full validated cwd path

    Raises:
        PathSecurityError: If path escapes base_dir
    """
    # Validate inputs
    user_id = validate_user_id(user_id)
    subdir = validate_subdir(subdir)

    # Build path
    if subdir:
        cwd = os.path.join(base_dir, user_id, subdir)
    else:
        cwd = os.path.join(base_dir, user_id)

    # Normalize path
    cwd = os.path.normpath(cwd)

    # Security check: ensure cwd is under base_dir/user_id
    user_base = os.path.normpath(os.path.join(base_dir, user_id))
    if not cwd.startswith(user_base):
        raise PathSecurityError(f"Path escape detected: {cwd} is not under {user_base}")

    return cwd


def build_add_dirs(
    add_dirs: Optional[List[str]],
    user_id: str,
    base_dir: str
) -> List[str]:
    """
    Build and validate add_dirs paths.

    Args:
        add_dirs: List of relative paths
        user_id: User identifier
        base_dir: Base directory for all users

    Returns:
        List of full validated paths

    Raises:
        PathSecurityError: If any path is invalid
    """
    if not add_dirs:
        return []

    result = []
    user_base = os.path.normpath(os.path.join(base_dir, user_id))

    for d in add_dirs:
        # Validate relative path
        d = d.strip('/')
        if not d:
            continue

        if '..' in d:
            raise PathSecurityError(f"Path traversal not allowed in add_dirs: {d}")

        if d.startswith('/'):
            raise PathSecurityError(f"Absolute path not allowed in add_dirs: {d}")

        # Build full path
        full_path = os.path.normpath(os.path.join(user_base, d))

        # Security check
        if not full_path.startswith(user_base):
            raise PathSecurityError(f"Path escape detected in add_dirs: {d}")

        result.append(full_path)

    return result


def ensure_directory(path: str, auto_create: bool = True) -> bool:
    """
    Ensure directory exists.

    Args:
        path: Directory path
        auto_create: Whether to create if not exists

    Returns:
        True if directory exists or was created

    Raises:
        PathSecurityError: If creation fails
    """
    if os.path.exists(path):
        if os.path.isdir(path):
            return True
        else:
            raise PathSecurityError(f"Path exists but is not a directory: {path}")

    if auto_create:
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except OSError as e:
            raise PathSecurityError(f"Failed to create directory {path}: {e}")

    return False
