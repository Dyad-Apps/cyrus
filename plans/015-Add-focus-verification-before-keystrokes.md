# Implementation Plan: Add focus verification before keystrokes

**Issue**: [015-Add-focus-verification-before-keystrokes](/home/daniel/Projects/barf/cyrus/issues/015-Add-focus-verification-before-keystrokes.md)
**Created**: 2026-03-16
**PROMPT**: PROMPT_plan (barf auto/plan)

## Gap Analysis

**Already exists**:
- Inline, best-effort focus via `win.activate()` and `SetFocus()` in try/except blocks that silently swallow failures — no verification that focus actually landed
- Active window tracker thread (`_start_active_tracker()`) polling `gw.getActiveWindow()` every 0.5s, but only for project name tracking — not used as a safety gate
- `uiautomation==2.0.29` library imported and configured in both `cyrus_brain.py` and `cyrus_common.py`
- `pygetwindow` used for window enumeration/activation
- COM STA thread for UIA operations (`_submit_worker`)

**Needs building**:
1. A centralized `_assert_vscode_focus()` guard function using UIAutomation
2. Integration at all pyautogui call sites (10 total across 2 files)
3. Graceful error handling (catch RuntimeError, log, abort operation)
4. Unit tests with mocked UIAutomation (tests run on Linux CI)

## Approach

**Define `_assert_vscode_focus()` in `cyrus_common.py`** (not `cyrus_brain.py` as the issue originally suggests) because:
- `cyrus_brain.py` imports from `cyrus_common.py`, not the other way around
- Both files need the function — defining in `cyrus_common.py` avoids circular imports
- `cyrus_common.py` is the shared utilities module by design (Issue 005 extracted it for this purpose)
- The issue's line references (`cyrus_brain.py:928`, `main.py:1295,1302`) are from the pre-refactor codebase; the refactored equivalents live in `cyrus_common.py`

**UIAutomation approach** (per acceptance criteria "Uses UIAutomation to get currently focused window"):
- Use `auto.GetFocusedControl()` to get the deepest focused UI element
- Walk up the UIA tree via `GetParentControl()` to find the top-level `WindowControl`
- Check if the window name contains "Visual Studio Code"
- Raise `RuntimeError` with the actual window name if verification fails
- Log which window had focus via `log.error()` before raising

**Call sites** — call `_assert_vscode_focus()` before every pyautogui keystroke sequence:

In `cyrus2/cyrus_brain.py` — `_submit_to_vscode_impl()`:
1. Before `pyautogui.click(*coords)` (line ~688) — first keystroke in submit sequence
2. Before `pyautogui.press("enter")` (line ~707) — re-verify before commit action

In `cyrus2/cyrus_common.py` — `PermissionWatcher.handle_response()`:
3. Before `pyautogui.press("1")` (line ~996) — approve keyboard path
4. Before `pyautogui.press("enter")` (line ~1005) — approve fallback
5. Before `pyautogui.press("escape")` (line ~1017) — deny path

In `cyrus2/cyrus_common.py` — `PermissionWatcher.handle_prompt_response()`:
6. Before `pyautogui.press("escape")` (line ~1040) — cancel path
7. Before `pyautogui.hotkey("ctrl", "a")` (line ~1047) — answer sequence start

**Not modifying root `main.py`**: The root-level `main.py` is the pre-refactored monolith. The build/test/lint commands in `.barfrc` all target `cyrus2/`. The "main.py equivalents" referenced in the issue are now in `cyrus2/cyrus_common.py` (PermissionWatcher).

## Rules to Follow

- `.claude/rules/` — Empty (no project rules defined)
- `docs/12-code-audit.md` H2 finding — the source requirement for this issue
- `python-expert` skill — Python best practices (type hints, error handling, docstrings)
- `python-testing` skill — pytest patterns (mocking, fixtures, acceptance-driven)
- `python-patterns` skill — EAFP, context managers, error re-raising

## Skills & Agents to Use

| Task | Skill/Agent | Purpose |
|------|-------------|---------|
| Function implementation | `python-expert` | Type hints, docstrings, error handling patterns |
| Test writing | `python-testing` | Mock-based unit tests, pytest patterns |
| Code quality | `python-linting` | Run `ruff check` and `ruff format --check` |
| Windows API mocking | `python-patterns` | EAFP, mock setup for `uiautomation` |

## Prioritized Tasks

- [ ] 1. Define `_assert_vscode_focus()` in `cyrus2/cyrus_common.py` as a module-level function
  - Use `auto.GetFocusedControl()` + parent walk to find top-level window
  - Check name contains "Visual Studio Code"
  - Raise `RuntimeError` with focused window name on failure
  - `log.error()` the mismatched window name before raising
  - Handle UIA exceptions gracefully (log warning, re-raise as RuntimeError)
  - Add to `__all__` or import list if applicable

