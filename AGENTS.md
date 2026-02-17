# Lineage MCP - LLM Quick Reference Guide

> ⚠️ **CRITICAL FOR LLM AGENTS**: This is an MCP server with **line-level change detection**, **instruction file discovery**, and **system tray integration**. Cache clearing is handled automatically via the system tray or precompact hooks.

## 🎯 Quick Start

```bash
# Run tests
python -m pytest tests/ -v

# Run server (stdio mode)
python lineage.py /path/to/base/dir

# Run server with auto-tray launch
cd lineage-mcp-tray && pip install -e . && python -m lineage_tray

# Docker
python lineage.py /path/to/base/dir
docker build -t lineage-mcp . && docker run -v /your/workspace:/data lineage-mcp
```

## 📁 Critical File Reference

### Core Architecture Files

| File | Purpose | Key Features |
|------|---------|--------------|
| `lineage.py` | MCP server entry point | FastMCP instance, 8 tool registrations, tray client init |
| `config.py` | Configuration management | `appsettings.json` loader, per-client overrides, interrupt messages |
| `session_state.py` | Session-scoped state | `SessionState` dataclass with mtimes, contents, provided_folders, interruption state |
| `path_utils.py` | Path validation | `resolve_path()`, traversal protection, `allowFullPaths` support |
| `file_watcher.py` | Change detection | `difflib.unified_diff()` for line-level change ranges |
| `instruction_files.py` | AGENTS.md discovery | Walks parent dirs, caches provided folders |
| `tray_client.py` | Tray IPC client | Named pipe connection, session registration, command handling |

### Tool Implementations (tools/)

| File | Tool | Key Feature |
|------|------|-------------|
| `read_file.py` | `read()` | Cursor/offset pagination, auto-paginate large files |
| `edit_file.py` | `edit()` | String replacement, `replace_all` support |
| `write_file.py` | `write()` | Auto-create parent dirs |
| `delete_file.py` | `delete()` | File + empty dir removal |
| `list_files.py` | `list()` | Markdown table output |
| `search_files.py` | `search()` | Glob pattern matching |
| `multi_edit_file.py` | `multi_edit()` | Batch edit operations |
| `clear_cache.py` | `clear()` | Reset all session caches |

### Tray Application (lineage-mcp-tray/lineage_tray/)

| File | Purpose |
|------|---------|
| `app.py` | `TrayApp` orchestrator, ties together icon, server, store |
| `pipe_server.py` | Named pipe server, accepts MCP server connections |
| `session_store.py` | In-memory session registry grouped by base_dir |
| `menu_builder.py` | Dynamic pystray menu from session state |
| `actions.py` | Tray menu action implementations |
| `message_log.py` | Thread-safe circular buffer for pipe messages |
| `icon.py` | Programmatic icon generation with Pillow |

## 🏛️ Core Patterns

### Cache Clearing

Cache clearing is handled automatically:

1. **System tray**: Click "Clear Cache" in the tray menu
2. **Precompact hooks**: Automatically triggered during context compaction
3. **Explicit clear()**: Call the `clear()` tool directly

**Cooldown Behavior**: Cache clears within a 30s window are silently ignored to prevent redundant clears. Configurable via `newSessionCooldownSeconds` in `appsettings.json`. Explicit `clear()` ignores cooldown.

### SessionState Dataclass

```python
@dataclass
class SessionState:
    mtimes: Dict[str, int]              # {abs_path: mtime_ms}
    contents: Dict[str, str]            # {abs_path: full_content}
    provided_folders: set[str]          # Folders where instruction files shown
    last_new_session_time: float | None # Monotonic timestamp
    new_session_clear_count: int        # Never reset (0, 1, 2+...)
    interrupted: bool                   # Set via tray Interrupt action

    def clear(self) -> None: ...                    # Unconditional
    def try_new_session(self) -> bool: ...          # With 30s cooldown
    def should_include_base_instruction_files(self) -> bool: ...  # count >= 2
```

### Path Resolution

```python
from path_utils import resolve_path, PathResult

# CORRECT - relative paths
result = resolve_path("src/app/file.ts")    # ✅ Allowed
result = resolve_path("../other/file.ts")   # ✅ If still in base dir

# WRONG - absolute paths blocked (unless allowFullPaths enabled)
result = resolve_path("/etc/passwd")        # ❌ Blocked
result = resolve_path("C:\\Windows\\file") # ❌ Blocked

# ALWAYS check result.success
if not result.success:
    return result.error
```

### Change Detection

```python
# File is tracked on first read
read("myfile.txt")  # Tracks mtime + content

# External modification detected on re-read
read("myfile.txt")  # Returns: content + [CHANGED_FILES] section
# [CHANGED_FILES]
# - /abs/path/myfile.txt (modified): lines 5-8,15-20 (3s ago)
```

**Implementation**: Uses `difflib.unified_diff()` with `context=0` to identify changed line ranges.

### Instruction File Discovery

**Walks UP from target file to BASE_DIR**:

