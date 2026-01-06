# Lineage MCP - LLM Quick Reference Guide

> **⚠️ CRITICAL FOR LLM AGENTS**: This MCP server provides file operations with **line-level change detection** and **instruction file auto-discovery**. Three critical patterns: (1) Session continuation uses `new_session=True` to reset caches, (2) All paths are relative to BASE_DIR, (3) Instruction files (AGENTS.md, CLAUDE.md) auto-discover from parent directories and append to responses.

## 🎯 Quick Start / Essential Patterns

### Essential Commands

```bash
# Run tests
python -m pytest tests/ -v

# Run server locally (stdio transport)
python lineage.py /path/to/base/dir

# Run with Docker
docker build -t lineage-mcp .
docker run -v /your/workspace:/data lineage-mcp

# Generate example responses
python tests/generate_examples.py
```

### Core Architecture Pattern

```python
# ALL tools follow this pattern:
# 1. Resolve path securely (blocks directory traversal)
# 2. Perform operation
# 3. Track file state for change detection
# 4. Append [CHANGED_FILES] section if changes detected
# 5. Discover & append instruction files from parents

@mcp.tool()
async def read(file_path: str, new_session: bool = False) -> str:
    if new_session:
        session.clear()  # Reset ALL caches

    result = resolve_path(file_path)  # Secure path resolution
    if not result.success:
        return result.error

    content = result.path.read_text(encoding='utf-8')
    session.track_file(str(result.path), mtime, content)

    # Append [CHANGED_FILES] + instruction file sections
    return content + format_changed_files_section() + instruction_files
```

### "Do This, Not That" Table

| ✅ DO                                                                | ❌ DON'T                                           |
| ------------------------------------------------------------------- | ------------------------------------------------- |
| Use `resolve_path()` for all path operations                        | Concatenate paths directly                        |
| Pass relative paths (e.g., `src/app/file.ts`)                       | Use absolute paths or backslashes                 |
| Use `new_session=True` on first read after restart                  | Forget to set `new_session=True` after compaction |
| Check `result.success` before operations                            | Skip security validation                          |
| Store mtime in milliseconds via `int(stat.st_mtime_ns / 1_000_000)` | Use float or seconds                              |
| Use `encoding='utf-8'` on all file operations                       | Rely on system default encoding                   |
| Use offset/limit for large files                                    | Read entire multi-MB files without chunking       |
| Use `replace_all=True` when replacing multiple occurrences          | Fail on ambiguous string replacements             |

## 📁 Critical File Reference

| File                   | Purpose                            | Key Features                                                           |
| ---------------------- | ---------------------------------- | ---------------------------------------------------------------------- |
| `lineage.py`           | Main entry point (~140 lines)      | FastMCP server, 6 tool registrations, async/await patterns             |
| `config.py`            | Configuration loading (~50 lines)  | Loads `appsettings.json`, instruction file names, sensible defaults    |
| `session_state.py`     | Session caches (~80 lines)         | `SessionState` dataclass: `mtimes`, `contents`, `provided_folders`     |
| `path_utils.py`        | Path security (~100 lines)         | `PathResult` dataclass, `resolve_path()` blocks directory traversal    |
| `file_watcher.py`      | Change detection (~130 lines)      | `calculate_changed_line_ranges()` using difflib, line-level diffs      |
| `instruction_files.py` | Instruction discovery (~120 lines) | `find_instruction_files_in_parents()`, caching with `provided_folders` |
| `tools/`               | Tool modules                       | One file per tool (read, write, edit, list, search, delete)            |
| `appsettings.json`     | Configuration                      | `instructionFileNames` array for instruction file priority             |

### Directory Structure

