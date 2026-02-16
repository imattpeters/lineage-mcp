"""Action implementations for tray menu commands.

Clear cache and interrupt actions are sent via pipe to lineage-mcp sessions.
These functions are thin wrappers used by the menu_builder module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lineage_tray.pipe_server import PipeServer
    from lineage_tray.session_store import SessionInfo


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
