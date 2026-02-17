"""Tests for session_store module."""

import time

from lineage_tray.session_store import SessionInfo, SessionStore, infer_client_from_ancestors


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


class TestFindByFilter:
    """Tests for SessionStore.find_by_filter."""

    def test_find_by_filter_base_dir(self):
        """SessionStore finds sessions by base_dir (case-insensitive on Windows)."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "VS Code",
        })
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj2",
            "started_at": time.time(),
            "client_name": "Cursor",
        })
        matches = store.find_by_filter(base_dir="C:\\proj1")
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_find_by_filter_base_dir_case_insensitive(self):
        """Base dir matching is case-insensitive."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\MyProject",
            "started_at": time.time(),
        })
        matches = store.find_by_filter(base_dir="c:\\myproject")
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_find_by_filter_client_name(self):
        """SessionStore finds sessions by client_name (substring match)."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "VS Code Insiders",
        })
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "Claude Desktop",
        })
        matches = store.find_by_filter(client_name="vscode")
        # "vscode" is not a substring of "VS Code Insiders", so no match
        assert len(matches) == 0

        matches = store.find_by_filter(client_name="VS Code")
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_find_by_filter_combined(self):
        """SessionStore intersects base_dir + client_name filters."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "VS Code",
        })
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "Cursor",
        })
        store.register({
            "session_id": "s3",
            "pid": 9012,
            "base_dir": "C:\\proj2",
            "started_at": time.time(),
            "client_name": "VS Code",
        })
        matches = store.find_by_filter(base_dir="C:\\proj1", client_name="VS Code")
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_find_by_filter_no_filters(self):
        """With no filters, returns all sessions."""
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
        matches = store.find_by_filter()
        assert len(matches) == 2

    def test_find_by_filter_no_matches(self):
        """Returns empty list when no sessions match."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "VS Code",
        })
        matches = store.find_by_filter(base_dir="C:\\nonexistent")
        assert len(matches) == 0

    def test_find_by_filter_client_name_none_in_session(self):
        """Sessions with client_name=None are included when filtering by client_name."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            # client_name is None
        })
        # When session.client_name is None, the filter condition skips the
        # client_name check (due to `and session.client_name is not None`),
        # so the session IS included.
        matches = store.find_by_filter(client_name="VS Code")
        assert len(matches) == 1


class TestFindByFilterAncestorPids:
    """Tests for find_by_filter with ancestor PID matching."""

    def test_match_by_ancestor_pids(self):
        """Sessions match when ancestor chains overlap."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 200, 300],
        })
        # Hook has chain [400, 200, 500] — shares PID 200
        matches = store.find_by_filter(
            base_dir="C:\\proj", ancestor_pids=[400, 200, 500]
        )
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_no_match_disjoint_ancestors(self):
        """Sessions don't match when ancestor chains don't overlap."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 200, 300],
        })
        matches = store.find_by_filter(
            base_dir="C:\\proj", ancestor_pids=[400, 500, 600]
        )
        assert len(matches) == 0

    def test_system_pids_excluded_from_match(self):
        """System PIDs (0, 4) should not count as overlap."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 0, 4],
        })
        # Only system PIDs in common
        matches = store.find_by_filter(
            base_dir="C:\\proj", ancestor_pids=[200, 0, 4]
        )
        assert len(matches) == 0

    def test_ancestor_match_with_base_dir_filter(self):
        """Ancestor matching respects base_dir filter too."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "ancestor_pids": [100, 200, 300],
        })
        store.register({
            "session_id": "s2",
            "pid": 101,
            "base_dir": "C:\\proj2",
            "started_at": time.time(),
            "ancestor_pids": [101, 200, 300],
        })
        # Same ancestor chain overlap, different base_dir
        matches = store.find_by_filter(
            base_dir="C:\\proj1", ancestor_pids=[400, 200, 500]
        )
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_fallback_to_client_name_when_session_has_no_ancestors(self):
        """Falls back to client_name matching when session has no ancestor_pids."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "claude-code",
            # No ancestor_pids
        })
        # ancestor_pids provided but session has none → falls back to client_name
        matches = store.find_by_filter(
            base_dir="C:\\proj",
            client_name="claude",
            ancestor_pids=[400, 500],
        )
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_ancestor_takes_priority_over_client_name(self):
        """When ancestor_pids are available, client_name is ignored for matching."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "claude-code",
            "ancestor_pids": [100, 200, 300],
        })
        store.register({
            "session_id": "s2",
            "pid": 101,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "claude-code",
            "ancestor_pids": [101, 400, 500],
        })
        # Both have client_name "claude-code" but only s1 has matching ancestor
        matches = store.find_by_filter(
            base_dir="C:\\proj",
            client_name="claude-code",
            ancestor_pids=[600, 200, 700],
        )
        assert len(matches) == 1
        assert matches[0].session_id == "s1"

    def test_no_ancestor_pids_in_filter_uses_client_name(self):
        """When no ancestor_pids in filter, uses client_name matching."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "Visual Studio Code",
            "ancestor_pids": [100, 200, 300],
        })
        store.register({
            "session_id": "s2",
            "pid": 101,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "claude-code",
            "ancestor_pids": [101, 400, 500],
        })
        # No ancestor_pids → fallback to client_name
        matches = store.find_by_filter(
            base_dir="C:\\proj",
            client_name="Visual Studio",
        )
        assert len(matches) == 1
        assert matches[0].session_id == "s1"


class TestAncestorChainStr:
    """Tests for SessionInfo.ancestor_chain_str property."""

    def test_ancestor_chain_str_with_names(self):
        """Formats chain with names and PIDs."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 200, 300],
            "ancestor_names": ["python.exe", "pwsh.exe", "Code.exe"],
        })
        session = store.get("s1")
        assert session is not None
        chain = session.ancestor_chain_str
        assert "python.exe(100)" in chain
        assert "pwsh.exe(200)" in chain
        assert "Code.exe(300)" in chain
        assert " → " in chain

    def test_ancestor_chain_str_empty(self):
        """Shows 'no chain' when no ancestor data."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
        })
        session = store.get("s1")
        assert session is not None
        assert "no chain" in session.ancestor_chain_str

    def test_ancestor_chain_str_pids_only(self):
        """Shows '?' for names when pids but no names provided."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 200],
            # No ancestor_names
        })
        session = store.get("s1")
        assert session is not None
        chain = session.ancestor_chain_str
        assert "?(100)" in chain
        assert "?(200)" in chain