```
lineage-mcp/
├── lineage.py              # Entry point + MCP tool registrations
├── config.py               # Configuration loading
├── session_state.py        # Session-scoped caches
├── path_utils.py           # Path resolution + security
├── file_watcher.py         # Change detection logic
├── instruction_files.py    # Instruction file discovery
├── tools/                  # Individual tool modules
│   ├── __init__.py
│   ├── read_file.py
│   ├── write_file.py
│   ├── edit_file.py
│   ├── search_files.py
│   ├── list_files.py
│   └── delete_file.py
├── appsettings.json        # Configuration
├── tests/                  # Test suite
│   ├── conftest.py
│   ├── test_*.py
│   └── generate_examples.py
├── Dockerfile              # Container config
├── docker-compose.yml      # Orchestration
└── requirements.txt        # Python deps
```

## 🏛️ MCP Server Patterns

### Session Management: new_session Pattern

**🛑 STOP AND CHECK before calling any lineage tool:**

Can you see the FULL output of a previous lineage tool call you made in this conversation (not a summary)?
- **NO or UNSURE** → `new_session=True` is REQUIRED
- **YES, I see complete previous output** → `new_session=False` is fine

Missing this = missing AGENTS.md instruction files. When in doubt, always use `new_session=True` - it's safe.

```python
# If you can't see full output of a previous lineage call, use new_session=True
# Can be used on ANY tool:
list(path="", new_session=True)
search(pattern="**/*.py", new_session=True)
read(file_path="src/app/page.tsx", new_session=True)

# After that, subsequent calls reuse caches (for change detection)
read(file_path="src/app/layout.tsx")  # new_session=False (default)

# Alternative: If you forgot new_session=True, use clear()
clear()  # Resets all caches - instruction files will re-appear on next read
```

**Why this matters**: When conversation context is compacted, you lose the detailed content from instruction files, but the server cache still thinks they were provided. Setting `new_session=True` or calling `clear()` resets the server cache so instruction files are re-appended to responses.

### Session-Scoped State (SessionState dataclass)

```python
@dataclass
class SessionState:
    mtimes: dict[str, int] = field(default_factory=dict)           # {path: mtime_ms}
    contents: dict[str, str] = field(default_factory=dict)         # {path: content}
    provided_folders: set[str] = field(default_factory=set)        # Folders already shown

    def track_file(self, path: str, mtime: int, content: str) -> None: ...
    def untrack_file(self, path: str) -> None: ...
    def mark_folder_provided(self, folder: str) -> None: ...
    def is_folder_provided(self, folder: str) -> bool: ...
    def clear(self) -> None: ...

session = SessionState()  # Module-level singleton
```

### Secure Path Resolution Pattern

```python
# ALL paths are relative to base directory
# resolve_path() enforces this security boundary
result = resolve_path("src/app/file.ts")  # ✅ Allowed
result = resolve_path("../other/file.ts")  # ✅ Allowed (still within base dir)
result = resolve_path("/etc/passwd")  # ❌ Blocked (outside base dir)

# Pattern: Always check result.success
if not result.success:
    return result.error  # Return error message
file_path = result.path  # Use resolved Path object
```

### Change Detection Pattern

Files you read are automatically tracked for changes. When you read again, lineage detects external modifications.

```python
# First read tracks the file
content1 = read("myfile.txt")
# Output: [file content]

# (Someone externally modifies myfile.txt)

# Second read detects the change and reports it
content2 = read("myfile.txt")
# Output: [file content]\n\n[CHANGED_FILES]\n- /path/to/myfile.txt (modified): lines 5-8 (2.34s ago)
```

**How it works**:
- `session.track_file()` stores mtime (ms) and content for every read/write/edit
- `format_changed_files_section()` compares current vs cached mtime + content
- Uses `difflib.unified_diff()` to calculate line ranges that changed
- Reports as `"5-8,15-20"` meaning lines 5-8 and 15-20 changed

### Line-Level Diff Detection

```python
def calculate_changed_line_ranges(old_content: str, new_content: str) -> str:
    """Uses difflib.unified_diff to find exact changed lines.

    Returns:
        "2-7"     - Specific line range changed
        "3,8-12"  - Multiple ranges
        "1-EOF"   - Fallback if diff fails
    """
    diff = list(unified_diff(old_lines, new_lines, lineterm='', n=0))
    # Parse @@ markers to extract line numbers
```

