---
name: "Validate-Guide"
description: "Comprehensively validate an implementation guide against the codebase, ALL assumptions, and feasibility"
---

## ⚠️ WHAT THIS IS NOT

**This is NOT a surface-level checklist.** It's not:
- ✗ Just checking if files exist
- ✗ Just checking if code patterns match superficially
- ✗ Reading summaries and moving on
- ✗ Assuming implied functionality

**This HAS FAILED when:**
- Files existed but guide misunderstood how they work
- Patterns existed but guide's assumptions about behavior were wrong
- Everything looked good but critical assumptions were never verified
- Dependencies were assumed implemented but weren't

## ✅ WHAT THIS SHOULD DO

This validation **thoroughly verifies that a guide is safe to implement:**

1. **Extract and verify EVERY assumption** - especially implicit ones
2. **Confirm all dependencies are implemented** - don't assume
3. **Read actual code** to understand behavior - not just pattern-match
4. **Check logic and coordination** - verify edge cases and potential issues
5. **Identify open questions** - don't guess at ambiguities
6. **Assess feasibility** - is the approach compatible with actual codebase?
7. **Flag risks** - edge cases, potential failures, missing error handling

**Result:** A guide you'd bet money on will work.

---

> **🚫 CRITICAL WARNING - DO NOT IGNORE**
>
> **NEVER IMPLEMENT THE GUIDE UNLESS EXPLICITLY TOLD TO BY THE USER**
>
> Your job is to **RIGOROUSLY VALIDATE** the guide, not **IMPLEMENT** it.
> - Read the guide completely and compare it to the actual codebase
> - **QUESTION EVERY ASSUMPTION** - don't take anything for granted
> - Check if features the guide depends on are actually implemented
> - Read actual code to verify the guide's understanding is correct
> - Find all discrepancies and document them
> - Fix the **GUIDE DOCUMENTATION** itself (fix typos, update paths, correct code examples)
> - **DO NOT** create the files described in the guide
> - **DO NOT** modify the actual codebase to match the guide
> - **DO NOT** implement features described in the guide
>
> **ONLY mark as VALID if:**
> - All file paths verified to exist
> - All code patterns verified against actual implementations
> - All foundational assumptions confirmed
> - All dependencies/features the guide relies on are confirmed implemented
> - No open questions remain
> - Integration with existing code is verified feasible
>
> **If uncertain, mark NEEDS CLARIFICATION** - don't guess or assume!

Validate that an implementation guide:
1. Accurately reflects current codebase patterns and project guide rules
2. Makes only valid assumptions about what exists in the codebase
3. Proposes technical approaches that are feasible given current architecture
4. Doesn't depend on unimplemented features
5. Has no unresolved questions or open assumptions

## Purpose

Before following a guide, verify it's **complete, accurate, and achievable**. A guide may have correct syntax/patterns but fail if it depends on missing features or makes incorrect assumptions about how the system works.

## Process

### ⚠️ BEFORE YOU START - REMEMBER

**You are validating, NOT implementing.**
- If the guide describes files that don't exist → Document it, don't create them
- If code examples are wrong → Fix the examples in the guide, don't fix the codebase
- If patterns don't match → Update the guide documentation to reflect reality
- **NEVER** run Write or Edit on actual source files (only on the guide itself)

**QUESTION EVERYTHING** - especially:
- "Does this feature actually exist in the codebase?"
- "Has this assumption been verified?"
- "What if the behavior doesn't work like the guide assumes?"
- "Are there unresolved edge cases?"

---

### 1. Read the Guide Completely

Read the entire implementation guide file specified in `$ARGUMENTS`.

**Extract and list:**
- ✅ All assumptions the guide makes (explicitly stated and implicit)
- ✅ All features the guide depends on ("guide assumes X is implemented")
- ✅ All logic/coordination requirements
- ✅ All dependencies between parts
- ✅ Any "TBD" or "TK" placeholders
- ✅ Any areas marked as "unclear" or "needs verification"

### 2. Extract All Assumptions

Create a list of **every assumption** the guide makes:

**Examples of assumptions to look for:**
- "Feature X is implemented"
- "Configuration option Y will always be set"
- "Component Z handles errors in a specific way"
- "API endpoint returns a specific payload structure"
- "Threading model follows pattern X"