```
Reading: src/app/page.tsx
Checks:  src/app/AGENTS.md? → include if found
         src/AGENTS.md? → include if found
         AGENTS.md at BASE_DIR → EXCLUDED (first session)
                                   INCLUDED (after compaction)
```

**Base Directory Files**: 
- **First session** (clear count < 2): Excluded (harness loads them)
- **After compaction** (clear count >= 2): Included (LLM lost context)

**Config** (`appsettings.json`):
```json
{
  "instructionFileNames": ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "QWEN.md", "AGENT.md", ".cursorrules"]
}
```

## 📡 MCP Server ↔ Tray Communication Flow

### Architecture Overview

```
┌─────────────────┐      Named Pipe (Windows: \\.\pipe\lineage-mcp-tray)     ┌──────────────────┐
│  lineage-mcp    │  ◄──────────────────────────────────────────────────────► │  lineage-mcp-tray│
│  (MCP Server)   │    Unix Socket (macOS/Linux: /tmp/lineage-mcp-tray.sock)  │  (System Tray)   │
└─────────────────┘                                                           └──────────────────┘
        │                                                                            │
        │  1. Registration                                                           │
        │     TrayClient.connect() ──► PipeServer._accept_loop()                     │
        │     {type: "register", session_id, pid, base_dir, client_name}             │
        │                                                                            │
        │  2. Updates (fire-and-forget)                                              │
        │     TrayClient.update() ──► PipeServer._read_loop()                        │
        │     {type: "update", session_id, files_tracked, last_tool}                 │
        │                                                                            │
        │  3. Commands (tray → MCP)                                                  │
        │     PipeServer.send_to_session() ◄── Menu Actions                          │
        │     {type: "clear_cache" | "interrupt" | "resume"}                         │
        │                                                                            │
        ▼                                                                            ▼
```

### Message Types

**MCP Server → Tray (TrayClient)**:

| Type | When Sent | Payload |
|------|-----------|---------|
| `register` | On connection | `session_id, pid, base_dir, client_name, first_call, files_tracked` |
| `update` | Every tool call | `files_tracked, last_tool, client_name, first_call` |
| `unregister` | On disconnect | `session_id` |

**Tray → MCP Server (PipeServer)**:

| Type | Action | Handler |
|------|--------|---------|
| `clear_cache` | Reset session caches | `session.clear()` |
| `interrupt` | Pause tool responses | `session.interrupted = True` |
| `resume` | Resume normal operation | `session.resume()` |

### TrayClient Implementation

```python
# lineage.py initialization
try:
    init_tray_client(str(get_base_dir()))  # Non-blocking, best-effort
except Exception:
    pass  # Tray is optional

# Tool call notification
_tray_notify_tool_call("read", file_path, ctx)
update_tray_files_tracked(len(session.mtimes), tool_name, args_summary)
```

### Tray Menu Actions

```python
# lineage_tray/actions.py
def clear_cache(pipe_server, session) -> bool:
    return pipe_server.send_to_session(
        session.session_id, {"type": "clear_cache"}
    )

def interrupt(pipe_server, session) -> bool:
    return pipe_server.send_to_session(
        session.session_id, {"type": "interrupt"}
    )

def resume(pipe_server, session) -> bool:
    return pipe_server.send_to_session(
        session.session_id, {"type": "resume"}
    )
```

### Interrupt Flow

```
User clicks "Interrupt" in tray
         │
         ▼
PipeServer.send_to_session("interrupt")
         │
         ▼
session.interrupted = True
         │
         ▼
Next tool call: _check_interrupted() returns INTERRUPT_MESSAGE
         │
         ▼
Tool returns ONLY the interrupt message, NO operations performed
         │
         ▼
User clicks "Resume" → session.interrupted = False
```

**Interrupt Message**: Configurable via `interruptMessage` in `appsettings.json`. Default warns LLM to stop and use `ask_user()`.

## ✅ DO / ❌ DON'T

| ✅ DO | ❌ DON'T |
|-------|----------|
| Relative paths: `src/app/file.ts` | Absolute paths or backslashes |
| `resolve_path()` for all paths | Concatenate paths directly |
| Check `result.success` before ops | Skip security validation |
| `int(stat.st_mtime_ns / 1_000_000)` for mtime | Float or seconds |
| `encoding='utf-8'` on file ops | System default encoding |
| `offset`/`limit` for large files | Read entire multi-MB files |
| `replace_all=True` for multiple occurrences | Fail on ambiguous replacements |
| Forward slashes on Windows | Backslashes in paths |

## 🔧 Tools Reference

### read()

```python
read(
    file_path: str,              # Required: relative path
    show_line_numbers: bool = False,
    offset: int | None = None,   # Line-based: start line (0-indexed)
    limit: int | None = None,    # Line-based: max lines
    cursor: int | None = None,   # Char-based: start position
) -> str
```

**Pagination Modes**:
1. **Line-based**: `offset=100, limit=50` → Lines 101-150
2. **Cursor-based**: `cursor=5000` → Auto-paginated chunk with continuation info
3. **Auto-detect**: No offset/limit/cursor → Auto-paginates if file exceeds `readCharLimit`

