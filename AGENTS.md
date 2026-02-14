# Lineage MCP - LLM Reference

> ⚠️ **CRITICAL**: File ops with **line-level change detection** + **instruction file auto-discovery**. Three patterns: (1) `new_session=True` on first call after compaction, (2) All paths relative to BASE_DIR, (3) Instruction files auto-append from parent dirs.

## 🚫 GIT COMMANDS - CRITICAL RULE

**NEVER run git commands (commit, push, tag, reset, etc.) without explicit user permission.**

This is a public repository. Before running ANY git command, you MUST:
1. Show the user exactly what command you plan to run
2. Explain what it will do
3. Wait for explicit "yes" confirmation
4. Only then execute the command

Violations of this rule can expose private information or corrupt public history.

## 📝 Git Commit Message Format (Semantic Versioning)

This project uses **python-semantic-release** for automatic versioning. Commit messages determine version bumps:

| Prefix | Version Bump | Example |
|--------|--------------|---------|
| `fix:` | Patch (1.0.0 → 1.0.1) | `fix: resolve path handling bug` |
| `perf:` | Patch (1.0.0 → 1.0.1) | `perf: optimize file reading` |
| `feat:` | Minor (1.0.0 → 1.1.0) | `feat: add new search tool` |
| `feat!:` | Major (1.0.0 → 2.0.0) | `feat!: change API interface` |
| `fix!:` | Major (1.0.0 → 2.0.0) | `fix!: breaking change to config` |

**Non-version commits (no version bump):**
- `chore:` - maintenance tasks
- `docs:` - documentation only
- `ci:` - CI/CD changes
- `refactor:` - code refactoring
- `style:` - formatting, whitespace
- `test:` - adding/updating tests

**With scope (optional):**
- `fix(path): resolve traversal issue`
- `feat(tools): add partial read support`

**Breaking changes (use `!` or footer):**
- `feat!: new config format` OR
- ```
  feat: new config format

  BREAKING CHANGE: config.json replaced with appsettings.json
  ```

## 🎯 Quick Start

```bash
python -m pytest tests/ -v              # Run tests
python lineage.py /path/to/base/dir     # Run server (stdio)
docker build -t lineage-mcp . && docker run -v /your/workspace:/data lineage-mcp
```

## ✅ DO / ❌ DON'T

| ✅ DO                                          | ❌ DON'T                          |
| --------------------------------------------- | -------------------------------- |
| `resolve_path()` for all paths                | Concatenate paths directly       |
| Relative paths: `src/app/file.ts`             | Absolute paths or backslashes    |
| `new_session=True` first call after restart   | Forget → missing AGENTS.md files |
| Check `result.success` before ops             | Skip security validation         |
| `int(stat.st_mtime_ns / 1_000_000)` for mtime | Float or seconds                 |
| `encoding='utf-8'` on file ops                | System default encoding          |
| `offset`/`limit` for large files              | Read entire multi-MB files       |
| `replace_all=True` for multiple occurrences   | Fail on ambiguous replacements   |
| `allowFullPaths` to access paths outside base | Assume all paths are unrestricted|

## 📁 Files

| File                   | Purpose                                                     |
| ---------------------- | ----------------------------------------------------------- |
| `lineage.py`           | Entry point, FastMCP server, 8 tool registrations           |
| `config.py`            | Loads `appsettings.json`, instruction file names            |
| `session_state.py`     | `SessionState`: `mtimes`, `contents`, `provided_folders`    |
| `path_utils.py`        | `PathResult`, `resolve_path()` blocks traversal             |
| `file_watcher.py`      | `calculate_changed_line_ranges()` via difflib               |
| `instruction_files.py` | `find_instruction_files_in_parents()`, folder caching       |
| `tools/*.py`           | One file per tool (read, multi_read, write, edit, multi_edit, list, search, delete) |

## 🏛️ Core Patterns

### new_session Pattern

**🛑 Before ANY lineage call**: Can you see FULL output of a previous lineage call (not summary)?

