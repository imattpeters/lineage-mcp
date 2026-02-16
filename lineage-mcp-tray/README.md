# lineage-mcp-tray

System tray companion for [lineage-mcp](https://github.com/imattpeters/lineage-mcp).

Shows active Lineage MCP sessions grouped by `base_dir`, with actions like Clear Cache and Interrupt.

## Installation

```bash
pip install lineage-mcp-tray
```

## Usage

```bash
# Run directly
lineage-tray

# Or via Python module
python -m lineage_tray
```

The tray application is automatically launched by `lineage-mcp` when a session starts (if installed).

## Features

- **Session Monitoring**: Shows all active lineage-mcp sessions grouped by base directory
- **Clear Cache**: Clear the file tracking cache for any session
- **Interrupt**: Send an interrupt signal to a session
- **Auto-Discovery**: Automatically detects client names (VS Code, Claude Desktop, Cursor, etc.)
- **Session Count Badge**: Icon badge shows number of active sessions

## Dependencies

- `pystray` — System tray icon and menus
- `Pillow` — Icon generation
- `tkinter` — Standard library, used for clipboard operations
