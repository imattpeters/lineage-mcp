---
name: "Create-Commit-Message"
description: "Create a commit message from staged changes and commit"
---

Create a high‑quality commit message from currently staged changes, confirm with the user, then commit.

> **⚠️ GIT COMMAND EXCEPTION**: This command explicitly allows Git operations. When this command is invoked, you ARE allowed to run git commands (`git status`, `git diff`, `git commit`, etc.).

## Goal

- Inspect only STAGED changes in the current Git repo using Git commands, draft a clear Conventional Commit message, show it for confirmation, and if approved: commit using a temp file, then delete the temp file.

## Preconditions & Safety

- **THIS COMMAND ONLY**: You may use Git commands (status, diff, commit, log) for this task. This is an exception to normal Git restrictions.
- Operate only on staged changes. If nothing is staged, ask whether to abort or stage all modified files; do not stage automatically unless the user explicitly asks.
- Avoid leaking secrets in the commit message (redact tokens, keys, passwords if they appear in diffs).
- Treat binary or large diffs by summarizing the file name and change type without dumping binary content.

## Steps

1) **Gather context**

- Run `git status` to list staged vs. unstaged files.
- Run `git diff --staged` to get a diff of all staged changes.

2) **Draft the commit message (Conventional Commits)**

- Based on the diff, draft a commit message that follows the Conventional Commits specification.

3) **Present the result for confirmation**

- Show a compact staged summary (file list with change types) and the candidate commit message(s).
- **IMPORTANT** - do not skip the confirmation step
- Ask: "Use this commit message? (yes/no/edit)". If edit, accept the user's replacement text and proceed as though "yes" with the edited message.

4) **On approval, commit using a temp file**

- Write the chosen message to a temp file
- Run `git commit -F <temp-file>`
- Clean up the temp file
- Do not run any other commands after cleanup.

5) **Error handling**

- If commit fails (e.g., hooks, empty commit), show the error and ask the user how to proceed.
- If temp file ops fail, show the path used and the exact error.

## Output expectations

- Always display:
  - Staged changes summary (file, A/M/D/R, brief note if available)
  - Candidate commit message in full
  - Prompt for user confirmation (yes/no/edit)
- On success, the command will finish.

## Example

- Staged summary:
  - M docs/README.md - clarified setup
  - A src/utils/date.ts - new helpers

- Candidate message:
```
feat(utils): add date helpers and clarify README setup

- add parseISO and formatDate utilities in src/utils/date.ts
- document required Node version and env setup in README

refs #123
```

## Confirmation flow

- If user says "yes": perform the commit flow in Step 4.
- If user says "edit": accept edited message and then perform Step 4.
- If user says "no": abort without changes.

---

## Important Notes

- Do not state that you are implementing something if the only change is a file rename.
- If you need to read any files to understand the changes, do so before drafting the message.
- You can ask the user for clarification if needed, including reasons for the changes.
