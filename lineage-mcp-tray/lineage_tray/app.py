"""Main tray application orchestrator.

Ties together pystray icon, pipe server, session store, menu builder,
and message log.
"""

import pystray
from pystray import Menu

from lineage_tray.actions import clear_by_filter
from lineage_tray.icon import create_tray_icon, create_tray_icon_with_badge
from lineage_tray.menu_builder import build_menu
from lineage_tray.message_log import MessageLog
from lineage_tray.pipe_server import PipeServer
from lineage_tray.session_store import CompactionEvent, SessionStore


class TrayApp:
    """Main tray application.

    Manages the system tray icon, pipe server, session store, and message log.
    """

    def __init__(self) -> None:
        self.store = SessionStore()
        self.message_log = MessageLog()
        self.compaction_events: list[CompactionEvent] = []
        self._base_icon = create_tray_icon()
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
        msg_type = msg.get("type")
        if msg_type == "register":
            self.store.register(msg)
        elif msg_type == "update":
            self.store.update(session_id, msg)
        elif msg_type == "unregister":
            self.store.unregister(session_id)

        # Update tray tooltip with session count
        count = self.store.count
        if count == 0:
            self.icon.title = "Lineage MCP \u2014 No active sessions"
        elif count == 1:
            self.icon.title = "Lineage MCP \u2014 1 active session"
        else:
            self.icon.title = f"Lineage MCP \u2014 {count} active sessions"

        # Update icon badge
        self.icon.icon = create_tray_icon_with_badge(self._base_icon, count)

        # Force menu refresh
        self.icon.update_menu()

    def _on_external_command(self, msg: dict) -> dict:
        """Handle external commands from hook scripts.

        Args:
            msg: The command message dict.

        Returns:
            Response dict to send back to the caller.
        """
        cmd = msg.get("type")
        if cmd == "clear_by_filter":
            # Find matching sessions BEFORE clearing (to capture their info)
            matches = self.store.find_by_filter(
                base_dir=msg.get("base_dir"),
                client_name=msg.get("client_name"),
                ancestor_pids=msg.get("ancestor_pids"),
            )

            result = clear_by_filter(
                self.store,
                self.pipe_server,
                base_dir=msg.get("base_dir"),
                client_name=msg.get("client_name"),
                ancestor_pids=msg.get("ancestor_pids"),
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

            return result
        return {"error": "unknown command"}

    def run(self) -> None:
        """Start the tray app. This blocks on the main thread."""

        def setup(icon: pystray.Icon) -> None:
            icon.visible = True
            self.pipe_server.start()

        self.icon.run(setup=setup)

    def stop(self) -> None:
        """Stop the tray app and clean up."""
        self.pipe_server.stop()
        self.icon.stop()
