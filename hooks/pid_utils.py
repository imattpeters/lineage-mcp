"""Cross-platform utility for retrieving the ancestor process chain.

Returns the list of (pid, process_name) tuples from the current process
up to the root. Uses ctypes on Windows and /proc on Linux for speed;
falls back to os.getppid() if platform-specific methods fail.
"""

from __future__ import annotations

import os
import sys

# PIDs that should be excluded from ancestor matching (system processes)
_SYSTEM_PIDS = frozenset({0, 4})


def get_ancestor_chain(max_depth: int = 10) -> list[tuple[int, str]]:
    """Get the ancestor process chain starting from the current process.

    Returns:
        List of (pid, process_name) tuples ordered from self to root.
        The first entry is always the current process.
    """
    if sys.platform == "win32":
        return _get_chain_windows(max_depth)
    return _get_chain_unix(max_depth)


def get_ancestor_pids(max_depth: int = 10) -> list[int]:
    """Get just the ancestor PIDs (convenience wrapper).

    Returns:
        List of PIDs ordered from self to root.
    """
    return [pid for pid, _ in get_ancestor_chain(max_depth)]


def chains_overlap(chain_a: list[int], chain_b: list[int]) -> bool:
    """Check if two ancestor PID chains share a common ancestor.

    Excludes system PIDs (0, 4) from the comparison.

    Args:
        chain_a: First list of ancestor PIDs.
        chain_b: Second list of ancestor PIDs.

    Returns:
        True if the chains share at least one non-system PID.
    """
    set_a = set(chain_a) - _SYSTEM_PIDS
    set_b = set(chain_b) - _SYSTEM_PIDS
    return bool(set_a & set_b)


# ---------------------------------------------------------------------------
# Windows implementation using CreateToolhelp32Snapshot (ctypes, no deps)
# ---------------------------------------------------------------------------

def _get_chain_windows(max_depth: int) -> list[tuple[int, str]]:
    """Get ancestor chain on Windows using Win32 API snapshot."""
    try:
        process_map = _snapshot_processes_windows()
    except Exception:
        # Fallback: just use os.getpid/os.getppid
        return _get_chain_fallback(max_depth)

    chain: list[tuple[int, str]] = []
    pid = os.getpid()
    seen: set[int] = set()

    for _ in range(max_depth):
        if pid in seen or pid == 0:
            break
        seen.add(pid)
        ppid, name = process_map.get(pid, (0, "?"))
        chain.append((pid, name))
        pid = ppid

    return chain


def _snapshot_processes_windows() -> dict[int, tuple[int, str]]:
    """Take a snapshot of all running processes on Windows.

    Returns:
        Dict mapping PID -> (parent_pid, exe_name).
    """
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError("CreateToolhelp32Snapshot failed")

    try:
        pe32 = PROCESSENTRY32W()
        pe32.dwSize = ctypes.sizeof(PROCESSENTRY32W)

        processes: dict[int, tuple[int, str]] = {}
        if kernel32.Process32FirstW(snapshot, ctypes.byref(pe32)):
            while True:
                processes[pe32.th32ProcessID] = (
                    pe32.th32ParentProcessID,
                    pe32.szExeFile,
                )
                if not kernel32.Process32NextW(snapshot, ctypes.byref(pe32)):
                    break
        return processes
    finally:
        kernel32.CloseHandle(snapshot)


# ---------------------------------------------------------------------------
# Unix implementation using /proc (Linux) or ps (macOS)
# ---------------------------------------------------------------------------

def _get_chain_unix(max_depth: int) -> list[tuple[int, str]]:
    """Get ancestor chain on Unix using /proc or ps."""
    chain: list[tuple[int, str]] = []
    pid = os.getpid()
    seen: set[int] = set()

    for _ in range(max_depth):
        if pid in seen or pid == 0:
            break
        seen.add(pid)
        ppid, name = _get_process_info_unix(pid)
        chain.append((pid, name))
        if ppid is None:
            break
        pid = ppid

    return chain


def _get_process_info_unix(pid: int) -> tuple[int | None, str]:
    """Get (parent_pid, name) for a process on Unix."""
    # Try /proc first (Linux)
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            ppid = None
            name = "?"
            for line in f:
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("PPid:"):
                    ppid = int(line.split(":", 1)[1].strip())
            return ppid, name
    except (FileNotFoundError, PermissionError, ValueError):
        pass

    # Fallback: ps command (macOS, other Unix)
    try:
        import subprocess

        result = subprocess.run(
            ["ps", "-o", "ppid=,comm=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            line = result.stdout.strip()
            parts = line.split(None, 1)
            if len(parts) >= 2:
                return int(parts[0]), parts[1]
            elif len(parts) == 1:
                return int(parts[0]), "?"
    except Exception:
        pass

    return None, "?"


# ---------------------------------------------------------------------------
# Fallback using only os.getpid/os.getppid (limited to direct parent)
# ---------------------------------------------------------------------------

def _get_chain_fallback(max_depth: int) -> list[tuple[int, str]]:
    """Minimal fallback: current process + direct parent only."""
    chain = [(os.getpid(), "self")]
    if max_depth > 1:
        ppid = os.getppid()
        if ppid != 0:
            chain.append((ppid, "parent"))
    return chain
