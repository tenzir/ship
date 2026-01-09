# Stats Command Execution Plan

**THIS PLAN FILE**: `.ai/stats-command-plan.md`
**Created**: 2026-01-09
**Type**: feature
**Estimated Complexity**: moderate

## CRITICAL: Execution Protocol

### The Three Commandments

1. **RELOAD BEFORE EVERY ACTION**: This plan is your only memory
2. **UPDATE AFTER EVERY ACTION**: If not written, it didn't happen
3. **TRUST ONLY THE PLAN**: Not memory, only what's written here

## Context

### Objective

Convert the `--stats` CLI flag into a proper `stats` subcommand with two view modes:

- **Vertical/card view**: For single projects (no modules) - stats displayed as rows for readability
- **Table view**: For multi-module projects - one row per module for comparison

### Current State

- `--stats` is a flag on the main CLI group in `_core.py`
- `_show_stats_table()` function renders a table with 2-row headers
- Always shows table view regardless of whether modules exist

### Success Criteria

1. `ship stats` command works with auto-detection (vertical for single, table for modules)
2. `ship stats --table` forces table view even for single projects
3. `ship stats --json` exports structured JSON
4. `ship --stats` flag is removed
5. All existing tests pass, new tests added for stats command
6. Vertical view is readable and shows all stats (releases + changelog entries)

### Key References

- `src/tenzir_ship/cli/_core.py`: Current `_show_stats_table()` implementation (lines 383-527)
- `src/tenzir_ship/cli/__init__.py`: Command registration
- `tests/test_modules.py`: Existing stats tests (lines 208-243)

## Implementation Steps

### Step 1: Create new `_stats.py` module

**Status:** ✅ DONE
**Description:** Extract stats functionality into its own module for cleaner organization
**Actions:**

- Create `src/tenzir_ship/cli/_stats.py`
- Move `_show_stats_table()` from `_core.py` to `_stats.py`
- Add imports and module structure

**Success Criteria:** Module exists and imports work
**Dependencies:** None
**Result:** [To be filled]

### Step 2: Implement vertical/card view for single projects

**Status:** ✅ DONE
**Description:** Create a new `_show_stats_vertical()` function for readable single-project display
**Actions:**

- Implement vertical view with sections:
  - Project header: `{id} {version}`
  - Releases section: Count, Last, Age
  - Changelog Entries section: Total, type breakdown with percentages, Shipped/Unreleased
- Use Rich panels/rules for visual separation
- Format similar to:

  ```
  Project root: /path/to/changelog

  ship v0.19.1

  ── Releases ─────────────────────────
    Count:        29
    Last:         2026-01-04
    Age:          5 days

  ── Changelog Entries ────────────────
    Total:        77  (20 shipped, 4 unreleased)
    💥 Breaking:   4  (16%)
    🚀 Feature:    5  (20%)
    🔧 Change:    14  (58%)
    🐞 Bugfix:     1  (4%)
  ```

**Success Criteria:** Vertical view renders correctly for single project
**Dependencies:** Step 1
**Result:** [To be filled]

### Step 3: Implement JSON export

**Status:** ✅ DONE
**Description:** Add `_show_stats_json()` function for structured JSON output
**Actions:**

- Create JSON structure with all stats data
- Include: project info, releases stats, entries stats (by type), shipped/unreleased counts
- For modules: array of project objects
- Output via `emit_output()` for proper stdout handling

**Success Criteria:** `--json` produces valid, parseable JSON
**Dependencies:** Step 1
**Result:** [To be filled]

### Step 4: Create `stats` command with options

**Status:** ✅ DONE
**Description:** Define the Click command with `--table` and `--json` options
**Actions:**

- Create `stats` command in `_stats.py`
- Add `--table` flag (force table view)
- Add `--json` flag (JSON export)
- Implement auto-detection logic:
  - If `--json`: call `_show_stats_json()`
  - Elif `--table` or has modules: call `_show_stats_table()`
  - Else: call `_show_stats_vertical()`
- Register command in `__init__.py`

**Success Criteria:** Command works with all option combinations
**Dependencies:** Steps 1-3
**Result:** [To be filled]

### Step 5: Remove `--stats` flag from main CLI

**Status:** ✅ DONE
**Description:** Clean up the old implementation
**Actions:**

- Remove `--stats` option from `_create_cli_group()` in `_core.py`
- Remove `stats` parameter from `_cli()` function
- Remove the `if stats:` handler block
- Keep any shared helper functions (like `format_age()`) accessible

**Success Criteria:** Old flag is gone, no import errors
**Dependencies:** Step 4
**Result:** [To be filled]

### Step 6: Update tests

**Status:** ✅ DONE
**Description:** Update existing tests and add new ones for the stats command
**Actions:**

- Update `test_cli_stats_option_shows_parent` → test `stats` command
- Update `test_cli_stats_option_lists_modules` → test `stats` command with modules
- Add test for `--table` flag forcing table view
- Add test for `--json` output structure
- Add test for vertical view (single project, no modules)

**Success Criteria:** All tests pass, coverage for new functionality
**Dependencies:** Steps 4-5
**Result:** [To be filled]

### Step 7: Verification and cleanup

**Status:** ✅ DONE
**Description:** Final verification across all scenarios
**Actions:**

- Test `ship stats` in `changelog/` directory (single project)
- Test `ship stats` in `~/code/tenzir/claude-plugins` (with modules)
- Test `ship stats --table` in single project
- Test `ship stats --json` in both scenarios
- Run full test suite
- Remove any dead code

**Success Criteria:** All manual tests work, full test suite passes
**Dependencies:** Step 6
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

- Total Steps: 7
- Completed: 7
- In Progress: 0
- Blocked: 0
- Success Rate: 100%

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

- Auto-detect view mode based on modules (vertical for single, table for multi)
- `--table` forces table view even for single projects
- `--json` for structured export
- Vertical view uses Rich rules for section headers

### Files Modified

- [ ] `src/tenzir_ship/cli/_stats.py` - new file for stats command
- [ ] `src/tenzir_ship/cli/_core.py` - remove --stats flag
- [ ] `src/tenzir_ship/cli/__init__.py` - register stats command
- [ ] `tests/test_modules.py` - update stats tests

## Completion Checklist

Before marking complete:

- [ ] All steps marked as ✅ DONE or ⏭️ SKIPPED
- [ ] `ship stats` works for single projects (vertical view)
- [ ] `ship stats` works for multi-module projects (table view)
- [ ] `ship stats --table` forces table view
- [ ] `ship stats --json` exports valid JSON
- [ ] All tests passing
- [ ] No dead code remaining

---

## Anti-Patterns to Avoid

- ❌ Don't batch multiple updates - update after each action
- ❌ Don't rely on memory - the plan is your only truth
- ❌ Don't skip recording results
- ❌ Don't have multiple IN_PROGRESS steps
- ❌ Don't proceed if a dependency failed
- ❌ Don't forget to remove the old `--stats` flag after new command works

Remember: This plan enables ANY AI to continue your work seamlessly.