**For each assumption, mark:**
- [ ] **Explicitly stated?** (said directly in guide)
- [ ] **Implicit?** (guide relies on it but doesn't mention it)
- [ ] **Verified?** (actually checked in codebase)
- [ ] **Critical?** (implementation will fail if false)

### 3. Read Project Documentation

Read the main project guide:
- Project's main AGENTS.md or CLAUDE.md file
- Any architectural documentation or README
- Configuration and environment setup documentation

### 4. Read Related Reference Files

Based on guide content, read:
- **All files mentioned in guide's Verification Source Files section** - Read the FULL TEXT, not just summaries
- **All CLAUDE.md or guide files for affected components** - Don't assume; read them
- **Related implementation guides** - Especially any guide the current guide depends on
- **Example implementations** - Understand how similar features work

### 5. Validate All Assumptions

**For each assumption from Step 2:**

**If explicitly stated assumption:**
1. Search codebase for evidence it's implemented
2. Read relevant code to understand actual implementation
3. Compare with assumption - are they the same?
4. If different: flag as "ASSUMPTION MISMATCH"
5. If missing: flag as "ASSUMPTION NOT IMPLEMENTED"

**If implicit assumption:**
1. Search for where this feature is used in existing code
2. Read that code to understand actual behavior
3. Does it match what the guide assumes?
4. If unclear: flag as "REQUIRES CLARIFICATION"

### 6. Validate File Existence

For **every file path** mentioned in the guide:
- Verify existence in the codebase
- Check directory structure matches guide
- Flag missing or moved files
- If file mentioned but paths don't work: research actual location

### 7. Validate Code Patterns

For each code pattern the guide claims to follow:
- Find real implementations in codebase
- **Read the actual code** - don't just pattern-match
- Compare guide examples to actual implementations
- Check for deviations, updates, or differences
- Note: "pattern exists" ≠ "guide example is correct"

### 8. Read Key Files and Compare

For **critical reference files**:
- Read the actual file completely
- Compare with guide's understanding
- Note structural changes (class names, method signatures, parameters)
- Verify guide's code examples match actual signatures
- **Special attention**: Constructor parameters, method signatures, required properties, return types

### 9. Verify Dependencies

List all features the guide depends on:
1. Is it implemented in the codebase?
2. Search for any related implementation guides
3. Are those guides marked as "DONE"?
4. Is there any "ASSUMED IMPLEMENTED" marker?
5. If dependency is unclear: treat as unverified

### 10. Check Logic and Edge Cases

For features involving logic, configuration, or coordination:
- Find where similar patterns are implemented
- Read the code to understand actual behavior
- Verify guide's understanding is correct
- Check for potential race conditions or edge cases
- Look for off-by-one errors or calculation issues

### 11. Cross-Reference All Rules

Verify the guide follows:
- **Project guides**: Read project rules to confirm patterns align
- **Conventions**: Check code style and naming match actual code
- **Patterns**: Do code examples match actual code style in codebase?
- **Terminology**: Does the guide use correct terms from project documentation?

### 12. Look for Edge Cases and Issues

For each significant piece of the implementation, ask:
- What happens if X is zero or null?
- What if two events happen simultaneously?
- What if a resource is not available?
- What if timing is slightly off?
- Can this cause memory leaks?
- Are there race conditions?
- Is this compatible with existing patterns?

## Validation Report

Produce a comprehensive validation report with all sections below. **Be specific and thorough.**

### Summary
- Guide file path
- Validation date
- Overall status: **VALID**, **NEEDS CLARIFICATION**, or **NEEDS UPDATE**
  - **VALID**: All assumptions confirmed, no open questions, feasible to implement
  - **NEEDS CLARIFICATION**: Critical questions remain unanswered - don't implement until clarified
  - **NEEDS UPDATE**: Contradictions found between guide and codebase - guide needs fixing

### Assumptions Validation

| # | Assumption | Source | Status | Evidence / Issue |
|---|-----------|--------|--------|------------------|
| 1 | (e.g., "feature X is implemented") | Explicit / Implicit | ✅ Verified / ❓ Unverified / ❌ False | (What you found in codebase) |
| 2 | ... | ... | ... | ... |

**Critical assumptions that would break the implementation if false:**
- (List high-risk assumptions here with their status)

**Unverified assumptions:**
- (List any assumptions you couldn't confirm)

### File Existence Check
| File | Status | Notes |
|------|--------|-------|
| (list all referenced files) | ✅ Exists / ❌ Missing / ⚠️ Moved | (path corrections or location) |

**Missing files that would block implementation:**
- (List if any)

### Code Pattern Verification
| Pattern | Guide Example | Actual Codebase | Status | Notes |
|---------|---------------|-----------------|--------|-------|
| (describe pattern) | (line/section in guide) | (file and line in codebase) | ✅ Match / ⚠️ Similar / ❌ Different | (Any discrepancies) |

**Pattern mismatches that affect implementation:**
- (If guide example doesn't match actual code, be specific)

### Dependency Verification

| Dependency | Status | Details |
|-----------|--------|---------|
| (e.g., feature X) | ✅ Implemented / ❌ Not Found / ❓ Unclear | (Where it's used, how it works) |

**Unimplemented dependencies that would block this guide:**
- (List any critical features the guide depends on that don't exist)

### Logic and Edge Case Analysis

**Potential issues identified:**
1. (e.g., "If X is unavailable, behavior unclear")
2. (e.g., "Logic assumes Y always available - what if null?")
3. (e.g., "Race condition possible if Z happens simultaneously")

**Feasibility assessment:**
- Is the proposed approach compatible with existing architecture? (Y/N)
- Are there any fundamental blockers? (List if Y)
- Will this integrate cleanly without major refactoring? (Y/N)

### Rule Compliance
| Rule | Status | Notes |
|------|--------|-------|
| (Project rule X) | ✅ Pass / ❌ Fail | (locations if fail) |
| (Project rule Y) | ✅ Pass / ❌ Fail | (locations if fail) |

### Open Questions

List any questions that remain unanswered:
1. (e.g., "Does feature X expose Y in the API?")
2. (e.g., "What's the expected behavior if Z fails?")
3. (e.g., "Is configuration always populated or can it be null?")

**If any open questions exist, DO NOT mark as VALID.**

### Required Updates to Guide

List specific changes needed:
1. (e.g., "Update file path from X to Y")
2. (e.g., "Correct logic in section X - current guide incorrect")
3. (e.g., "Add clarification: behavior when X happens")
4. (e.g., "Fix terminology: change X to Y in line Z")

### Validation Sign-Off

Add to the bottom of the guide file. Choose the appropriate status:

**If VALID (all assumptions confirmed, no open questions):**
```markdown
<!-- VALIDATION: [DATE] - Status: VALID - All assumptions verified, dependencies confirmed, ready for implementation -->
```

**If NEEDS CLARIFICATION (critical questions remain):**
```markdown
<!-- VALIDATION: [DATE] - Status: NEEDS CLARIFICATION - Open questions:
1. Does feature X work as described?
2. What's expected behavior in edge case Y?
DO NOT IMPLEMENT until these are clarified -->
```

**If NEEDS UPDATE (contradictions or issues found):**
```markdown
<!-- VALIDATION: [DATE] - Status: NEEDS UPDATE - Issues found:
1. ✓ Fixed timing calculation (was incorrect)
2. ✓ Clarified behavior (parent must be position: relative)
3. ✓ Added fallback for missing X
AFTER FIXES: Status changed to VALID -->
```

## Pre-Completion Validation Checklist

**Do NOT skip steps. Every checkbox must be completed and verified.**

### Reading Phase
- [ ] Read guide completely - understand every assumption and requirement
- [ ] Read project documentation/CLAUDE.md/AGENTS.md
- [ ] Read ALL reference files mentioned in guide
- [ ] Read ALL files for affected components
- [ ] Read ANY related implementation guides (especially if guide depends on them)
- [ ] Read example implementations to understand current behavior

### Assumption Extraction
- [ ] Created explicit list of ALL assumptions (explicit and implicit)
- [ ] Categorized assumptions as: explicit/implicit, critical/optional
- [ ] Listed all features the guide depends on
- [ ] Flagged all logic/coordination requirements

### Assumption Verification
- [ ] **For EACH assumption**: Searched codebase for evidence
- [ ] **For EACH assumption**: Read relevant code to verify
- [ ] **For EACH assumption**: Documented status (verified/unverified/false)
- [ ] Flagged critical unverified assumptions
- [ ] Resolved or documented all implicit assumptions

### File and Pattern Validation
- [ ] Verified ALL file paths exist
- [ ] Verified directory structure matches guide
- [ ] Validated code patterns against actual implementations
- [ ] Read actual code to compare with guide examples
- [ ] Checked for structural changes (method signatures, parameters, class names)
- [ ] Noted any deviations between guide and actual code

### Dependency Verification
- [ ] Listed all external dependencies (features, APIs, modules, etc.)
- [ ] Searched for evidence each dependency is implemented
- [ ] Read code to understand actual implementation
- [ ] Compared with guide's assumptions about that dependency
- [ ] Flagged any unimplemented dependencies

### Logic and Edge Cases
- [ ] Identified potential edge cases (zero/null values, concurrent events, missing resources)
- [ ] Checked for potential race conditions
- [ ] Checked for unbounded loops or allocations
- [ ] Verified compatibility with existing patterns
- [ ] Assessed overall feasibility

### Report Generation
- [ ] Created comprehensive validation report with all sections
- [ ] Listed all assumptions with verification status
- [ ] Documented all open questions
- [ ] Identified all issues (missing dependencies, pattern mismatches, ambiguities)
- [ ] Proposed specific fixes to guide
- [ ] Included risk/feasibility assessment

### Guide Updates (if needed)
- [ ] Applied fixes to guide documentation (typos, paths, examples)
- [ ] Updated code examples to match actual patterns
- [ ] Added clarifications for implicit assumptions
- [ ] Fixed incorrect logic or calculations
- [ ] Did NOT modify any actual source code files

### Final Status
- [ ] Assigned appropriate status: VALID / NEEDS CLARIFICATION / NEEDS UPDATE
- [ ] Status matches actual validation results
- [ ] Added validation sign-off comment to guide file
- [ ] If VALID: All assumptions confirmed, no open questions
- [ ] If NEEDS CLARIFICATION: Listed specific questions that must be answered
- [ ] If NEEDS UPDATE: Applied all fixes, marked which ones

---

## Final Critical Questions

**Answer every question. If ANY answer is NO, do not mark as VALID.**

1. **Have you extracted and verified EVERY assumption the guide makes?**
   - (Not just surface-level assumptions - implicit ones too)

2. **For each feature the guide depends on, have you confirmed it's actually implemented?**
   - (Not assumed, not "probably" - actually verified in code)

3. **Have you read actual code implementations, not just pattern-matched?**
   - (Do you understand HOW it actually works?)

4. **Are there ANY open questions or unverified assumptions remaining?**
   - (If YES, status must be NEEDS CLARIFICATION, not VALID)

5. **Have you checked logic and edge cases?**
   - (Are there race conditions, off-by-one errors, null checks needed?)

6. **Have you identified and documented all potential risks?**
   - (Edge cases, race conditions, incompatibilities)

7. **Does the guide's proposed approach fit with existing architecture?**
   - (Or will it require significant refactoring?)

8. **Is the validation report complete with specific, actionable findings?**
   - (Not vague statements - specific file references and issues)

9. **If you applied updates to the guide, did you verify they're correct?**
   - (Re-read the updated section to confirm)

10. **Have you ONLY edited the guide file itself?**
    - (NOT the actual codebase - answer should be YES)

**Only proceed if you can answer YES to ALL questions.**

---

## Status Sanity Check

**VALID status requires:**
- ✅ All file paths exist
- ✅ All code patterns verified correct
- ✅ All assumptions confirmed in codebase
- ✅ All dependencies implemented
- ✅ No open questions
- ✅ No unresolved contradictions
- ✅ Feasibility confirmed

**NEEDS CLARIFICATION status when:**
- ❓ Critical questions remain unanswered
- ❓ Key assumptions can't be verified
- ❓ Dependencies can't be found
- ❓ Behavior is ambiguous

**NEEDS UPDATE status when:**
- ❌ Contradictions found between guide and codebase
- ❌ Missing dependencies
- ❌ Incorrect code examples
- ❌ Wrong file paths
- ❌ Outdated assumptions
- (After fixes applied, change to VALID)

**NEVER leave a guide with mismatched status.**

---

## Important Principles

### Healthy Skepticism

**Question EVERYTHING:**
- Don't assume a feature exists just because the guide mentions it
- Don't assume logic will work just because it sounds reasonable
- Don't assume implicit patterns - read actual code
- If you can't verify something, flag it as unverified

### The "Assume False Until Proven" Approach

Start with the assumption that anything not explicitly verified in the codebase is FALSE:
- Feature exists? False until you find it in code.
- Logic correct? False until you verify it and read the code.
- Assumption valid? False until you confirm in the codebase.

### Communication Over Confidence

If you're uncertain:
- Say "NEEDS CLARIFICATION" instead of guessing
- Document the specific questions
- Make it clear what additional information is needed
- Better to ask than to be confidently wrong

### Remember the User

The user has to implement this guide. If the guide is inaccurate:
- They waste time implementing something that doesn't work
- They discover assumptions were false partway through
- They waste more time fixing/debugging

A thorough validation prevents that.

---

## Execute Validation

**Guide to validate:** `$ARGUMENTS`

**Follow every step in the Process section above.**

**Do not skip steps.**

**Check every assumption.**

**Read actual code, don't pattern-match.**

**When done, provide the completed validation report with all sections filled in.**

**Report status as:**
- ✅ **VALID** - Ready to implement
- ⚠️ **NEEDS CLARIFICATION** - Questions remain, don't implement yet
- ❌ **NEEDS UPDATE** - Issues found, guide updated (then marked VALID)
