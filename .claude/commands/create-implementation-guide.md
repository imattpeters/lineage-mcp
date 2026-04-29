---
name: "Create-Implementation-Guide"
description: "Create a Comprehensive Implementation Guide"
---

Create a comprehensive implementation guide that developers can follow to implement a feature correctly on the first attempt. The guide combines PRD-style product framing (problem, goals, users, success criteria, scope) with concrete engineering instructions (files, code, Gherkin tests, checklist).

## Step 0: Get On The Same Page As The User (MANDATORY - DO NOT SKIP)

Before reading any code or writing anything, your first job is to remove every gap in your understanding of what the user actually wants. You are not a stenographer - you are a wingman. If you do not understand the request well enough to write a PRD-quality summary, you do not understand it well enough to write a guide.

**Process:**

1. Re-read the user's request and write down (in chat) your current understanding in 3-6 bullets covering: what is being built, who it is for, why it matters, what the success criteria are, what is explicitly out of scope.
2. Identify every assumption you are making to fill gaps the user did not explicitly state. Each assumption is a question.
3. Ask the user the questions (use whichever ask-user MCP tool is available, or plain chat questions). Batch related questions together. Ask the smallest number of questions that resolves the largest amount of ambiguity.
4. **Do NOT proceed to Step 1 until the user has answered.** It is never acceptable to guess and write a guide hoping the user corrects it later.

**Question categories to cover (only ask the ones that are actually unclear):**

| Category | Examples |
| --- | --- |
| Problem & motivation | What problem does this solve? Whose pain? Why now? |
| Users & roles | Who interacts with this? What permissions / contexts apply? |
| Scope boundaries | What is in scope vs out of scope? Any related features deliberately excluded? |
| Success criteria | How do we know it worked? Metric, behaviour, or qualitative outcome? |
| UX & flows | Entry points, states, error / empty / loading states |
| Data & domain | New entities? New fields? Migration impact? |
| API surface | New endpoints / tools / commands? Public shape? |
| Integrations | External services, IPC, events, workers |
| Non-functional | Performance, accessibility, observability, rate limits |
| Rollout | Feature flag? Backfill? Gradual rollout? |
| Open questions | Anything the user has not decided yet that you need decided before writing the guide |

When the user answers, restate your updated understanding in chat in one short paragraph and confirm before continuing.

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

The guide is part PRD, part engineering spec. The PRD sections frame WHY and WHAT; the engineering sections give the HOW. Both are required.

### PRD-style sections (the WHY and WHAT)

- **Summary**: One paragraph - what we're building and why it matters
- **Problem Statement**: The user pain or business gap this addresses. Concrete, not abstract.
- **Goals & Non-Goals**: Bulleted. Goals are what success looks like. Non-Goals explicitly call out what this guide does NOT do (to prevent scope creep).
- **Target Users & Roles**: Who is affected and how
- **User Stories**: `As a <role>, I want <capability>, so that <outcome>.` One per discrete capability.
- **Success Criteria & Metrics**: Measurable outcomes
- **UX / Interaction Flow**: Entry points, primary happy path, key states (loading / empty / error / unauthorised)
- **Scope Boundaries**: In-scope and out-of-scope, with one-line justifications for the out-of-scope items
- **Open Questions Resolved**: Brief log of the questions you asked the user in Step 0 and the answers received - this becomes the source of truth for the decisions made

### Engineering sections (the HOW)

- **Architectural Decisions**: Major decisions made (as a table)
- **File Structure**: New files to create with their purpose
- **Core Implementation**: Copy-paste-ready code organized by component
- **Integration Points**: How to hook this into existing code
- **Error Handling & Edge Cases**: What can go wrong and how to handle it
- **Threading/Concurrency** (if applicable): Threading model and safety
- **Configuration** (if applicable): Environment variables or config changes
- **Acceptance Criteria (Gherkin)**: Given/When/Then scenarios for every user story - see below
- **Testing Strategy**: Unit and integration tests, each mapping to a Gherkin scenario
- **Implementation Order**: Phases for building the feature
- **Verification Source Files**: Structured tables of every reference file the implementor should cross-check (see below)
- **Implementation Checklist**: Every step as a `- [ ]` markdown checkbox - see below

### Verification Source Files Requirements

After the engineering sections list, add a **Verification Source Files** section with tables organized by category. This section exists so the implementor can validate the guide independently.

Categories to include (only those relevant to the feature):

1. **Architectural Decisions** - Key design docs, ADRs, or AGENTS.md sections and what to verify in each
2. **AGENTS.md / CLAUDE.md Files** - All applicable guide files and which patterns to verify
3. **Existing Implementation Examples** - Specific source files showing the exact patterns to follow
4. **Configuration** - Config files, environment variable files, docker-compose, etc.
5. **Tests** - Existing test files showing the pattern to follow

Format: tables with two columns: `File` (full paths) and `Verify` (what to check).

**Example:**

| File | Verify |
| --- | --- |
| `src/server/session_manager.py` | How sessions are created and stored |
| `AGENTS.md` | Threading rules, forbidden patterns |

### Implementation Checklist Requirements

The guide MUST end with an `## Implementation Checklist` section. Every discrete step the implementor needs to perform must appear as a `- [ ]` checkbox. This is not a summary - it is a complete ordered list of every action, including build and test commands, so the implementor can tick off each step and always know exactly where they are.