### Instruction File Discovery Pattern

Instruction files (AGENTS.md, CLAUDE.md) auto-discover from parent directories.

```python
# When reading src/app/page.tsx, lineage walks up directory tree:
# src/app/page.tsx (target file)
# → src/app/AGENTS.md? (found!) → include it
# → src/AGENTS.md? (found!) → include it
# → AGENTS.md? (stop at BASE_DIR - excluded)

# Pattern: Instruction files only included once per folder per session
# SessionState.provided_folders tracks which folders already provided
```

**Configuration** via `appsettings.json`:
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

The server looks for instruction files in **priority order**. For each folder, only the **first matching file** is included.

### MCP Tools Available

| Tool                                                                | Purpose                     | Returns                                        |
| ------------------------------------------------------------------- | --------------------------- | ---------------------------------------------- |
| `list(path, new_session)`                                           | Directory listing           | Markdown table + [CHANGED_FILES]               |
| `read(file_path, new_session, show_line_numbers, offset, limit)`    | Read file (full or partial) | Content + [CHANGED_FILES] + [INSTRUCTION_FILE] |
| `write(file_path, content, new_session)`                            | Write file                  | Success/error message                          |
| `edit(file_path, old_string, new_string, replace_all, new_session)` | Edit file                   | Success/error message                          |
| `search(pattern, path, new_session)`                                | Search by pattern           | File list + [CHANGED_FILES]                    |
| `delete(file_path, new_session)`                                    | Delete file/dir             | Success/error message                          |
| `clear()`                                                           | Clear all session caches    | Success message                                |

### Offset/Limit Pattern for Large Files

```python
# Read large files in chunks to avoid token usage
read("huge_file.csv", offset=0, limit=100)      # Lines 1-100
read("huge_file.csv", offset=100, limit=100)    # Lines 101-200
read("huge_file.csv", offset=200, limit=None)   # Lines 201-EOF

# With line numbers for navigation
read("types.gen.ts", offset=100, limit=50, show_line_numbers=True)
# Returns:
# 101→export type Foo = ...
# 102→export type Bar = ...
```

### Edit Pattern with replace_all

```python
# Single replacement (default)
edit("file.txt", "old", "new")  # Error if "old" appears multiple times
# Output: "Error: String found 5 times. Use replace_all=True..."

# Multiple replacement
edit("file.txt", "old", "new", replace_all=True)
# Output: "Successfully replaced 5 occurrence(s) in file.txt"

# Pattern: Be specific with old_string to avoid needing replace_all
```

## 🚨 Best Practices & Common Pitfalls

### Critical Rules

| Rule                  | Details                                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **new_session**       | MUST be True on first lineage tool call after session continuation. Only once per session restart. Can be used on any tool. |
| **Relative paths**    | ALL paths must be relative to BASE_DIR. No backslashes on Windows.                                                          |
| **Path resolution**   | Always check `result.success` before using `result.path`.                                                                   |
| **Instruction files** | They auto-append. Don't manually copy content unless overriding.                                                            |
| **Change detection**  | Only reports changes since last read of that file. External edits only.                                                     |
| **Large files**       | Use offset/limit to read in chunks. Never read multi-MB files all at once.                                                  |
| **String matching**   | Edit requires exact match including whitespace. Use raw strings if needed.                                                  |

### Common Pitfalls

