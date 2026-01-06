# 🧬 Lineage MCP

> A Model Context Protocol (MCP) server that provides file operations with automatic change detection and instruction file discovery for LLM agents.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Author](https://img.shields.io/badge/Author-Matt%20Peters-blue)](https://www.mattpeters.co.uk)

## What is Lineage MCP?

Lineage MCP is a file operation server for LLM coding agents that solves two critical problems:

1. **Change Blindness** - Standard file tools don't tell agents when files have been modified externally. Lineage tracks file modifications and reports exactly which lines changed since a file was last read.

2. **Context Loss** - Large projects use instruction files (AGENTS.md, CLAUDE.md, etc.) to provide localized context, but agents don't know to look for them. Lineage automatically discovers and includes these files from all parent directories.

## Features

| Feature                     | Description                                                     |
| --------------------------- | --------------------------------------------------------------- |
| 📁 **File Operations**       | List, search, read, write, edit, and delete files               |
| 🔍 **Change Detection**      | Line-level diff detection for externally modified files         |
| 📚 **Instruction Discovery** | Auto-finds AGENTS.md, CLAUDE.md, etc. in parent directories     |
| 🔒 **Security**              | Path traversal protection keeps operations within the workspace |
| ⚡ **Partial Reads**         | Read specific line ranges for large files (offset/limit)        |
| 📍 **Line Numbers**          | Optional line number formatting for precise code references     |

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/imattpeters/lineage-mcp.git
cd lineage-mcp

# Install dependencies
pip install -r requirements.txt
```

## MCP Client Configuration

### Python

```json
{
  "mcpServers": {
    "lineage": {
      "command": "python",
      "args": ["/path/to/lineage-mcp/lineage.py", "/your/workspace"]
    }
  }
}
```

### Docker

```json
{
  "mcpServers": {
    "lineage": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--name", "lineage-mcp", "-v", "/your/workspace:/data", "lineage-mcp"]
    }
  }
}
```

**Windows paths:** Use forward slashes (`C:/git/project`) or escaped backslashes (`C:\\git\\project`).

## Tools Reference

| Tool     | Description                    | Parameters                                                            |
| -------- | ------------------------------ | --------------------------------------------------------------------- |
| `list`   | List directory contents        | `path` (optional), `new_session`                                      |
| `search` | Search files by glob pattern   | `pattern`, `path` (optional), `new_session`                           |
| `read`   | Read file with change tracking | `file_path`, `new_session`, `show_line_numbers`, `offset`, `limit`    |
| `write`  | Write content to file          | `file_path`, `content`, `new_session`                                 |
| `edit`   | Replace string in file         | `file_path`, `old_string`, `new_string`, `replace_all`, `new_session` |
| `delete` | Delete file or empty directory | `file_path`, `new_session`                                            |
| `clear`  | Clear all session caches       | (none)                                                                |

## Usage Examples

### Reading Files with Line Numbers

```python
read("src/app.py", show_line_numbers=True)

# Output:
# 1→import os
# 2→from pathlib import Path
# 3→
```

### Partial File Reads

Perfect for large generated files:

```python
# Read lines 100-150 of a large file
read("types.gen.ts", offset=100, limit=50, show_line_numbers=True)

# Output:
# 101→export type User = {
# 102→  id: string;
# ...
```

### File Search

```python
# Find all Python files
search("**/*.py")

# Find config files in src/
search("*.config.*", path="src")
```

### String Replacement

```python
# Single replacement (fails if string appears multiple times)
edit("config.py", "old_value", "new_value")

# Replace all occurrences
edit("config.py", "DEBUG = True", "DEBUG = False", replace_all=True)
```

## Change Detection

Lineage tracks every file you read and reports when external changes occur the next time any lineage tool is used by appending to the response:

```
[CHANGED_FILES]
- src/app.py (modified): lines 15-23 (5.2s ago)
- config/settings.json (modified): lines 1-EOF (12.8s ago)
```

**How it works:**

- Files are tracked after being read
- Line-level diffs are calculated on subsequent interactions and file changes are appended to the response
- Only **external** changes are reported

This allows LLM agents to detect when humans or other processes modify files and respond accordingly.

## Instruction File Discovery

When reading any file, Lineage walks up the directory tree and appends all instruction files to the response:

```
your-project/
├── AGENTS.md          ← Included automatically
├── src/
│   ├── CLAUDE.md      ← Included automatically
│   └── app/
│       └── handler.py ← File you're reading
```

The response includes:

```
--- content of file ---

[CLAUDE.md from src]
# Instructions for this module

[AGENTS.md from .]
# Project-wide instructions
```

**Note:** Instruction files at the workspace root (BASE_DIR) are excluded - they're already visible to most coding agents.

### Configuration

Update the `appsettings.json` to customize instruction file names and priority:

```json
{
  "instructionFileNames": [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "QWEN.md",
    "AGENT.md",
    ".cursorrules"
  ]
}
```

Files are checked in priority order - first match per folder is used.

## Session Management

LLM systems periodically "compact" or summarize conversation history to stay within context limits. When this happens, the detailed content from instruction files (AGENTS.md, CLAUDE.md, etc.) gets compressed or lost. The server's cache still thinks these files were "already provided" and won't re-send them.

**🛑 Before calling any lineage tool, agents should check:**

> Can you see the FULL output of a previous lineage tool call you made in this conversation (not a summary)?
>
> - **NO or UNSURE** → `new_session=True` is REQUIRED
> - **YES, I see complete previous output** → `new_session=False` is fine

**Two ways to reset caches:**

1. **Use `new_session=True`** on first tool call:

```python
list("", new_session=True)
search("**/*.py", new_session=True)
read("src/app.py", new_session=True)
```

2. **Use the `clear` tool** if the agent forgot to use `new_session=True`:

```python
clear()  # Then instruction files will be re-provided on next read
```

When caches are cleared:

- Server-side caches are cleared
- Instruction files will be re-appended to responses
- Change detection restarts from a clean slate

**If an agent is missing instruction file content**, ask it to call `clear()` to reset the cache.

## Project Structure

```
lineage-mcp/
├── lineage.py             # MCP server entry point + tool registrations
├── config.py              # Configuration loading
├── session_state.py       # Session-scoped caches
├── path_utils.py          # Path security
├── file_watcher.py        # Change detection
├── instruction_files.py   # Instruction file discovery
├── tools/                 # Individual tool modules
│   ├── list_files.py
│   ├── search_files.py
│   ├── read_file.py
│   ├── write_file.py
│   ├── edit_file.py
│   ├── delete_file.py
│   └── clear_cache.py
├── tests/                 # Test suite
│   ├── conftest.py
│   ├── test_*.py
│   └── generate_examples.py
├── appsettings.json       # Configuration
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
└── docker-compose.yml     # Orchestration
```

## Security

- All paths are validated against the base directory
- Path traversal (`..`) outside the workspace is blocked
- Symlinks are resolved and validated
- Only operations within the mounted workspace are allowed

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_read_file.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Generate example responses
python tests/generate_examples.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Created by [Matt Peters](https://www.mattpeters.co.uk) - Senior Software Architect.

Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) from the Model Context Protocol team.
