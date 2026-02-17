"""Action implementations for tray menu commands.

Clear cache and interrupt actions are sent via pipe to lineage-mcp sessions.
These functions are thin wrappers used by the menu_builder module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lineage_tray.pipe_server import PipeServer
    from lineage_tray.session_store import SessionInfo, SessionStore


def clear_cache(pipe_server: PipeServer, session: SessionInfo) -> bool:
    """Send a clear_cache command to a lineage-mcp session.

    Args:
        pipe_server: The pipe server to send through.
        session: The target session.

    Returns:
        True if the message was sent successfully.
    """
    return pipe_server.send_to_session(
        session.session_id, {"type": "clear_cache"}
    )


def interrupt(pipe_server: PipeServer, session: SessionInfo) -> bool:
    """Send an interrupt command to a lineage-mcp session.

    Args:
        pipe_server: The pipe server to send through.
        session: The target session.

    Returns:
        True if the message was sent successfully.
    """
    return pipe_server.send_to_session(
        session.session_id, {"type": "interrupt"}
    )


def resume(pipe_server: PipeServer, session: SessionInfo) -> bool:
    """Send a resume command to a lineage-mcp session.

    Clears the interrupted state so the session returns to normal operation.

    Args:
        pipe_server: The pipe server to send through.
        session: The target session.

    Returns:
        True if the message was sent successfully.
    """
    return pipe_server.send_to_session(
        session.session_id, {"type": "resume"}
    )


def clear_by_filter(
    store: SessionStore,
    pipe_server: PipeServer,
    base_dir: str | None = None,
    client_name: str | None = None,
    ancestor_pids: list[int] | None = None,
) -> dict:
    """Clear cache for all sessions matching the filter.

    Uses ancestor PID chain matching as the primary mechanism.
    Falls back to client_name matching if ancestor_pids are not available.

    Args:
        store: The session store to search.
        pipe_server: The pipe server to send commands through.
        base_dir: Filter by base directory.
        client_name: Filter by client name (fallback, also for logging).
        ancestor_pids: Ancestor PID chain from the hook script.

    Returns:
        Dict with 'sessions_cleared' count.
    """
    matches = store.find_by_filter(
        base_dir=base_dir,
        client_name=client_name,
        ancestor_pids=ancestor_pids,
    )
    cleared = 0

    for session in matches:
        success = pipe_server.send_to_session(
            session.session_id, {"type": "clear_cache"}
        )
        if success:
            cleared += 1

    return {"sessions_cleared": cleared}
