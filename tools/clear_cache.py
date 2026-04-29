"""Clear cache tool - reset all session caches."""

from session_state import session


async def clear_cache() -> str:
    """Clear all session caches.

    Resets file tracking (mtimes, contents) and appended instruction tracking
    (appended_instruction_folders). Use when instruction files need to be re-provided
    after context compaction.

    Returns:
        Success message confirming cache was cleared
    """
    session.clear()
    return "Cache cleared. Instruction files will be re-provided on next read."
