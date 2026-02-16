"""Builds dynamic pystray Menu from current session state."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pystray
from pystray import Menu, MenuItem

if TYPE_CHECKING:
    from lineage_tray.message_log import MessageLog
    from lineage_tray.pipe_server import PipeServer
    from lineage_tray.session_store import SessionInfo, SessionStore


def build_menu(
    store: SessionStore,
    pipe_server: PipeServer,
    icon: pystray.Icon,
    message_log: MessageLog | None = None,
) -> list[MenuItem]:
    """Build the dynamic tray menu from current session state.

    Args:
        store: Session store with active sessions.
        pipe_server: Pipe server for sending commands to sessions.
        icon: The pystray icon instance (for stop action).
        message_log: Optional message log for viewing recent messages.

    Returns:
        List of MenuItem objects for the tray menu.
    """
    groups = store.get_grouped()
    items: list[MenuItem] = []

    if not groups:
        items.append(MenuItem("No active sessions", None, enabled=False))
    else:
        first_group = True
        for base_dir, sessions in sorted(groups.items()):
            if not first_group:
                items.append(Menu.SEPARATOR)
            first_group = False

            # Group header
            short_dir = _shorten_path(base_dir)
            items.append(MenuItem(f"\U0001f4c1 {short_dir}", None, enabled=False))

            # Session entries
            for sess in sessions:
                display = sess.display_name
                detail = f"  {sess.files_tracked} files \u00b7 since {sess.since_str}"

                # Submenu with actions — use factory to capture session in closure
                sub = _make_session_submenu(sess, pipe_server, store)

                items.append(MenuItem(display, sub))
                items.append(MenuItem(detail, None, enabled=False))

    log_items: list[MenuItem] = []
    if message_log is not None:
        count = message_log.count
        label = f"\U0001f4cb Message Log ({count})" if count > 0 else "\U0001f4cb Message Log"

        def on_view_log(icon: object, item: object) -> None:
            _show_message_log(message_log, store)

        log_items = [MenuItem(label, on_view_log)]

    items.extend(
        [
            Menu.SEPARATOR,
            *log_items,
            MenuItem("Quit", lambda icon, item: icon.stop()),
        ]
    )

    return items


def _make_session_submenu(
    session: SessionInfo,
    pipe_server: PipeServer,
    store: SessionStore,
) -> Menu:
    """Create a submenu with actions for a specific session.

    Uses a factory function to properly capture the session in closures.

    Args:
        session: The session to create actions for.
        pipe_server: Pipe server for sending commands.
        store: Session store for updating interrupted state.

    Returns:
        pystray Menu with session actions and info.
    """

    def on_clear(icon: object, item: object) -> None:
        _clear_cache(pipe_server, session)

    def on_interrupt(icon: object, item: object) -> None:
        _interrupt(pipe_server, session, store)

    def on_resume(icon: object, item: object) -> None:
        _resume(pipe_server, session, store)

    def on_copy(icon: object, item: object) -> None:
        _copy_session_info(session)

    # Show Interrupt when normal, Resume when interrupted
    if session.interrupted:
        status_text = "⛔ INTERRUPTED"
        action_item = MenuItem("\u25b6\ufe0f Resume", on_resume)
    else:
        status_text = "✅ Normal"
        action_item = MenuItem("\u26d4 Interrupt", on_interrupt)

    return Menu(
        MenuItem(status_text, None, enabled=False),
        action_item,
        MenuItem("\U0001f504 Clear Cache", on_clear),
        MenuItem("\U0001f4cb Copy Info", on_copy),
        Menu.SEPARATOR,
        MenuItem(f"PID: {session.pid}", None, enabled=False),
        MenuItem(f"Since: {session.since_str}", None, enabled=False),
        MenuItem(
            f"Files: {session.files_tracked} tracked", None, enabled=False
        ),
    )


def _shorten_path(path: str, max_len: int = 45) -> str:
    """Shorten a path for display by truncating in the middle.

    Shows the start and end of the path with ``...`` in the middle,
    preserving the drive/root and the final directory components so
    users can identify the project.

    Args:
        path: Full path string.
        max_len: Maximum length before shortening.

    Returns:
        Shortened path string with middle truncation if needed.
    """
    if len(path) <= max_len:
        return path

    ellipsis = "..."
    # Reserve space for ellipsis
    available = max_len - len(ellipsis)
    if available < 4:
        return path[:max_len]

    # Show more of the end (project name matters more)
    start_len = available // 3
    end_len = available - start_len
    return path[:start_len] + ellipsis + path[-end_len:]


def _clear_cache(pipe_server: PipeServer, session: SessionInfo) -> None:
    """Send clear_cache command to a session.

    Args:
        pipe_server: Pipe server for sending the command.
        session: Target session.
    """
    pipe_server.send_to_session(session.session_id, {"type": "clear_cache"})


def _interrupt(pipe_server: PipeServer, session: SessionInfo, store: SessionStore) -> None:
    """Send interrupt command to a session and update local state.

    Args:
        pipe_server: Pipe server for sending the command.
        session: Target session.
        store: Session store to update interrupted state.
    """
    pipe_server.send_to_session(session.session_id, {"type": "interrupt"})
    store.update(session.session_id, {"interrupted": True})


def _resume(pipe_server: PipeServer, session: SessionInfo, store: SessionStore) -> None:
    """Send resume command to a session and update local state.

    Args:
        pipe_server: Pipe server for sending the command.
        session: Target session.
        store: Session store to update interrupted state.
    """
    pipe_server.send_to_session(session.session_id, {"type": "resume"})
    store.update(session.session_id, {"interrupted": False})


def _copy_session_info(session: SessionInfo) -> None:
    """Copy session context information to clipboard.

    Args:
        session: Session whose info to copy.
    """
    text = (
        f"[Lineage MCP Session Context]\n"
        f"Base Directory: {session.base_dir}\n"
        f"Client: {session.client_name or 'Unknown'}\n"
        f"PID: {session.pid}\n"
        f"Files Tracked: {session.files_tracked}\n"
        f"Active Since: {session.since_str}\n"
        f"\n"
        f"Note: This session's cache has been cleared. Use new_session=True "
        f"on your next lineage tool call to re-sync instruction files."
    )

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
    except Exception:
        pass  # Clipboard copy is best-effort


# Singleton message log window reference
_message_log_window: object | None = None
_message_log_lock = threading.Lock()


def _show_message_log(message_log: MessageLog, store: SessionStore) -> None:
    """Show or focus the singleton message log window with auto-refresh.

    Only one window is created. Clicking again brings it to front.
    Content refreshes every 2 seconds.

    Args:
        message_log: The message log to display.
        store: Session store for resolving session labels.
    """
    global _message_log_window

    with _message_log_lock:
        if _message_log_window is not None:
            try:
                # Window exists — bring to front
                _message_log_window.lift()  # type: ignore[union-attr]
                _message_log_window.focus_force()  # type: ignore[union-attr]
                return
            except Exception:
                # Window was destroyed externally
                _message_log_window = None

    def _build_text() -> str:
        entries = message_log.get_recent(50)
        if not entries:
            return "No messages recorded yet."
        lines = []
        for entry in entries:
            session = store.get(entry.session_id) if entry.session_id else None
            label = session.display_name if session else entry.session_id
            lines.append(entry.format(label))
        return "\n".join(lines)

    def _run_window() -> None:
        global _message_log_window
        try:
            import tkinter as tk

            window = tk.Tk()
            _message_log_window = window
            window.title("Lineage MCP \u2014 Message Log")
            window.geometry("750x500")
            window.minsize(500, 350)
            window.configure(bg="#1e1e1e")

            def _on_close() -> None:
                global _message_log_window
                _message_log_window = None
                window.destroy()

            window.protocol("WM_DELETE_WINDOW", _on_close)

            # Text widget with monospace font
            text_widget = tk.Text(
                window,
                wrap=tk.WORD,
                font=("Consolas", 10),
                bg="#1e1e1e",
                fg="#d4d4d4",
                insertbackground="#d4d4d4",
                selectbackground="#264f78",
                padx=10,
                pady=10,
            )
            text_widget.insert(tk.END, _build_text())
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(fill=tk.BOTH, expand=True)

            # Bottom bar with buttons
            btn_frame = tk.Frame(window, bg="#1e1e1e", pady=8)
            btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

            def copy_to_clipboard() -> None:
                content = text_widget.get("1.0", tk.END).strip()
                window.clipboard_clear()
                window.clipboard_append(content)

            copy_btn = tk.Button(
                btn_frame,
                text="  \U0001f4cb  Copy to Clipboard  ",
                command=copy_to_clipboard,
                bg="#333333",
                fg="#d4d4d4",
                font=("Segoe UI", 10),
                padx=14,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2",
            )
            copy_btn.pack(side=tk.RIGHT, padx=(5, 0))

            close_btn = tk.Button(
                btn_frame,
                text="  Close  ",
                command=_on_close,
                bg="#333333",
                fg="#d4d4d4",
                font=("Segoe UI", 10),
                padx=14,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2",
            )
            close_btn.pack(side=tk.RIGHT)

            # Auto-refresh every 2 seconds
            def _refresh() -> None:
                try:
                    new_text = _build_text()
                    text_widget.config(state=tk.NORMAL)
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert(tk.END, new_text)
                    text_widget.config(state=tk.DISABLED)
                    window.after(2000, _refresh)
                except Exception:
                    pass  # Window may have been closed

            window.after(2000, _refresh)

            window.mainloop()
        except Exception:
            _message_log_window = None  # Ensure cleanup on error

    threading.Thread(target=_run_window, daemon=True).start()
