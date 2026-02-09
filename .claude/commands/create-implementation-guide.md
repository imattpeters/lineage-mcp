---
name: "Create-Implementation-Guide"
description: "Create a Comprehensive Implementation Guide"
---

Create a comprehensive implementation guide that developers can follow to implement a feature correctly on the first attempt.

## Step 1: Gather Context

1. **Read the main project guide** - Review `AGENTS.md` (or `CLAUDE.md`) to understand:
   - Core patterns and conventions
   - Absolute rules and constraints
   - File organization and module structure
   - Session management, state, and key APIs

2. **Understand the architecture** - Review existing docs to understand:
   - Core components and their responsibilities
   - How different layers interact
   - Key design patterns used (e.g., separation of concerns, IPC, threading)
   - Configuration and environment patterns

3. **Find similar implementations** - Search the codebase for 2-3 similar features:
   - Read their complete implementations
   - Understand how they follow established patterns
   - Identify edge cases and variations

4. **Check existing guides** - Review any existing implementation guides in `docs/` to:
   - Understand the expected structure and depth
   - See what level of detail is provided
   - Learn what "copy-paste-ready" means in your codebase

5. **Create the guide location** - Place the document in `docs/` (e.g., `docs/feature-name-implementation-guide.md`)

## Step 2: Design the Feature

Use sequential thinking to work through:

- **High-level architecture**: How does this feature fit into the existing system?
- **Core components**: What modules/files need to be created or modified?
- **Integration points**: Which existing components interact with this feature?
- **State management**: How will state be tracked and communicated?
- **Error handling**: What errors can occur and how should they be handled?
- **Threading/concurrency**: Are there threading considerations?
- **Testing strategy**: What needs to be tested (unit, integration)?

## Step 3: Generate the Guide

Structure the guide similar to existing implementation guides in the project. Include:

- **Overview/Summary**: What is being built and why
- **Architectural Decisions**: Major decisions made (as a table)
- **File Structure**: New files to create with their purpose
- **Core Implementation**: Copy-paste-ready code organized by component
- **Integration Points**: How to hook this into existing code
- **Error Handling & Edge Cases**: What can go wrong and how to handle it
- **Threading/Concurrency** (if applicable): Threading model and safety
- **Configuration** (if applicable): Environment variables or config changes
- **Testing Strategy**: Unit and integration test examples
- **Implementation Order**: Phases for building the feature
- **Open Questions/Decisions**: Items that need user decision

## Step 4: Validate Against Actual Codebase

**CRITICAL: After writing the guide, validate it against actual code.** This is non-negotiable.

### Validation Checklist

- [ ] **Code examples match actual patterns**
  - [ ] Read existing files you referenced to confirm patterns
  - [ ] Verify imports, class names, and structure
  - [ ] Check that async/sync usage matches actual code
  - [ ] Ensure naming conventions match (snake_case, camelCase, etc.)

- [ ] **File paths are accurate**
  - [ ] Verify all paths exist in the codebase
  - [ ] Check module/package names are correct
  - [ ] Confirm directory structure is as specified

- [ ] **Rules compliance**
  - [ ] Read the project guide and confirm examples follow all rules
  - [ ] Check for any forbidden patterns (e.g., specific imports, styles)
  - [ ] Verify error handling approach matches project patterns

- [ ] **Similar implementations exist**
  - [ ] Find 2-3 real examples of the patterns you described
  - [ ] Read actual implementation to confirm your guide matches
  - [ ] Look for variations or special cases not covered

- [ ] **Configuration and environment setup**
  - [ ] If config changes are needed, check the config module/file
  - [ ] Verify config structure and naming patterns
  - [ ] Check for environment variable patterns

- [ ] **API and integration points**
  - [ ] Verify that existing APIs work as described
  - [ ] Check that integration points are available
  - [ ] Confirm signatures and parameter names

- [ ] **Test patterns and tooling**
  - [ ] Read existing test files to understand the pattern
  - [ ] Verify test framework and assertion style
  - [ ] Check how test setup/fixtures work

### Tools to Use

- **Read** - Get full file content to verify patterns and details
- **Grep** - Search for similar implementations across codebase
- **Glob** - Find and verify files exist at expected paths

### When Validation Fails

If you find discrepancies:

1. **Update the guide immediately** - Don't proceed with wrong information
2. **Document what was wrong** - Note what you found vs. what you wrote
3. **Re-verify** - Use read/grep/glob to confirm the fix
4. **Do NOT mark as complete** until guide matches reality

### Sign Off

After all validation checks pass, add this line at the end of the guide:

```
<!-- VALIDATED: This guide was validated against actual codebase on [DATE]. All examples match current patterns and file structure. -->
```

---

Now create the implementation guide for: $ARGUMENTS