Plain bullet points and numbered lists are not acceptable for this section. Every item must be a checkbox.

### Acceptance Criteria (Gherkin / SpecFlow) Requirements

Every user story MUST have at least one Gherkin scenario. Use standard Gherkin syntax inside ```gherkin fenced blocks. Scenarios drive the test plan - every scenario maps to a concrete test.

Required structure:

```gherkin
Feature: <short feature name matching the user story>

  Background:
    Given <shared setup that applies to every scenario>

  Scenario: <happy path - one sentence>
    Given <preconditions>
    And <more preconditions>
    When <the user action or system trigger>
    Then <observable outcome>
    And <additional assertion>

  Scenario: <a key error / edge / unauthorised case>
    Given ...
    When ...
    Then ...

  Scenario Outline: <when behaviour varies by input>
    Given an input of <input>
    When the operation runs
    Then the result is <result>

    Examples:
      | input    | result   |
      | valid    | success  |
      | missing  | rejected |
```

Coverage rules:

- Every user story has at least a happy-path scenario.
- Every authorisation / permission boundary has both an allowed and denied scenario.
- Every error state shown in the UX flow has a scenario.
- Every invariant / validation rule has a scenario proving it triggers.
- Use `Scenario Outline` + `Examples` for input / state variations rather than copy-pasting scenarios.
- Every Gherkin scenario maps 1:1 to a concrete test in the Testing Strategy section.

## Language Rules (MUST be followed when writing the guide)

These rules apply to every sentence you write in the guide. Violating them will cause the guide to fail validation.

### No Non-Committal Language

Implementation guides are instructions, not suggestions. Every step must be written as a direct, unambiguous instruction. The following language is **never acceptable**:

| Banned phrase | Replace with |
| --- | --- |
| "consider adding X" | "add X" |
| "you might want to X" | "X" |
| "it may be worth X" | "X" |
| "could be useful to X" | "X" |
| "it might be a good idea to X" | "X" |
| "potentially add X" | "add X" |
| "you may wish to X" | "X" |
| "might need to X" | "X" |
| "perhaps X" | "X" |

If you find yourself wanting to write non-committal language, stop and ask the user for clearer direction. Do not guess, do not soften the wording, and do not write a vague instruction hoping the implementor figures it out. Get the clarification you need before writing the step.

### No Deferred or Incomplete Statements

The guide must be complete. The following are never acceptable:

| Category | Banned examples |
| --- | --- |
| Deferred work | "for later development", "future work", "we can add this later", "in a follow-up", "phase 2" |
| Scope reduction | "not needed for now", "can be skipped for now", "out of scope for this guide", "simplified for now" |
| Disabling code | "just comment it out", "disable for now", "temporarily remove" |
| Placeholders | "TODO", "TBD", "TK", "placeholder", "stub", "to be implemented" |
| Hardcoding workarounds | "hardcode for now", "we'll make this configurable later" |
| Incomplete error handling | "ignore the error for now", "we'll add error handling later", "skip validation for now" |
| Deferred tests | "we'll add tests later", "skip the test for now" |

If you cannot write the complete implementation for something, stop and ask the user before writing a placeholder. Do not write incomplete sections and flag them for later.

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

- [ ] **PRD-style sections are complete**
  - [ ] Problem Statement, Goals & Non-Goals, Target Users & Roles, User Stories, Success Criteria & Metrics, UX Flow, Scope Boundaries, Open Questions Resolved are all present and non-empty
  - [ ] Every user story follows `As a <role>, I want <capability>, so that <outcome>.`
  - [ ] Open Questions Resolved reflects the actual Q&A from Step 0

- [ ] **Gherkin / SpecFlow acceptance criteria**
  - [ ] Every user story has at least one `Scenario` (or `Scenario Outline`) in a ```gherkin block
  - [ ] Every authorisation / permission boundary has both allowed and denied scenarios
  - [ ] Every error / empty state from the UX flow has a scenario
  - [ ] Every invariant / validation rule has a scenario proving it triggers
  - [ ] Every Gherkin scenario maps 1:1 to a concrete test in the Testing Strategy section
  - [ ] Gherkin uses standard Given/When/Then keywords and `Examples:` tables for variations rather than copy-pasted scenarios

- [ ] **Verification Source Files section exists**
  - [ ] Tables present for all relevant categories (design docs, example files, config, tests)
  - [ ] Every file path in the tables has been verified to exist
  - [ ] Every `Verify` column entry is specific, not generic

- [ ] **Language rule compliance**
  - [ ] Scan entire guide for non-committal language (consider, might, perhaps, could, optionally, potentially, may wish to, it may be worth)
  - [ ] Scan for deferred work statements (TODO, TBD, for now, later, future, phase 2, skip for now, comment out, hardcode for now)
  - [ ] Fix every violation found - leave none in the guide

- [ ] **Implementation Checklist completeness**
  - [ ] Every item is a `- [ ]` checkbox - no plain bullets or numbered items
  - [ ] Every step in the guide body has a corresponding checkbox
  - [ ] Build and test commands are included as checkboxes
  - [ ] Checkboxes are in logical implementation order

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
