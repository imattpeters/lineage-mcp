"""PreCompact hook script for lineage-mcp.

Called by AI client hooks (Claude Code, VS Code) when context
compaction occurs. Connects to the lineage-mcp-tray Named Pipe and
requests cache clearing for matching sessions.

The hook sends its ancestor PID chain so the tray can match it against
registered MCP server sessions — both are spawned by the same AI client
process, so their ancestor chains will overlap.

Usage:
    echo '{"cwd":"/path/to/project",...}' | python precompact.py <client_name>

    client_name: Required. Identifies the AI client for logging purposes.
                 Examples: "claude-code", "Visual Studio Code"

Exit codes:
    0 - Success (or tray not running - silent no-op)
    1 - Invalid arguments or unexpected error
"""

import json
import os
import sys

# Allow importing pid_utils from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pid_utils import get_ancestor_chain

PIPE_ADDRESS = r'\\.\pipe\lineage-mcp-tray'
PIPE_AUTHKEY = b'lineage-mcp-tray-v1'


def get_pipe_address():
    """Get the platform-appropriate pipe address."""
    if sys.platform == 'win32':
        return PIPE_ADDRESS
    import tempfile
    return os.path.join(tempfile.gettempdir(), 'lineage-mcp-tray.sock')


def main():
    if len(sys.argv) < 2:
        print("Usage: precompact.py <client_name>", file=sys.stderr)
        sys.exit(1)

    client_name = sys.argv[1]

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # If stdin is empty or invalid, use cwd as fallback
        hook_input = {}

    # Extract base_dir from hook input (cwd field)
    base_dir = hook_input.get("cwd", os.getcwd())

    # Normalize the path for consistent matching
    base_dir = os.path.normpath(base_dir)

    # Get our ancestor PID chain for session matching
    ancestor_chain = get_ancestor_chain()
    ancestor_pids = [pid for pid, _ in ancestor_chain]
    ancestor_names = [name for _, name in ancestor_chain]

    # Connect to tray and send clear request
    try:
        from multiprocessing.connection import Client

        conn = Client(get_pipe_address(), authkey=PIPE_AUTHKEY)

        # Build the clear request message
        msg = {
            "type": "clear_by_filter",
            "base_dir": base_dir,
            "client_name": client_name,
            "ancestor_pids": ancestor_pids,
            "ancestor_names": ancestor_names,
        }

        conn.send(msg)

        # Wait for acknowledgement (with timeout)
        if conn.poll(timeout=5.0):
            response = conn.recv()
            sessions_cleared = response.get("sessions_cleared", 0)
            if sessions_cleared > 0:
                print(
                    f"Cleared {sessions_cleared} session(s) for "
                    f"{client_name} in {base_dir}",
                    file=sys.stderr,
                )
        conn.close()

    except (ConnectionRefusedError, FileNotFoundError, OSError):
        # Tray not running - silent no-op
        pass
    except ImportError:
        # multiprocessing.connection not available (shouldn't happen)
        pass


if __name__ == "__main__":
    main()