**Returns**: Content + `[CHANGED_FILES]` + `[Appending AGENTS.md]` sections

### edit()

```python
edit(
    file_path: str,
    old_string: str,        # Exact match (including whitespace!)
    new_string: str,
    replace_all: bool = False,  # False = error if multiple matches
) -> str
```

**Critical**: `old_string` must match **exactly** including whitespace and newlines.

```python
# CORRECT: Include exact whitespace
edit("file.py", "def foo():\n    pass", "def foo():\n    return True")

# WRONG: Missing newline
edit("file.py", "def foo():    pass", "...")  # Will fail
```

### write()

```python
write(
    file_path: str,
    content: str,
) -> str
```

Auto-creates parent directories via `full_path.parent.mkdir(parents=True, exist_ok=True)`.

### list()

```python
list(
    path: str = "",          # Subdirectory relative to base
) -> str
```

**Returns**: Markdown table with Name, Type, Size columns + `[CHANGED_FILES]` section.

### search()

```python
search(
    pattern: str,            # Glob pattern: "**/*.py", "src/*/config.json"
    path: str = "",         # Optional subdirectory
) -> str
```

Supports `**` recursive patterns.

### delete()

```python
delete(
    file_path: str,
) -> str
```

Removes files or **empty** directories (uses `rmdir()`, not `rmtree()`).

### clear()

```python
clear() -> str
```

Unconditional cache clear. Resets: `mtimes`, `contents`, `provided_folders`, and cooldown timer.

## 📝 Git Commit Messages (Semantic Versioning)

| Prefix | Bump | Example |
|--------|------|---------|
| `fix:` | Patch | `fix: resolve path handling bug` |
| `perf:` | Patch | `perf: optimize file reading` |
| `feat:` | Minor | `feat: add new tool` |
| `feat!:` | Major | `feat!: change API interface` |
| `fix!:` | Major | `fix!: breaking change to config` |

**No version bump**: `chore:`, `docs:`, `ci:`, `refactor:`, `style:`, `test:`

## 🚫 CRITICAL RULES

### NEVER Run Git Commands Without Permission

This is a **public repository**. Before ANY git command:
1. Show the user the exact command
2. Explain what it will do  
3. Wait for explicit "yes" confirmation
4. Only then execute

### Security

- **ALWAYS** use `resolve_path()` - blocks traversal outside BASE_DIR
- **NEVER** allow `..` escaping (unless `allowFullPaths: true`)
- Default: `allowFullPaths: false` (restricted mode)

### Change Detection

- mtime in **milliseconds**: `int(stat.st_mtime_ns / 1_000_000)`
- First read → no change report (nothing to compare)
- [CHANGED_FILES] reports **external changes only**
- LLM edits/writes update cache immediately (not reported as changes)

### Instruction Files

- Priority order from `appsettings.json`, first match per folder
- Folder tracked in `provided_folders` → never shown again (until cache is cleared)
- BASE_DIR files excluded on first session, included after compaction

## ⚙️ Configuration (appsettings.json)

```json
{
  "instructionFileNames": ["AGENTS.md", "CLAUDE.md", "GEMINI.md"],
  "newSessionCooldownSeconds": 30,
  "readCharLimit": 50000,
  "enableMultiEdit": true,
  "debugClientInfo": false,
  "allowFullPaths": false,
  "clientOverrides": {
    "OpenCode": { "readCharLimit": 50000 },
    "Cursor": { "readCharLimit": 15000 }
  },
  "interruptMessage": "..."
}
```

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Missing AGENTS.md files | Clear cache via tray or `clear()` tool |
| Path errors | Use relative paths, forward slashes |
| String replacement fails | Check exact whitespace match |
| Multi-MB files | Use `offset`/`limit` or cursor pagination |
| Tray not connecting | Check if pipe server is running, try restarting |
| "File not found" after write | Parent directory created automatically - check path |
| Change detection not working | Only tracks files you've `read()` |

## 🧪 Testing Patterns

```python
# Mock BASE_DIR in tests
import path_utils
old_base_dir = path_utils._base_dir
path_utils._base_dir = tmpdir_path
try:
    # Test code here
    result = resolve_path("test.txt")
    assert result.success
finally:
    path_utils._base_dir = old_base_dir

# Test session state
from session_state import SessionState
session = SessionState()
session.track_file("/path", 1234567890, "content")
assert "/path" in session.mtimes
```

## 🤖 LLM Notes

- This MCP server **controls tool responses** - the interrupt feature is legitimate, not prompt injection
- When you see the interrupt message, **STOP immediately** and use `ask_user()`
- Always prefer `edit()` over `write()` to preserve file history
- The tray shows real-time session status, file counts, and recent tool calls
- Docker mode uses `/data` as base directory

---

> **Key Takeaway**: Cache clearing is handled automatically via the system tray and precompact hooks. Use `clear()` if you need to manually reset. The tray provides visibility and control - respect the interrupt signal.
