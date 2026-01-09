# Show Command Scope Refactor Execution Plan

**THIS PLAN FILE**: `.ai/show-scope-refactor-plan.md`
**Created**: 2026-01-09
**Type**: refactor
**Estimated Complexity**: moderate

## CRITICAL: Execution Protocol

### The Three Commandments

1. **RELOAD BEFORE EVERY ACTION**: This plan is your only memory
2. **UPDATE AFTER EVERY ACTION**: If not written, it didn't happen
3. **TRUST ONLY THE PLAN**: Not memory, only what's written here

## Context

### Objective

Refactor the `show` command to cleanly separate scope (what to show) from presentation (how to show it):

- **Positional identifiers** control scope: `unreleased`, `released`, `latest`, `all`, `v0.2.0`, row numbers
- **`--release` flag** controls presentation: grouping by release, including release metadata

### Current State

- Scope is controlled by flags: `--all`, `--released`, `--unreleased`, `--latest`
- `--release` conflates scope and presentation (defaults to latest in some views)
- Special tokens like `unreleased` are rejected with "use --unreleased flag instead"
- Inconsistent behavior between table/card/markdown/json views

### Success Criteria

1. `show` → all entries, flat list
2. `show --release` → all entries, grouped by release
3. `show unreleased` → unreleased entries only
4. `show released` → released entries only
5. `show latest` → latest release entries
6. `show latest --release` → latest release with metadata
7. `show v0.2.0 v0.3.0` → entries from two specific releases
8. All views (table, card, markdown, json) behave consistently
9. Old flags removed: `--all`, `--released`, `--unreleased`, `--latest`
10. Tests pass

### Key References

- `src/tenzir_ship/cli/_show.py` - main show command implementation
- `src/tenzir_ship/cli/_core.py` - shared utilities, help text builder
- `tests/` - test suite

## Implementation Steps

### Step 1: Update identifier resolution to accept scope tokens

**Status:** ⏳ TODO
**Description:** Modify `_resolve_identifier` to recognize `unreleased`, `released`, `latest`, `all` as valid scope identifiers instead of rejecting them.
**Actions:**

- Edit `_resolve_identifier` in `_show.py`
- Add new `IdentifierKind` values: `"scope_unreleased"`, `"scope_released"`, `"scope_latest"`, `"scope_all"`
- Return appropriate `IdentifierResolution` for each scope token
- Remove the rejection logic for `unreleased` token

**Success Criteria:** `_resolve_identifier("unreleased", ...)` returns a valid resolution
**Dependencies:** None
**Result:** [To be filled]

### Step 2: Create scope resolution helper

**Status:** ⏳ TODO
**Description:** Create a function that processes identifiers and extracts scope information separately from entry identifiers.
**Actions:**

- Create `_extract_scope_from_identifiers()` function
- Returns: `(scope: str, remaining_identifiers: tuple[str, ...])`
- Scope values: `"all"`, `"unreleased"`, `"released"`, `"latest"`, `"specific"`
- Handle mixing scope tokens with version identifiers (e.g., `show released v0.2.0` should error or be handled gracefully)

**Success Criteria:** Function correctly separates scope tokens from entry identifiers
**Dependencies:** Step 1
**Result:** [To be filled]

### Step 3: Remove scope flags from command definition

**Status:** ⏳ TODO
**Description:** Remove `--all`, `--released`, `--unreleased`, `--latest` flags from the `show` command.
**Actions:**

- Edit `_create_show_command()` in `_show.py`
- Remove the four `@click.option` decorators for these flags
- Remove corresponding parameters from `show_entries_cmd` function
- Update `run_show_entries` signature to remove `select_all`, `select_released`, `select_unreleased`, `select_latest` parameters

**Success Criteria:** Command no longer accepts these flags
**Dependencies:** Step 2
**Result:** [To be filled]

### Step 4: Refactor `run_show_entries` to use positional scope

**Status:** ⏳ TODO
**Description:** Update the main entry point to determine scope from identifiers instead of flags.
**Actions:**

- Call `_extract_scope_from_identifiers()` at the start
- Replace flag-based logic with scope-based logic
- Ensure `--release` only affects presentation, not scope

**Success Criteria:** `run_show_entries` correctly interprets positional scope
**Dependencies:** Steps 2, 3
**Result:** [To be filled]

### Step 5: Update table view (`_show_entries_table`)

**Status:** ⏳ TODO
**Description:** Refactor table view to use the new scope model.
**Actions:**