- **NO/UNSURE** → `new_session=True` REQUIRED
- **YES** → `new_session=False` OK

**Missing this = missing AGENTS.md**. When in doubt, use `new_session=True`.

**⏱️ Cooldown**: When `new_session=True` clears caches, subsequent `new_session=True` calls within 30 seconds are silently ignored. This prevents redundant clears during the initial burst of tool calls. Configurable via `newSessionCooldownSeconds` in `appsettings.json`. Explicit `clear()` always works regardless of cooldown.

```python
# After restart/compaction - use on ANY tool:
list(path="", new_session=True)
read(file_path="src/app/page.tsx", new_session=True)

# Subsequent calls reuse caches:
read(file_path="src/app/layout.tsx")  # new_session=False default

# Alternative: forgot new_session? Use clear()
clear()  # Resets all caches (ignores cooldown)
```

### SessionState

```python
@dataclass
class SessionState:
    mtimes: dict[str, int]           # {path: mtime_ms}
    contents: dict[str, str]         # {path: content}
    provided_folders: set[str]       # Folders already shown
    last_new_session_time: float | None  # Monotonic timestamp of last clear
    new_session_clear_count: int     # Times caches were cleared (never reset)

    def clear(self) -> None: ...           # Unconditional clear (resets cooldown, increments count)
    def try_new_session(self) -> bool: ... # Clear with 30s cooldown (increments count if cleared)
    def should_include_base_instruction_files(self) -> bool: ...  # True when count >= 2
```

### Path Resolution

```python
result = resolve_path("src/app/file.ts")  # ✅ Allowed
result = resolve_path("../other/file.ts") # ✅ If still in base dir
result = resolve_path("/etc/passwd")      # ❌ Blocked

# ALWAYS check result.success
if not result.success:
    return result.error
```

### Change Detection

Files read are tracked. Re-reading detects external modifications:

```python
read("myfile.txt")  # Tracks file
# (External modification happens)
read("myfile.txt")  # Returns: content + [CHANGED_FILES] section with line ranges
```

Uses `difflib.unified_diff()` → reports `"5-8,15-20"` for changed lines.

### Instruction File Discovery

Walks up from target file to BASE_DIR, includes first matching file per folder:

```python
# Reading src/app/page.tsx checks:
# src/app/AGENTS.md? → include if found
# src/AGENTS.md? → include if found  
# AGENTS.md at BASE_DIR → EXCLUDED (first session) / INCLUDED (after compaction)
```

**Base directory instruction files:** On the first session, base dir files (e.g.,
`AGENTS.md` at BASE_DIR) are excluded because the harness (VS Code, OpenCode)
loads them. After context compaction triggers a second `new_session` clear
(clear count ≥ 2), base dir files ARE included so the LLM recovers lost context.

Config via `appsettings.json`:

```json
{"instructionFileNames": ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "QWEN.md", "AGENT.md", ".cursorrules"]}
```

### Per-Client Configuration

Override settings per MCP client using `clientOverrides` in `appsettings.json`:

```json
{
  "readCharLimit": 7000,
  "clientOverrides": {
    "OpenCode": { "readCharLimit": 50000 },
    "Cursor": { "readCharLimit": 15000 }
  }
}
```

The client name is auto-detected from the MCP `clientInfo.name` sent during initialization.
Falls back to the global `readCharLimit` when no override matches.

## 🔧 Tools

| Tool                                                                | Returns                                        |
| ------------------------------------------------------------------- | ---------------------------------------------- |
| `list(path, new_session)`                                           | Markdown table + [CHANGED_FILES]               |
| `read(file_path, new_session, show_line_numbers, offset, limit, cursor)` | Content + [CHANGED_FILES] + [INSTRUCTION_FILE] |
| `write(file_path, content, new_session)`                            | Success/error                                  |
| `edit(file_path, old_string, new_string, replace_all, new_session)` | Success/error                                  |
| `multi_edit(edits, new_session)`                                    | Per-edit success/error + [CHANGED_FILES]       |
| `multi_read(file_paths, new_session, show_line_numbers)`            | Per-file content + [CHANGED_FILES] + [AGENTS.MD] |
| `search(pattern, path, new_session)`                                | File list + [CHANGED_FILES]                    |
| `delete(file_path, new_session)`                                    | Success/error                                  |
| `clear()`                                                           | Resets all caches                              |

