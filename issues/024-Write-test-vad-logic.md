# Issue 024: Write test_vad_logic.py (Tier 3)

## Sprint
Sprint 3 — Test Suite

## Priority
High

## References
- [docs/14-test-suite.md — Tier 3: Keyword & State Machine Tests](../docs/14-test-suite.md#tier-3-keyword--state-machine-tests)
- `cyrus2/cyrus_voice.py` (VAD state machine, ring buffer, silence detection)
- Silero VAD model integration

## Description
Tier 3 tests for VAD (Voice Activity Detection) state machine. Mock the Silero model and test ring buffer management, adaptive silence thresholds, timeout logic, and state transitions. Approximately 15 test cases covering normal speech, silence, edge cases, and model failures.

## Blocked By
- Issue 005 (cyrus_common.py foundation)
- Issue 018 (conftest.py fixtures)

## Acceptance Criteria
- [ ] `cyrus2/tests/test_vad_logic.py` exists with 15+ test cases
- [ ] VAD state machine transitions tested (~5 cases): idle→listening→speaking, timeouts
- [ ] Ring buffer management tested (~3 cases): chunk queuing, size limits, FIFO behavior
- [ ] Silence detection tested (~3 cases): silence threshold, adaptive behavior, pre-speech buffer
- [ ] Timeout behavior tested (~2 cases): speech timeout, silence timeout
- [ ] Edge cases tested (~2 cases): no audio, rapid transitions, Silero model mock failures
- [ ] All tests pass: `pytest tests/test_vad_logic.py -v`

## Implementation Steps
1. Create `cyrus2/tests/test_vad_logic.py`
2. Import VAD components from cyrus_voice.py:
   ```python
   from unittest.mock import Mock, patch
   from cyrus_voice import VADStateMachine, RingBuffer  # or equivalent classes
   ```
3. Create conftest fixture for mocked Silero model:
   ```python
   @pytest.fixture
   def mock_silero_model():
       model = Mock()
       model.return_value = {"confidence": 0.8}  # or appropriate return format
       return model
   ```
4. Write state machine tests (~5 cases):
   - Transition from idle to listening on first audio chunk
   - Transition from listening to speaking on high confidence
   - Transition to silence on low confidence
   - Timeout from speaking to idle after N seconds
   - Recovery to speaking after brief silence (pre-speech buffer)
5. Write ring buffer tests (~3 cases):
   - Append chunks maintains FIFO order
   - Buffer respects max_size limit
   - get_frames() returns correct number of frames
   - Clear buffer resets to empty state
6. Write silence detection tests (~3 cases):
   - Silence threshold (e.g., confidence < 0.5) correctly detected
   - Adaptive threshold adjusts based on environment noise estimate
   - Pre-speech buffer holds N chunks before declaring speech
   - Silence counter increments correctly
7. Write timeout tests (~2 cases):
   - Speaking timeout (e.g., 5 seconds of silence ends utterance)
   - Listening timeout (e.g., 30 seconds with no audio resets)
8. Write edge cases (~2 cases):
   - All-silence audio (no speech detected)
   - Rapid on/off transitions (stutter/backtrack)
   - Silero model raises exception (graceful degradation)
9. Mock audio chunks as numpy arrays or simple lists

## Files to Create/Modify
- `cyrus2/tests/test_vad_logic.py` (new)
- Update `cyrus2/tests/conftest.py` to add mock_silero_model fixture

## Testing
```bash
pytest cyrus2/tests/test_vad_logic.py -v
pytest cyrus2/tests/test_vad_logic.py::test_state_transitions -v
pytest cyrus2/tests/test_vad_logic.py -k "buffer or silence" -v
pytest cyrus2/tests/test_vad_logic.py -k "timeout" -v
```
