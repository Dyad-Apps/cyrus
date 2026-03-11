# Issue 009: Create cyrus_log module

## Sprint
Sprint 2 — Quality & Safety

## Priority
High

## References
- docs/16-logging-system.md — Configuration section

## Description
Create a new `cyrus_log.py` module to centralize logging setup. This module will be imported by all entry points to configure the root "cyrus" logger with stderr output, conditional timestamps (DEBUG level only), and environment variable control via `CYRUS_LOG_LEVEL`.

## Blocked By
- None

## Acceptance Criteria
- [ ] `cyrus2/cyrus_log.py` created with `setup_logging()` function
- [ ] Accepts optional `name` parameter (defaults to "cyrus")
- [ ] Returns configured root logger
- [ ] Reads `CYRUS_LOG_LEVEL` env var (defaults to "INFO")
- [ ] Validates log level and falls back to INFO on invalid value
- [ ] Handler writes to stderr
- [ ] Format: `[{name}] {levelname:.1s} {message}` for INFO/WARNING/ERROR
- [ ] Format: `{asctime} [{name}] {levelname:.1s} {message}` for DEBUG and below
- [ ] Timestamp format: `%H:%M:%S` (hours:minutes:seconds)
- [ ] Handler attached to root logger with `propagate=False`
- [ ] File is ~40 lines

## Implementation Steps
1. Create `/home/daniel/Projects/barf/cyrus/cyrus2/cyrus_log.py`
2. Import `logging`, `sys`, `os`
3. Define `setup_logging(name: str = "cyrus") -> logging.Logger`
4. Read `CYRUS_LOG_LEVEL` env var, uppercase it
5. Use `getattr(logging, level_name, logging.INFO)` to validate
6. Build format string: check if `level <= logging.DEBUG` for conditional timestamp
7. Create `StreamHandler(sys.stderr)` with formatter
8. Get root logger via `getattr(logging, name)`
9. Set level, attach handler, set `propagate=False`
10. Return root logger
11. Add docstring explaining usage pattern (call once per entry point)

## Files to Create/Modify
- `cyrus2/cyrus_log.py` — create new

## Testing
```bash
# Test default INFO level
python -c "from cyrus2.cyrus_log import setup_logging; log = setup_logging('cyrus'); log.info('test')"
# Expected: [cyrus] I test

# Test DEBUG level with timestamp
CYRUS_LOG_LEVEL=DEBUG python -c "from cyrus2.cyrus_log import setup_logging; log = setup_logging('cyrus'); log.debug('test')"
# Expected: HH:MM:SS [cyrus] D test

# Test invalid level falls back to INFO
CYRUS_LOG_LEVEL=INVALID python -c "from cyrus2.cyrus_log import setup_logging; log = setup_logging('cyrus'); log.info('test')"
# Expected: [cyrus] I test (no error)

# Test child logger inherits from root
python -c "from cyrus2.cyrus_log import setup_logging; setup_logging('cyrus'); import logging; log = logging.getLogger('cyrus.brain'); log.info('from brain')"
# Expected: [cyrus.brain] I from brain
```
