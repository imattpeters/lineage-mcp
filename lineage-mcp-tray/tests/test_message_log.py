"""Tests for message_log module."""

import threading
import time

from lineage_tray.message_log import LogEntry, MessageLog


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_direction_arrow_received(self):
        entry = LogEntry(direction="received", session_id="s1", message={"type": "register"})
        assert entry.direction_arrow == "←"

    def test_direction_arrow_sent(self):
        entry = LogEntry(direction="sent", session_id="s1", message={"type": "interrupt"})
        assert entry.direction_arrow == "→"

    def test_time_str_format(self):
        entry = LogEntry(session_id="s1", message={"type": "test"})
        # Should be HH:MM:SS format
        assert len(entry.time_str) == 8
        assert entry.time_str.count(":") == 2

    def test_format_simple(self):
        entry = LogEntry(direction="received", session_id="s1", message={"type": "register"})
        formatted = entry.format()
        assert "←" in formatted
        assert "s1" in formatted
        assert "register" in formatted

    def test_format_with_label(self):
        entry = LogEntry(direction="sent", session_id="s1", message={"type": "interrupt"})
        formatted = entry.format("VS Code session")
        assert "→" in formatted
        assert "VS Code session" in formatted
        assert "interrupt" in formatted

    def test_format_with_extras(self):
        entry = LogEntry(
            direction="received",
            session_id="s1",
            message={"type": "update", "files_tracked": 5, "client_name": "VS Code"},
        )
        formatted = entry.format()
        assert "update" in formatted
        assert "files_tracked=5" in formatted
        assert "client_name=VS Code" in formatted


class TestMessageLog:
    """Tests for MessageLog class."""

    def test_empty_log(self):
        log = MessageLog()
        assert log.count == 0
        assert log.get_recent() == []

    def test_log_received(self):
        log = MessageLog()
        log.log_received("s1", {"type": "register", "pid": 1234})
        assert log.count == 1
        entries = log.get_recent()
        assert len(entries) == 1
        assert entries[0].direction == "received"
        assert entries[0].session_id == "s1"
        assert entries[0].message["type"] == "register"

    def test_log_sent(self):
        log = MessageLog()
        log.log_sent("s1", {"type": "interrupt"})
        assert log.count == 1
        entries = log.get_recent()
        assert entries[0].direction == "sent"

    def test_get_recent_limits(self):
        log = MessageLog()
        for i in range(20):
            log.log_received("s1", {"type": "update", "i": i})
        # Default recent = last 10
        entries = log.get_recent()
        assert len(entries) == 10
        assert entries[0].message["i"] == 10  # Oldest of last 10
        assert entries[-1].message["i"] == 19  # Most recent

    def test_get_recent_custom_n(self):
        log = MessageLog()
        for i in range(5):
            log.log_received("s1", {"type": "test", "i": i})
        entries = log.get_recent(3)
        assert len(entries) == 3
        assert entries[0].message["i"] == 2

    def test_max_entries_circular_buffer(self):
        log = MessageLog(max_entries=5)
        for i in range(10):
            log.log_received("s1", {"type": "test", "i": i})
        assert log.count == 5
        entries = log.get_recent(10)  # Ask for more than exists
        assert len(entries) == 5
        assert entries[0].message["i"] == 5  # Oldest surviving entry
        assert entries[-1].message["i"] == 9  # Most recent

    def test_message_copy(self):
        """Messages should be copied to avoid mutation."""
        log = MessageLog()
        msg = {"type": "test", "data": [1, 2, 3]}
        log.log_received("s1", msg)
        msg["data"].append(4)  # Mutate original
        entries = log.get_recent()
        assert entries[0].message["data"] == [1, 2, 3]  # Should be unchanged

    def test_clear(self):
        log = MessageLog()
        log.log_received("s1", {"type": "test"})
        log.log_sent("s1", {"type": "interrupt"})
        assert log.count == 2
        log.clear()
        assert log.count == 0
        assert log.get_recent() == []

    def test_thread_safety(self):
        """Log should be safe for concurrent access."""
        log = MessageLog(max_entries=1000)
        errors = []

        def writer(session_id: str, count: int) -> None:
            try:
                for i in range(count):
                    log.log_received(session_id, {"type": "test", "i": i})
                    log.log_sent(session_id, {"type": "ack", "i": i})
            except Exception as e:
                errors.append(e)

        def reader(count: int) -> None:
            try:
                for _ in range(count):
                    log.get_recent(5)
                    _ = log.count
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=("s1", 100)),
            threading.Thread(target=writer, args=("s2", 100)),
            threading.Thread(target=reader, args=(200,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Thread safety errors: {errors}"
        assert log.count > 0

    def test_mixed_directions_ordering(self):
        """Entries maintain insertion order regardless of direction."""
        log = MessageLog()
        log.log_received("s1", {"type": "register"})
        log.log_sent("s1", {"type": "interrupt"})
        log.log_received("s1", {"type": "update"})

        entries = log.get_recent()
        assert entries[0].direction == "received"
        assert entries[0].message["type"] == "register"
        assert entries[1].direction == "sent"
        assert entries[1].message["type"] == "interrupt"
        assert entries[2].direction == "received"
        assert entries[2].message["type"] == "update"
