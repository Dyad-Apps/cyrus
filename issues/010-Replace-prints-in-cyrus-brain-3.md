---
id=010-Replace-prints-in-cyrus-brain-3
title=Convert 19 existing logging.xyz() root-logger calls to named log.xyz() in cyrus_brain.py
state=NEW
parent=010-Replace-prints-in-cyrus-brain
children=
split_count=0
---

# Convert 19 existing logging.xyz() root-logger calls to named log.xyz() in cyrus_brain.py

## Sprint
Sprint 2 — Quality & Safety

## Priority
High

## Parent
010-Replace-prints-in-cyrus-brain

## References
- docs/16-logging-system.md — logging conventions
- cyrus2/cyrus_brain.py — file to modify (lines 309-472)
- plans/010-Replace-prints-in-cyrus-brain.md — scope definition

## Description
Nineteen existing `logging.xyz()` calls (using the root logger) were added to `cyrus2/cyrus_brain.py` by Issues 007/008. These need to be switched to the named `log` logger (`log = logging.getLogger("cyrus.brain")`). This is purely mechanical: `logging.debug(...)` → `log.debug(...)`, etc. These calls already use `%s`-style formatting — no format changes needed. Requires children 1 and 2 to be complete.

## Blocked By
- 010-Replace-prints-in-cyrus-brain-1 — `log` must be defined first
- 010-Replace-prints-in-cyrus-brain-2 — complete print replacement first to avoid conflicts

## Acceptance Criteria
- [ ] All `logging.debug(...)`, `logging.info(...)`, `logging.warning(...)`, `logging.error(...)`, `logging.exception(...)` calls in `cyrus2/cyrus_brain.py` replaced with `log.*()` equivalents
- [ ] `grep -c "logging\.\(debug\|info\|warning\|error\|exception\)" cyrus2/cyrus_brain.py` → 0
- [ ] No changes to message content or arguments (these already use `%s` formatting)
- [ ] `ruff check cyrus2/cyrus_brain.py` passes with no errors
- [ ] `ruff format --check cyrus2/cyrus_brain.py` passes
- [ ] Existing tests still pass: `python -m pytest cyrus2/tests/ -v`

## Implementation Steps
1. Search for all root-logger calls in `cyrus2/cyrus_brain.py` (approximately lines 309-472):
   ```bash
   grep -n "logging\.\(debug\|info\|warning\|error\|exception\)(" cyrus2/cyrus_brain.py
   ```
2. For each found call, apply the simple substitution:
   - `logging.debug(...)` → `log.debug(...)`
   - `logging.info(...)` → `log.info(...)`
   - `logging.warning(...)` → `log.warning(...)`
   - `logging.error(...)` → `log.error(...)`
   - `logging.exception(...)` → `log.exception(...)`
3. Do NOT change the arguments — these already use `%s`-style lazy formatting
4. Verify zero root-logger calls remain:
   ```bash
   grep -c "logging\.\(debug\|info\|warning\|error\|exception\)" cyrus2/cyrus_brain.py
   # Expected: 0
   ```
5. Run `ruff check cyrus2/cyrus_brain.py` and fix any issues
6. Run `ruff format cyrus2/cyrus_brain.py`
7. Run the existing test suite to confirm no regressions

## Files to Modify
- `cyrus2/cyrus_brain.py` — convert ~19 `logging.xyz()` calls to `log.xyz()`

## Testing
```bash
# Zero root-logger calls
grep -c "logging\.\(debug\|info\|warning\|error\|exception\)" cyrus2/cyrus_brain.py
# Expected: 0

# Lint
ruff check cyrus2/cyrus_brain.py

# Existing tests
python -m pytest cyrus2/tests/ -v
```
