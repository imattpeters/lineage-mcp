"""Main tray application orchestrator.

Ties together pystray icon, pipe server, session store, menu builder,
and message log.
"""

import logging
import threading

import pystray
from pystray import Menu

from lineage_tray.actions import clear_by_filter
from lineage_tray.icon import create_tray_icon, create_tray_icon_with_badge
from lineage_tray.menu_builder import build_menu
from lineage_tray.message_log import MessageLog
from lineage_tray.pipe_server import PipeServer
from lineage_tray.session_store import CompactionEvent, SessionStore

logger = logging.getLogger("lineage_tray.app")


class TrayApp:
    """Main tray application.

    Manages the system tray icon, pipe server, session store, and message log.
    """

    def __init__(self) -> None:
        self.store = SessionStore()
        self.message_log = MessageLog()
        self.compaction_events: list[CompactionEvent] = []
        self._base_icon = create_tray_icon()
        self._stopping = False
        self.pipe_server = PipeServer(
            on_message=self._on_message,
            message_log=self.message_log,
            on_external_command=self._on_external_command,
        )
        self.icon = pystray.Icon(
            "lineage-mcp",
            icon=self._base_icon,
            title="Lineage MCP \u2014 No active sessions",
            menu=Menu(
                lambda: build_menu(
                    self.store, self.pipe_server, self.icon, self.message_log,
                    compaction_events=self.compaction_events,
                )
            ),
        )

    def _on_message(self, session_id: str, msg: dict) -> None:
        """Handle messages from lineage-mcp instances.

        Args:
            session_id: The session that sent the message.
            msg: The message dict.
        """
        if self._stopping:
            return

        try:
            msg_type = msg.get("type")
            if msg_type == "register":
                logger.info(
                    "Session registered: %s (pid=%s, base_dir=%s, interrupted=%s)",
                    session_id,
                    msg.get("pid"),
                    msg.get("base_dir"),
                    msg.get("interrupted", False),
                )
                self.store.register(msg)
            elif msg_type == "update":
                logger.debug(
                    "Session update: %s — %s",
                    session_id,
                    {k: v for k, v in msg.items() if k != "type"},
                )
                self.store.update(session_id, msg)
            elif msg_type == "tool_call":
                logger.debug(
                    "Tool call: %s — %s",
                    session_id,
                    msg.get("summary", ""),
                )
                self.store.update(session_id, {
                    "last_tool": msg.get("summary", msg.get("tool", "")),
                })
            elif msg_type == "unregister":
                logger.info("Session unregistered: %s", session_id)
                self.store.unregister(session_id)
            else:
                logger.warning(
                    "Unknown message type %r from session %s", msg_type, session_id
                )

            self._update_icon()

        except Exception:
            if not self._stopping:
                logger.error(
                    "Error handling message from %s: %r", session_id, msg, exc_info=True
                )

    def _update_icon(self) -> None:
        """Update icon badge, tooltip, and menu. Safe to call anytime."""
        if self._stopping:
            return

        try:
            count = self.store.count
            if count == 0:
                self.icon.title = "Lineage MCP \u2014 No active sessions"
            elif count == 1:
                self.icon.title = "Lineage MCP \u2014 1 active session"
            else:
                self.icon.title = f"Lineage MCP \u2014 {count} active sessions"

            self.icon.icon = create_tray_icon_with_badge(self._base_icon, count)
            self.icon.update_menu()
        except Exception:
            if not self._stopping:
                logger.error("Error updating icon", exc_info=True)

    def _on_external_command(self, msg: dict) -> dict:
        """Handle external commands from hook scripts.

        Args:
            msg: The command message dict.

        Returns:
            Response dict to send back to the caller.
        """
        cmd = msg.get("type")
        logger.info(
            "External command: %s from %s", cmd, msg.get("client_name", "unknown")
        )

        try:
            if cmd == "clear_by_filter":
                # Find matching sessions BEFORE clearing (to capture their info)
                matches = self.store.find_by_filter(
                    base_dir=msg.get("base_dir"),
                    client_name=msg.get("client_name"),
                    ancestor_pids=msg.get("ancestor_pids"),
                    ancestor_names=msg.get("ancestor_names"),
                )

                result = clear_by_filter(
                    self.store,
                    self.pipe_server,
                    base_dir=msg.get("base_dir"),
                    client_name=msg.get("client_name"),
                    ancestor_pids=msg.get("ancestor_pids"),
                    ancestor_names=msg.get("ancestor_names"),
                )

                # Record compaction events for cleared sessions
                for session in matches:
                    self.compaction_events.append(CompactionEvent(
                        session_id=session.session_id,
                        client_name=session.client_name,
                        base_dir=session.base_dir,
                        ancestor_chain_str=session.ancestor_chain_str,
                        files_tracked=session.files_tracked,
                    ))

                logger.info(
                    "clear_by_filter: %d sessions matched, result=%r",
                    len(matches),
                    result,
                )
                return result

            return {"error": "unknown command"}

        except Exception:
            logger.error(
                "Error handling external command: %r", msg, exc_info=True
            )
            return {"error": "Internal error processing command"}

    def run(self) -> None:
        """Start the tray app. This blocks on the main thread."""

        # Install a global thread exception handler to prevent
        # unhandled exceptions (like Tcl_AsyncDelete) from crashing
        _original_excepthook = threading.excepthook

        def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
            # Suppress Tcl-related errors during shutdown
            if self._stopping:
                logger.debug(
                    "Suppressed thread exception during shutdown: %s",
                    args.exc_type.__name__ if args.exc_type else "unknown",
                )
                return
            # Fall through to original handler for non-shutdown errors
            if _original_excepthook:
                _original_excepthook(args)

        threading.excepthook = _thread_excepthook

        def setup(icon: pystray.Icon) -> None:
            icon.visible = True
            self.pipe_server.start()
            logger.info("Tray icon visible, pipe server started")

        try:
            self.icon.run(setup=setup)
        finally:
            # Restore original excepthook
            threading.excepthook = _original_excepthook

    def stop(self) -> None:
        """Stop the tray app and clean up.

        Sets the stopping flag first to suppress spurious errors from
        background threads during shutdown.
        """
        if self._stopping:
            return
        self._stopping = True
        logger.info("Stopping tray app")

        # Destroy any open Tkinter windows before stopping the icon/pipe.
        # This must happen while Python is still running (before os._exit)
        # so Tcl can clean up its async handlers properly, preventing the
        # fatal Tcl_AsyncDelete crash.
        try:
            from lineage_tray.menu_builder import _destroy_message_log_on_exit
            _destroy_message_log_on_exit()
        except Exception:
            pass

        try:
            self.pipe_server.stop()
        except Exception:
            logger.error("Error stopping pipe server", exc_info=True)
        try:
            self.icon.stop()
        except Exception:
            logger.error("Error stopping icon", exc_info=True)