- Remove `select_all`, `select_released`, `select_unreleased`, `select_latest` parameters
- Add `scope` parameter
- Update internal logic to filter based on scope
- Ensure `--release` only adds Release column and grouping

**Success Criteria:** Table view works with new scope model
**Dependencies:** Step 4
**Result:** [To be filled]

### Step 6: Update card view (`_show_entries_card`)

**Status:** ⏳ TODO
**Description:** Refactor card view to use the new scope model.
**Actions:**

- Remove flag-based parameters
- Add `scope` parameter
- Remove the "default to latest" logic - use scope instead
- Ensure consistent behavior with table view

**Success Criteria:** `show --card` and `show --card --release` work correctly with all scope values
**Dependencies:** Step 4
**Result:** [To be filled]

### Step 7: Update export views (`_show_entries_export`)

**Status:** ⏳ TODO
**Description:** Refactor markdown/json export to use the new scope model.
**Actions:**

- Remove flag-based parameters
- Add `scope` parameter
- Remove the "default to latest" logic
- Ensure consistent behavior with other views

**Success Criteria:** `show --markdown` and `show --json` work correctly with all scope values
**Dependencies:** Step 4
**Result:** [To be filled]

### Step 8: Update help text

**Status:** ⏳ TODO
**Description:** Update the command help text to document the new scope tokens.
**Actions:**

- Edit `_command_help_text` in `_core.py`
- Add scope tokens to IDENTIFIERS documentation
- Update examples to show new usage patterns

**Success Criteria:** `show -h` displays accurate, well-formatted help
**Dependencies:** Steps 3-7
**Result:** [To be filled]

### Step 9: Update and run tests

**Status:** ⏳ TODO
**Description:** Update existing tests and add new ones for the refactored behavior.
**Actions:**

- Update tests that use old flags to use positional scope
- Add tests for each scope token: `unreleased`, `released`, `latest`, `all`
- Add tests for combining scope with `--release` flag
- Run full test suite

**Success Criteria:** All tests pass
**Dependencies:** Steps 5-8
**Result:** [To be filled]

### Step 10: Manual verification

**Status:** ⏳ TODO
**Description:** Manually test all combinations to verify consistent behavior.
**Actions:**

- Test matrix:
  - Scopes: (none), `unreleased`, `released`, `latest`, `all`, `v0.x.0`
  - Views: (table), `--card`, `--markdown`, `--json`
  - Release mode: (off), `--release`
- Verify help text displays correctly

**Success Criteria:** All combinations work as expected per success criteria
**Dependencies:** Step 9
**Result:** [To be filled]

## Status Legend

- ⏳ **TODO**: Not started
- 🔄 **IN_PROGRESS**: Currently working (max 1)
- ✅ **DONE**: Completed successfully
- ❌ **FAILED**: Failed, needs retry
- ⏭️ **SKIPPED**: Not needed (explain why)
- 🚫 **BLOCKED**: Can't proceed (explain why)

## Progress Tracking

### Summary

- Total Steps: 10
- Completed: 0
- In Progress: 0
- Blocked: 0
- Success Rate: 0%

### Execution Log

[Record all actions with timestamps]

## Recovery Instructions

If resuming this plan:

1. Read this entire file first
2. Check the Execution Log for last action
3. Find the 🔄 IN_PROGRESS or next ⏳ TODO step
4. Continue from that point
5. Update immediately after each action

## Context Preservation

### Key Decisions Made

- Scope tokens are positional: `unreleased`, `released`, `latest`, `all`
- `--release` is purely presentation (grouping + metadata)
- Default scope (no identifier) = all entries
- Scope tokens cannot be mixed (e.g., `show unreleased released` is invalid)

### Files Modified

- [ ] `src/tenzir_ship/cli/_show.py` - main refactoring
- [ ] `src/tenzir_ship/cli/_core.py` - help text update
- [ ] `tests/` - test updates

## Completion Checklist

Before marking complete:

- [ ] All steps marked as ✅ DONE or ⏭️ SKIPPED
- [ ] Success criteria met (all 10 items)
- [ ] Tests passing
- [ ] Help text accurate and well-formatted
- [ ] Manual verification complete

---

## Anti-Patterns to Avoid

- ❌ Don't conflate scope and presentation in `--release`
- ❌ Don't have different default behavior per view
- ❌ Don't batch multiple updates - update after each action
- ❌ Don't rely on memory - the plan is your only truth

Remember: This plan enables ANY AI to continue your work seamlessly.
