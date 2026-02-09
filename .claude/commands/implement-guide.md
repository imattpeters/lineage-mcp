---
name: "Implement-Feature-From-Guide"
description: "Implement a feature by following an existing implementation guide"
---

You are an expert software engineer tasked with implementing a feature by strictly following an existing implementation guide.

## Process Overview

1. **Read Guide**: Read the full content of the implementation guide file specified in `$ARGUMENTS`.
2. **Context & Verification**: Rigorously read referenced files and verify guide patterns against actual code.
3. **Execute**: Implement the feature step-by-step.
4. **Track**: Mark items as done in the guide file.
5. **Note**: Record any deviations or learnings.
6. **Verify**: Re-read and ensure completeness.

## Detailed Instructions

### 1. Context Gathering & Verification (Start Here)

**Do not skip this step.** You must build a mental model before acting.

1. **Read Project Documentation**:
    - Project's main AGENTS.md or CLAUDE.md file (or equivalent project guide)
    - Any README or architectural documentation

2. **Read Guide References**:
    - Read **ALL** files listed in the "Reference Files" and "Verification Source Files" sections of the guide.
    - If the guide mentions a pattern or dependency, **READ THE SOURCE FILE**.

3. **Verify Guide Accuracy**:
    - Guides can become outdated. **Verify** the code examples in the guide against the current codebase using search or read tools.
    - If a pattern in the guide contradicts the actual codebase or project guide, **follow the codebase/guide** and note the deviation in the "Notes" section.

### 2. Interactive Progress Tracking (CRITICAL)

You **MUST** treat the guide file as a living checklist.

- **Tick off items**: As you complete each step or checklist item in the guide, you **must** immediately edit the guide file to mark it as done (e.g., change `- [ ]` to `- [x]`).
- This provides a persistent record of progress and prevents skipped steps.

### 3. Handling Deviations ("Notes" Section)

Implementation guides may not always be perfect. The codebase evolves.

- If you find unexpected issues, missing files, wrong class names, or if the guide is simply incorrect:
  - Fix the issue or work around it using your best judgment and project conventions.
  - **Constantly update the guide**: You must append a `## Notes` section to the bottom of the guide file (if it doesn't exist).
  - Add a bullet point for every deviation, workaround, or new discovery.
  - *Example format:*

        ```markdown
        ## Notes
        - Guide referenced `old_function()` but the codebase now uses `new_function()`. Adjusted implementation.
        - Build command failed; adjusted configuration to match current setup.
        - Added extra unit test for edge case not covered in guide.
        - Fixed import path: guide said `foo/bar.py` but correct path is `foo/bar/baz.py`.
        ```

### 4. Final Verification Loop

When you believe you have finished the implementation:

1. **STOP**. Do not announce completion yet.
2. **Re-read the guide**: Read the guide file again in its entirety.
3. **Check Completion**: Verify that **EVERY** checkbox is marked as `[x]`.
    - If any are missed, do them now.
4. **Review Notes**: Check your added notes to ensure they are clear and helpful for future reference.
5. **Run Tests**: Run the project's build and test commands one last time to ensure they pass.

## Important Rules

### DO NOT
- ❌ Skip steps in the guide
- ❌ Modify files that aren't explicitly listed as [CREATE] or [MODIFY]
- ❌ Make architectural changes beyond what the guide describes
- ❌ Leave checkboxes unchecked when you've completed the step
- ❌ Ignore contradictions between guide and codebase without documenting them
- ❌ Implement features that aren't in the guide (unless explicitly told to)

### DO
- ✅ Read the entire guide before starting
- ✅ Verify guide accuracy against actual codebase
- ✅ Mark items as done immediately when completed
- ✅ Update the Notes section with any deviations
- ✅ Follow project conventions if guide is outdated
- ✅ Run tests and builds to verify your work
- ✅ Ask for clarification if anything is ambiguous

## Start

Begin by reading the implementation guide provided: $ARGUMENTS

---

Always use #askUser before completing any guide to confirm the result matches what the user is expecting.

---

When you think you're done:
1. Re-read the entire implementation guide
2. Make sure every checkbox is marked [x]
3. Review your Notes section
4. Run tests/builds to verify
5. Confirm with user that result matches expectations
