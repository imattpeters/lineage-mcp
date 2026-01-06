"""Pytest configuration and shared fixtures for Lineage MCP tests.

Run tests with: python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator

import pytest

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import test utilities after path setup
from tests.test_utils import TempWorkspace  # noqa: E402


@pytest.fixture
def temp_workspace() -> Generator[TempWorkspace, None, None]:
    """Pytest fixture for creating isolated test workspaces."""
    with TempWorkspace() as ws:
        yield ws


@pytest.fixture
def clean_session() -> Generator[None, None, None]:
    """Pytest fixture that clears session before and after test."""
    from session_state import session
    session.clear()
    yield
    session.clear()
