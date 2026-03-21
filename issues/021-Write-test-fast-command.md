# Issue 021: Write test_fast_command.py (Tier 1)

## Sprint
Sprint 3 — Test Suite

## Priority
Critical

## References
- [docs/14-test-suite.md — Tier 1: Pure Function Tests](../docs/14-test-suite.md#tier-1-pure-function-tests-zero-mocking)
- `cyrus2/cyrus_brain.py:290-330` (_fast_command function)

## Description
Tier 1 pure function tests for _fast_command() meta-command routing. Approximately 25+ test cases covering pause, unlock, which_project, last_message, switch, rename, and non-command edge cases. Zero mocking required.

## Blocked By
- Issue 005 (cyrus_common.py foundation)
- Issue 018 (conftest.py fixtures)

## Acceptance Criteria
- [ ] `cyrus2/tests/test_fast_command.py` exists with 25+ test cases
- [ ] Each command type has 2-3 test cases: happy path, edge case, invalid format
- [ ] Commands tested: pause, unlock, which_project, last_message, switch, rename
- [ ] Non-command strings return None or empty dict
- [ ] All tests pass: `pytest tests/test_fast_command.py -v`
- [ ] Test names indicate command type and scenario

## Implementation Steps
1. Create `cyrus2/tests/test_fast_command.py`
2. Import function from `cyrus_brain.py`:
   ```python
   from cyrus_brain import _fast_command
   ```
3. Write test cases organized by command type:
   - **pause** (~3 cases):
     - "pause" → {command: "pause"}
     - "pause for 10 seconds" → {command: "pause", duration: 10}
     - "pause xyz" → error/None (invalid format)
   - **unlock** (~2 cases):
     - "unlock" → {command: "unlock"}
     - "unlock password" → {command: "unlock", password: "password"}
   - **which_project** (~2 cases):
     - "which project" / "what project" → {command: "which_project"}
     - Case variations
   - **last_message** (~2 cases):
     - "last message" / "repeat that" / "what did you say" → {command: "last_message"}
   - **switch** (~4 cases):
     - "switch to myproject" → {command: "switch", project: "myproject"}
     - "switch myproject" → same
     - "switch" alone → error
   - **rename** (~4 cases):
     - "rename to newname" → {command: "rename", name: "newname"}
     - "rename project newname" → same
     - "rename" alone → error
   - **Non-commands** (~3 cases):
     - Regular conversation → None
     - Partial matches ("pausable" != "pause") → None
     - Empty string → None
4. Use parametrize for systematic coverage
5. Verify return type consistency (dict or None)

## Files to Create/Modify
- `cyrus2/tests/test_fast_command.py` (new)

## Testing
```bash
pytest cyrus2/tests/test_fast_command.py -v
pytest cyrus2/tests/test_fast_command.py::test_pause -v
pytest cyrus2/tests/test_fast_command.py -k "switch or rename" -v
```
