# [COLOR] Agent Memory

<!--
  ╔══════════════════════════════════════════════════════════════════╗
  ║  READ-ONLY SECTION - DO NOT EDIT THIS BLOCK UNDER ANY CIRCUMSTANCE  ║
  ║  You are ONLY allowed to edit between ## State and ## Activity Log  ║
  ║  and to APPEND new entries at the bottom of ## Activity Log.        ║
  ╚══════════════════════════════════════════════════════════════════╝
-->

> ## HOW TO USE THIS FILE - READ ONLY - NEVER EDIT THIS BLOCK
>
> This file has two sections separated by a horizontal rule (`---`), with different rules for each.
> **This instructions block must never be edited, truncated, summarised or removed.**
>
> ---
>
> ### SECTION 1: STATE (between `## State` and `## Activity Log`)
>
> Keep tidy. Rewrite and reorganize freely to always reflect the **current** status.
> **TIMING: Update this section IMMEDIATELY after every ask_user response, BEFORE doing any other work.**
> After every ask_user response, update:
>
> - **Instructions Received** - full list of everything the user has asked you to do
> - **Files Read** - every file you have read so far, with a brief note on why
> - **Files Edited** - every file you have edited so far, with a brief note on what changed and why
> - **Current State** - where things stand right now: what's done, what's next, any blockers
>
> ---
>
> ### SECTION 2: ACTIVITY LOG (everything after `## Activity Log`)
>
> **APPEND ONLY. Never edit, rewrite, or remove existing entries. Only ever add new entries at the bottom.**
> **TIMING: Append a new entry IMMEDIATELY after every ask_user response, BEFORE doing any other work. This is the same timing as the State section - both must be updated before you start working.**
>
> After every ask_user response, add one new entry using this exact format:
>
> ```
> ### [timestamp] - [brief label e.g. "Instructions received" / "Task 1 complete" / "User correction"]
>
> **Asked:** [The exact question you sent via ask_user - do not paraphrase]
> **User said:** [The exact response the user gave - do not paraphrase]
> **Work done:** [Everything you did after receiving this response]
> **Next:** [What you are about to do next]
> ```
>
> The Activity Log is the audit trail. A new agent must be able to read it from top to bottom
> and resume your work without any other context. Every interaction must be recorded here, forever.
>
> ---
>
> ### RULES YOU MUST FOLLOW
>
> - You MUST follow all rules in AGENTS.md and relevant CLAUDE.md files.
> - You MUST use ask_user (with your name prefix) before starting work and before finishing work.
> - You MUST identify yourself by your name in every communication with the user.
> - **NEVER use any git command-line tools** (git checkout, git reset, git log, git status, git diff, etc.) without explicit written confirmation from the user. Git commands can be destructive and irreversible. If you believe a git command is needed, ask the user first via ask_user and wait for them to say yes before running anything.
> - Never use the `any` type in TypeScript.
> - Read full files, never partial.
> - **The ONLY tool allowed for reading files is the lineage tool.** Never use any other file-reading mechanism.
> - **NEVER use the built-in `read_file` tool.** This tool is NOT available to you. It is not in your tools list. If you attempt to call `read_file`, `readFile`, or any VS Code built-in file reading tool, you are violating your configuration. Use ONLY `mcp_lineage_modify` for all file reading.
> - When responding to the user via the ask_user tool, remember that the user may be working with many agents at once and will not remember what they told you to go and do, so always restate the instructions they gave you in your ask_user message before providing your answer or update.
> - Reports must be thorough and detailed, covering all relevant findings. Inform the user of the file path once written via the ask_user tool.
> - When creating an implementation guide, ALWAYS prefix the filename with your name in lowercase followed by a hyphen (e.g. for Green: `green-my-feature.md`).
> - If the linage tool is paused you must not do anything else other than use the ask_user tool, Never try to work around the lineage tool being paused!
>
> ---
>
> ### WHAT YOU ARE ALLOWED TO EDIT
>
> | Section                       | Allowed edits                         |
> | ----------------------------- | ------------------------------------- |
> | This block (above `## State`) | **NOTHING. Read only. Never touch.**  |
> | `## State` section            | Rewrite freely to keep current        |
> | `## Activity Log` section     | Append new entries at the bottom only |

---

## State

**Agent Color:** [COLOR]
**Session Started:** [timestamp]
**Status:** Waiting for instructions

### Instructions Received

_None yet_

### Files Read

_None yet_

### Files Edited

_None yet_

### Current State

Agent initialized. Reading AGENTS-REFERENCE then asking for instructions.

---

## Activity Log

_Append only. Never edit existing entries. Add new entries at the bottom._

### [timestamp] - Session Started

**Asked:** N/A - session just initialized
**User said:** N/A
**Work done:** Created memory file from template. Reading AGENTS-REFERENCE.md next.
**Next:** Read AGENTS-REFERENCE.md then ask for instructions.
