# Issue 005: Extract shared code into cyrus_common.py

## Sprint
Cyrus 2.0 Rewrite — Sprint 1

## Priority
Critical

## References
- docs/12-code-audit.md — C3 (90% code duplication)
- docs/15-recommendations.md — #1 (extract cyrus_common.py)

## Description
`main.py` and `cyrus_brain.py` duplicate ~2,000 lines of identical helper functions, classes, and constants. Extract all shared logic into a new `cyrus_common.py` module. Both entry points then import from it, eliminating duplication and making every subsequent refactor a single-file change.

## Blocked By
None

## Acceptance Criteria
- [ ] `cyrus2/cyrus_common.py` created with all shared functions and classes
- [ ] All functions/classes from the C3 duplication table extracted
- [ ] Both `cyrus2/main.py` and `cyrus2/cyrus_brain.py` import from `cyrus_common.py`
- [ ] No duplicate function/class definitions across files
- [ ] ~2,000 lines of duplication eliminated
- [ ] All tests pass (unit tests for pure functions added in Issue 009)

## Implementation Steps

1. **Create** `/home/daniel/Projects/barf/cyrus/cyrus2/cyrus_common.py`

2. **Extract all helper functions** (copy from source, update imports as needed):
   - `_extract_project(title: str) -> str`
   - `_make_alias(proj: str) -> str`
   - `_resolve_project(query: str, aliases: dict) -> str | None`
   - `_vs_code_windows() -> list[tuple[str, str]]`
   - `clean_for_speech(text: str) -> str`
   - `_sanitize_for_speech(text: str) -> str`
   - `_strip_fillers(text: str) -> str`
   - `_is_answer_request(text: str) -> bool`
   - `_fast_command(text: str, aliases: dict) -> tuple[str, list[str]] | None`
   - `play_chime()` (handles both audio playback and fallback)
   - `play_listen_chime()`

3. **Extract all classes**:
   - `ChatWatcher` (polls VS Code chat input field)
   - `PermissionWatcher` (monitors permission dialogs)
   - `SessionManager` (manages chat history per project)

4. **Extract all constants**:
   - `_FILLER_RE` (regex pattern for speech fillers)
   - `_HALLUCINATIONS` (set of common Whisper misrecognitions)
   - `_CHAT_INPUT_HINT`
   - `VSCODE_TITLE`
   - `MAX_SPEECH_WORDS` (keep configurable in main.py / cyrus_brain.py for override)

5. **Update imports** in `cyrus2/main.py`:
   ```python
   from cyrus_common import (
       _extract_project, _make_alias, _resolve_project, _vs_code_windows,
       clean_for_speech, _strip_fillers, _is_answer_request, _fast_command,
       play_chime, play_listen_chime,
       ChatWatcher, PermissionWatcher, SessionManager,
       _FILLER_RE, _HALLUCINATIONS
   )
   ```

6. **Update imports** in `cyrus2/cyrus_brain.py`:
   ```python
   from cyrus_common import (
       _extract_project, _make_alias, _resolve_project, _vs_code_windows,
       clean_for_speech, _strip_fillers,
       ChatWatcher, PermissionWatcher, SessionManager,
       _FILLER_RE, _HALLUCINATIONS
   )
   ```

7. **Remove** all duplicate definitions from `cyrus2/main.py` and `cyrus2/cyrus_brain.py`

8. **Verify** no import errors by running:
   ```bash
   cd /home/daniel/Projects/barf/cyrus/cyrus2
   python -c "import cyrus_common; print('OK')"
   ```

## Files to Create/Modify
- Create: `cyrus2/cyrus_common.py` (1,500–2,000 lines)
- Modify: `cyrus2/main.py` (add imports, remove duplicates)
- Modify: `cyrus2/cyrus_brain.py` (add imports, remove duplicates)

## Testing
- Import `cyrus_common` in both `main.py` and `cyrus_brain.py` without errors
- Verify duplicate definitions are gone: `grep -r "^def _extract_project" cyrus2/`
- Run linter on all three files: `pylint cyrus_common.py main.py cyrus_brain.py`
- Line count comparison (before vs after): `wc -l cyrus2/*.py`