class TestInferClientFromAncestors:
    """Tests for infer_client_from_ancestors function."""

    def test_code_exe(self):
        """Detects Visual Studio Code from Code.exe."""
        result = infer_client_from_ancestors(["python.exe", "pwsh.exe", "Code.exe"])
        assert result == "Visual Studio Code"

    def test_opencode_exe(self):
        """Detects opencode from opencode.exe."""
        result = infer_client_from_ancestors(["python.exe", "opencode.exe"])
        assert result == "opencode"

    def test_claude_exe(self):
        """Detects Claude Code from claude.exe."""
        result = infer_client_from_ancestors(["python.exe", "claude.exe"])
        assert result == "Claude Code"

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        result = infer_client_from_ancestors(["Python.exe", "CODE.EXE"])
        assert result == "Visual Studio Code"

    def test_no_match(self):
        """Returns None when no known client found."""
        result = infer_client_from_ancestors(["python.exe", "bash", "systemd"])
        assert result is None

    def test_empty_list(self):
        """Returns None for empty ancestor list."""
        result = infer_client_from_ancestors([])
        assert result is None

    def test_first_match_wins(self):
        """Returns the first matching ancestor."""
        result = infer_client_from_ancestors(["opencode.exe", "Code.exe"])
        assert result == "opencode"

    def test_unix_code_no_extension(self):
        """Detects VS Code on Linux/macOS where process is 'code' (no .exe)."""
        result = infer_client_from_ancestors(["python3", "code", "bash"])
        assert result == "Visual Studio Code"


class TestRegisterInfersClientName:
    """Tests that register() infers client_name from ancestors."""

    def test_infers_vscode_on_register(self):
        """New session with Code.exe ancestor gets client_name inferred."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 200, 300],
            "ancestor_names": ["python.exe", "pwsh.exe", "Code.exe"],
        })
        session = store.get("s1")
        assert session is not None
        assert session.client_name == "Visual Studio Code"

    def test_infers_opencode_on_register(self):
        """New session with opencode.exe ancestor gets client_name inferred."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 200],
            "ancestor_names": ["python.exe", "opencode.exe"],
        })
        session = store.get("s1")
        assert session is not None
        assert session.client_name == "opencode"

    def test_explicit_client_name_not_overridden(self):
        """If client_name is provided, inference is skipped."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "MyCustomClient",
            "ancestor_pids": [100, 200],
            "ancestor_names": ["python.exe", "Code.exe"],
        })
        session = store.get("s1")
        assert session is not None
        assert session.client_name == "MyCustomClient"

    def test_update_overrides_inferred_name(self):
        """MCP client's actual client_name overwrites the inferred one."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "ancestor_pids": [100, 200],
            "ancestor_names": ["python.exe", "Code.exe"],
        })
        # Inferred initially
        session = store.get("s1")
        assert session.client_name == "Visual Studio Code"

        # MCP client sends real name
        store.update("s1", {"client_name": "GitHub Copilot Chat"})
        session = store.get("s1")
        assert session.client_name == "GitHub Copilot Chat"

    def test_no_ancestors_no_inference(self):
        """Without ancestor data, client_name stays None."""
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
        })
        session = store.get("s1")
        assert session is not None
        assert session.client_name is None