- [ ] 2. Import and call in `cyrus2/cyrus_brain.py` — `_submit_to_vscode_impl()`
  - Add `_assert_vscode_focus` to imports from `cyrus_common`
  - Call before `pyautogui.click(*coords)` (first keystroke in sequence)
  - Call before `pyautogui.press("enter")` (re-verify before submit)
  - Wrap calls in try/except RuntimeError → log and return/abort

- [ ] 3. Call in `cyrus2/cyrus_common.py` — `PermissionWatcher.handle_response()`
  - Before `pyautogui.press("1")` (approve keyboard path)
  - Before `pyautogui.press("enter")` (approve fallback)
  - Before `pyautogui.press("escape")` (deny path)
  - Wrap in try/except RuntimeError → log and return

- [ ] 4. Call in `cyrus2/cyrus_common.py` — `PermissionWatcher.handle_prompt_response()`
  - Before `pyautogui.press("escape")` (cancel path)
  - Before `pyautogui.hotkey("ctrl", "a")` (answer sequence start)
  - Wrap in try/except RuntimeError → log and return

- [ ] 5. Write unit tests in `cyrus2/tests/test_015_focus_verification.py`
  - Test function exists and is callable
  - Test passes when mock UIA returns VS Code window
  - Test raises RuntimeError when different window focused
  - Test logs window name on failure (check log.error call)
  - Test handles UIA exceptions gracefully
  - Test structural: verify _assert_vscode_focus calls precede pyautogui calls in source

- [ ] 6. Run validation: ruff check, ruff format, pytest

## Acceptance-Driven Tests

| Acceptance Criterion | Required Test | Type |
|---------------------|---------------|------|
| Function `_assert_vscode_focus()` created | `test_function_exists_and_callable` | unit |
| Uses UIAutomation to get focused window | `test_calls_get_focused_control` | unit (mock) |
| Verifies title contains "Visual Studio Code" | `test_passes_when_vscode_focused` | unit (mock) |
| Raises RuntimeError if focus is not VS Code | `test_raises_when_wrong_window_focused` | unit (mock) |
| Logs which window had focus on failure | `test_logs_focus_mismatch_on_failure` | unit (mock) |
| Called before every pyautogui keystroke sequence | `test_assert_precedes_pyautogui_in_brain` + `test_assert_precedes_pyautogui_in_common` | structural (AST) |
| All clipboard manipulation preceded by focus check | `test_clipboard_ops_preceded_by_focus_check` | structural (AST) |
| No misdirected input due to focus change | `test_submit_aborts_on_focus_failure` + `test_permission_aborts_on_focus_failure` | unit (mock) |
| Existing functionality preserved | `test_submit_succeeds_when_focused` + existing tests still pass | unit + regression |

**No cheating** — cannot claim done without all tests passing.

## Validation (Backpressure)

- Lint: `cyrus2/.venv/bin/python -m ruff check cyrus2/`
- Format: `cyrus2/.venv/bin/python -m ruff format --check cyrus2/`
- Tests: `cyrus2/.venv/bin/python -m pytest cyrus2/tests/`
- All 145+ existing tests must continue to pass
- New test file must have 100% pass rate

## Files to Create/Modify

- `cyrus2/cyrus_common.py` — Add `_assert_vscode_focus()` function definition
- `cyrus2/cyrus_brain.py` — Import `_assert_vscode_focus`, call before keystroke sequences in `_submit_to_vscode_impl()`
- `cyrus2/tests/test_015_focus_verification.py` — **NEW** — Unit tests for focus verification

## Key Decisions

1. **Function location**: `cyrus_common.py` instead of `cyrus_brain.py` — avoids circular import since brain imports from common, not vice versa. Both files need the function.

2. **UIAutomation API**: `auto.GetFocusedControl()` + parent walk — this is the standard way to identify which top-level window has focus via the `uiautomation` library. Alternative was `pygetwindow.getActiveWindow()` (simpler, already used in tracker thread) but the acceptance criteria explicitly requires UIAutomation.

3. **Call granularity**: Check before each keystroke *sequence* (group), plus re-check before Enter (the commit action). Not before every single `pyautogui.*` call — the 10-50ms between calls within a sequence has negligible focus-change risk, and excessive UIA COM calls would slow operations.

4. **Error handling**: RuntimeError caught at each call site, logged, and operation aborted gracefully. No crash, no silent continuation. Matches the issue requirement: "Catch RuntimeError and log/abort gracefully".

5. **Root `main.py` not modified**: Only `cyrus2/` files modified, per the project's refactoring direction. The build/test/lint pipeline in `.barfrc` targets `cyrus2/` exclusively.

6. **Test approach**: Mock-based unit tests + AST structural analysis. No live UIA tests (CI runs on Linux). Follows the pattern established in `test_007_command_handlers.py` and `test_008_init_functions.py`.