### Large Files

```python
read("huge.csv", offset=0, limit=100)       # Lines 1-100
read("huge.csv", offset=100, limit=100)     # Lines 101-200
read("huge.csv", show_line_numbers=True)    # 101→content...
# Cursor-based pagination (auto-triggers for large files):
read("huge.csv")                            # Returns first chunk + cursor value
read("huge.csv", cursor=44500)              # Continue from cursor position
```

### Edit Pattern

```python
edit("file.txt", "old", "new")              # Error if "old" appears multiple times
edit("file.txt", "old", "new", replace_all=True)  # Replaces all occurrences
```

## 🚨 Rules

### Change Detection

- mtime in **milliseconds**: `int(stat.st_mtime_ns / 1_000_000)`
- Cache content in `session.contents` for line-level diffs
- First read → `"1-EOF"` (no previous content)
- [CHANGED_FILES] reports **external changes only** - edit()/write() update cache
- Changes reported **once** then cache updates

### Instruction Files

- Priority order from `appsettings.json`, first match per folder wins
- Include files **between** target and BASE_DIR only
- BASE_DIR instruction files **excluded** on first session (clear count < 2)
- BASE_DIR instruction files **included** after compaction (clear count ≥ 2)
- Folder tracked in `provided_folders` → never shown again in session
- Only `new_session=True` resets

### Security

- **ALWAYS** `resolve_path()` validates paths within BASE_DIR (unless `allowFullPaths` is enabled)
- **NEVER** allow `..` traversal outside BASE_DIR (unless `allowFullPaths` is enabled)
- When `allowFullPaths: true` in `appsettings.json`, any absolute path on the system can be accessed
- Default: `allowFullPaths: false` (restricted to BASE_DIR)

## ❌ Common Pitfalls → ✅ Fix

| Pitfall                                    | Fix                                              |
| ------------------------------------------ | ------------------------------------------------ |
| Forgot `new_session=True` after compaction | First lineage call: always `new_session=True`    |
| Absolute paths `/home/user/file.txt`       | Relative: `file.txt`                             |
| Backslashes on Windows                     | Forward slashes: `src/app/file.ts`               |
| Reading multi-MB files                     | Use `offset`/`limit`                             |
| Ambiguous string replacement               | More specific `old_string` or `replace_all=True` |
| Instruction files not appearing            | Check `appsettings.json` + folder hierarchy      |
| Session state lost after compaction        | `new_session=True` on first call                 |

## 🆘 When Stuck

1. **Path errors** → Relative path within BASE_DIR, forward slashes
2. **File not found after write** → Parent dir may not exist
3. **String replacement ambiguous** → Make `old_string` more unique
4. **Instruction files missing** → Walks UP from file to BASE_DIR
5. **Change detection missing** → Only tracks files you've read
6. **Session state lost** → `new_session=True` after restart

## 🧪 Testing

```python
# Mock BASE_DIR
import path_utils
old_base_dir = path_utils._base_dir
path_utils._base_dir = tmpdir_path
try:
    # Test code
finally:
    path_utils._base_dir = old_base_dir
```

---

> 🤖 Server runs in Docker with `/data` mount. All tools validate via `resolve_path()`. Line diffs use `difflib`, search uses `glob`. **Always `new_session=True` after restart/compaction.**

---

When the task requires multiple steps or non-trivial changes, present a detailed plan using #planReview and wait for approval before executing.
If the plan is rejected, incorporate the comments and submit an updated plan with #planReview.
Always use #askUser before completing any task to confirm the result matches what the user asked for.
