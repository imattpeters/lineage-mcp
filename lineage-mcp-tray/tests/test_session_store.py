"""Tests for session_store module."""

import time

from lineage_tray.session_store import SessionInfo, SessionStore


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_display_name_with_client(self):
        s = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
            client_name="VS Code",
        )
        assert "VS Code" in s.display_name

    def test_display_name_with_first_call(self):
        s = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
            client_name="Cursor",
            first_call="[edit:app.py]",
        )
        assert "Cursor" in s.display_name
        assert "[edit:app.py]" in s.display_name

    def test_display_name_fallback_pid(self):
        s = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
        )
        assert "PID 1234" in s.display_name

    def test_since_str(self):
        s = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
        )
        # Should produce something like "02:30 PM"
        assert len(s.since_str) > 0


class TestSessionStore:
    """Tests for SessionStore."""

    def test_register_new(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
        })
        assert store.count == 1
        assert store.get("s1") is not None
        assert store.get("s1").pid == 1234

    def test_register_update_existing(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
        })
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "VS Code",
        })
        assert store.count == 1
        assert store.get("s1").client_name == "VS Code"

    def test_unregister(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
        })
        store.unregister("s1")
        assert store.count == 0
        assert store.get("s1") is None

    def test_unregister_nonexistent(self):
        store = SessionStore()
        store.unregister("nonexistent")  # Should not raise
        assert store.count == 0

    def test_update(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "files_tracked": 0,
        })
        store.update("s1", {"files_tracked": 15})
        assert store.get("s1").files_tracked == 15

    def test_update_nonexistent(self):
        store = SessionStore()
        store.update("nonexistent", {"files_tracked": 10})  # Should not raise

    def test_get_grouped_empty(self):
        store = SessionStore()
        groups = store.get_grouped()
        assert groups == {}

    def test_get_grouped_single(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
        })
        groups = store.get_grouped()
        assert "C:\\proj1" in groups
        assert len(groups["C:\\proj1"]) == 1

    def test_get_grouped_multiple_same_dir(self):
        store = SessionStore()
        t = time.time()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": t,
        })
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj1",
            "started_at": t + 1,
        })
        groups = store.get_grouped()
        assert len(groups["C:\\proj1"]) == 2
        # Should be sorted by started_at
        assert groups["C:\\proj1"][0].pid == 1234
        assert groups["C:\\proj1"][1].pid == 5678

    def test_get_grouped_multiple_dirs(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
        })
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj2",
            "started_at": time.time(),
        })
        groups = store.get_grouped()
        assert len(groups) == 2
        assert "C:\\proj1" in groups
        assert "C:\\proj2" in groups

    def test_count(self):
        store = SessionStore()
        assert store.count == 0
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
        })
        assert store.count == 1
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
        })
        assert store.count == 2
