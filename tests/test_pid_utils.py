"""Tests for hooks/pid_utils.py — ancestor PID chain retrieval."""

import os
import sys

import pytest

# Add the repo root to path so we can import hooks.pid_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks.pid_utils import (
    chains_overlap,
    get_ancestor_chain,
    get_ancestor_pids,
)


class TestGetAncestorChain:
    """Tests for get_ancestor_chain()."""

    def test_returns_list_of_tuples(self):
        """Chain should be a list of (pid, name) tuples."""
        chain = get_ancestor_chain()
        assert isinstance(chain, list)
        assert len(chain) >= 1
        for pid, name in chain:
            assert isinstance(pid, int)
            assert isinstance(name, str)

    def test_first_entry_is_current_process(self):
        """First entry should be our own PID."""
        chain = get_ancestor_chain()
        assert chain[0][0] == os.getpid()

    def test_second_entry_is_parent(self):
        """Second entry should be our parent PID."""
        chain = get_ancestor_chain()
        if len(chain) >= 2:
            assert chain[1][0] == os.getppid()

    def test_no_duplicate_pids(self):
        """Chain should not contain duplicate PIDs (cycle detection)."""
        chain = get_ancestor_chain()
        pids = [pid for pid, _ in chain]
        assert len(pids) == len(set(pids))

    def test_max_depth_limits_chain(self):
        """max_depth should limit the chain length."""
        chain = get_ancestor_chain(max_depth=2)
        assert len(chain) <= 2

    def test_max_depth_1_returns_only_self(self):
        """max_depth=1 should return only the current process."""
        chain = get_ancestor_chain(max_depth=1)
        assert len(chain) == 1
        assert chain[0][0] == os.getpid()


class TestGetAncestorPids:
    """Tests for get_ancestor_pids()."""

    def test_returns_list_of_ints(self):
        """Should return a flat list of PIDs."""
        pids = get_ancestor_pids()
        assert isinstance(pids, list)
        for pid in pids:
            assert isinstance(pid, int)

    def test_first_is_current_pid(self):
        """First PID should be ours."""
        pids = get_ancestor_pids()
        assert pids[0] == os.getpid()

    def test_matches_chain(self):
        """Should match the PIDs from get_ancestor_chain."""
        chain = get_ancestor_chain()
        pids = get_ancestor_pids()
        assert pids == [pid for pid, _ in chain]


class TestChainsOverlap:
    """Tests for chains_overlap()."""

    def test_overlap_with_common_pid(self):
        """Should return True when chains share a PID."""
        assert chains_overlap([100, 200, 300], [300, 400, 500]) is True

    def test_no_overlap(self):
        """Should return False when chains share no PIDs."""
        assert chains_overlap([100, 200, 300], [400, 500, 600]) is False

    def test_empty_chains(self):
        """Empty chains should not overlap."""
        assert chains_overlap([], [1, 2, 3]) is False
        assert chains_overlap([1, 2, 3], []) is False
        assert chains_overlap([], []) is False

    def test_system_pids_excluded(self):
        """PIDs 0 and 4 (system) should be excluded from matching."""
        assert chains_overlap([0, 4], [0, 4]) is False
        assert chains_overlap([0, 100], [0, 200]) is False
        assert chains_overlap([4, 100], [4, 200]) is False

    def test_system_pid_with_real_overlap(self):
        """System PIDs excluded but real overlap still works."""
        assert chains_overlap([0, 4, 100], [0, 4, 100]) is True

    def test_identical_chains(self):
        """Identical chains should overlap."""
        assert chains_overlap([100, 200], [100, 200]) is True

    def test_subset_chain(self):
        """A subset chain should overlap."""
        assert chains_overlap([100], [100, 200, 300]) is True

    def test_single_element_overlap(self):
        """Single matching PID is enough."""
        assert chains_overlap([999], [999]) is True