| ❌ Pitfall                                                | ✅ Fix                                                                             |
| -------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Forgetting `new_session=True` after compaction           | First lineage tool call after restart: always set `new_session=True`              |
| Using absolute paths like `/home/user/file.txt`          | Use relative: `file.txt` or `src/app/file.ts`                                     |
| Backslashes on Windows paths                             | Use forward slashes: `src/app/file.ts` not `src\app\file.ts`                      |
| Reading entire multi-MB files                            | Use offset/limit to paginate                                                      |
| Ambiguous string replacements failing                    | Either make old_string more specific, or use `replace_all=True`                   |
| Instruction files not appearing                          | Check `appsettings.json`. Folder must have AGENTS.md or configured name.          |
| Edited files showing as changed next read                | Expected - LLM edits are tracked. External edits after your edit show as changed. |
| Not populating `session.contents` before expecting diffs | Cache content in session for accurate line-level diffs                            |
| Forgetting `time.sleep(0.1)` between writes when testing | Need delay for mtime changes to register                                          |

### File-Scoped Operations

All operations are file-scoped (no full repo operations):

```python
# ✅ Supported operations
read("src/app/page.tsx")
edit("src/app/page.tsx", "old", "new")
write("src/app/new-file.ts", "content")
search("**/*.tsx")
list("src/app")

# ❌ Operations that don't exist
# - "rebuild entire project" - use external script
# - "format all files" - use external tool
# - "delete directory recursively" - delete only supports empty dirs
```

### Security Rules

- **ALWAYS** use `resolve_path()` which validates paths start with BASE_DIR
- **NEVER** allow `..` traversal outside BASE_DIR
- All path operations use `pathlib.Path` for consistent behavior

### Change Detection Rules

- Track mtime in **milliseconds** (via `int(stat.st_mtime_ns / 1_000_000)`)
- Cache **content** in `session.contents` for accurate line-level diffs
- First read of a file won't have previous content → returns `"1-EOF"`
- **[CHANGED_FILES] only reports EXTERNAL changes** - edits made via `edit()` or `write()` update the cache
- **All 6 tools include [CHANGED_FILES]** in their response when external changes are detected
- **Changes are only reported once** - after showing a change, the cache is updated

### Instruction File Rules

- Looked up from `appsettings.json` `instructionFileNames` property (defaults to `["AGENTS.md"]`)
- Only include instruction files **between** target and BASE_DIR
- **Exclude** instruction files at BASE_DIR itself
- For each folder, checks files in **priority order** and includes only the **first one found**
- **Folder-based tracking**: `session.provided_folders` is a set of folder paths (not file paths)
- **Once a folder is provided, never shown again** in the same session
- **Only `new_session=True` resets** the cache to force re-reading all instruction files

### When Stuck

1. **Path errors**: Check relative path is within BASE_DIR. Use forward slashes. No absolute paths.
2. **File not found after write**: Write returns success, but file may not exist if parent dir missing.
3. **String replacement ambiguous**: Make old_string more unique. Add surrounding context.
4. **Instruction files not showing**: Check folder hierarchy. Lineage walks UP from file location to BASE_DIR.
5. **Change detection missing**: Only tracks files you've read. Read it again to check for changes.
6. **Session state lost after compaction**: Always use `new_session=True` on first read after restart.

### Testing Pattern

```python
# Always mock BASE_DIR when testing
import path_utils
old_base_dir = path_utils._base_dir
path_utils._base_dir = tmpdir_path
try:
    # Test code here
finally:
    path_utils._base_dir = old_base_dir
```

## 🔗 Related Documentation

- [MCP Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://github.com/modelcontextprotocol/python-sdk#fastmcp)

---

> **🤖 LLM NOTE**: This server runs in Docker with `/data` as the mount point. All 6 tools (list, read, write, edit, search, delete) include security validation via `resolve_path()`. The line-level diff uses Python's `difflib`, and search uses Python's `glob`. Session continuations are critical - always start with `new_session=True` after any session restart or context compaction.

---

When the task requires multiple steps or non-trivial changes, present a detailed plan using #planReview and wait for approval before executing.
If the plan is rejected, incorporate the comments and submit an updated plan with #planReview.
When the user asks for a step-by-step guide or walkthrough, present it using #walkthroughReview.
Always use #askUser before completing any task to confirm the result matches what the user asked for.
