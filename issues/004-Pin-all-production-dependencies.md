# Issue 004: Pin All Production Dependencies

## Sprint
Cyrus 2.0 Rewrite — Foundation (Week 1)

## Priority
High

## References
- docs/12-code-audit.md — Section H5 "All Dependencies Unpinned"
- /home/daniel/Projects/barf/cyrus/requirements.txt (v1 unpinned base)
- /home/daniel/Projects/barf/cyrus/requirements-voice.txt (v1 unpinned voice)
- /home/daniel/Projects/barf/cyrus/requirements-brain.txt (v1 unpinned brain)

## Description
Pinning all production dependencies to exact versions ensures reproducible builds, prevents silent breakage from upstream changes, and is especially critical for fragile packages (torch, faster-whisper, onnxruntime-gpu). Currently all three requirements files are unpinned, leading to non-deterministic installs and version conflicts.

## Blocked By
- None (but Issue 002 should be complete for consistency)

## Acceptance Criteria
- [ ] `cyrus2/requirements.txt` exists with exact pinned versions (all 17 packages)
- [ ] `cyrus2/requirements-voice.txt` exists with exact pinned versions (all 10 packages)
- [ ] `cyrus2/requirements-brain.txt` exists with exact pinned versions (all 8 packages)
- [ ] All versions obtained from active/working Python environment via `pip freeze`
- [ ] torch, faster-whisper, onnxruntime-gpu have confirmed compatible versions
- [ ] Each file can be installed with `pip install -r [file]` without version conflicts
- [ ] Git shows changed files (not new files) — tracking version updates over time

## Implementation Steps
1. Identify a working Python environment with all current dependencies installed
2. From that environment, run `pip freeze > /tmp/freeze.txt` to capture all installed versions
3. Extract pinned versions for base requirements:
   - pyautogui
   - pyperclip
   - pygetwindow
   - uiautomation
   - comtypes
   - python-dotenv
   - websockets
   Create `cyrus2/requirements.txt` with format: `package==X.Y.Z`
4. Extract pinned versions for voice requirements:
   - faster-whisper
   - sounddevice
   - numpy
   - torch
   - silero-vad
   - edge-tts
   - keyboard
   - pygame-ce
   - python-dotenv (already in base, but verify version match)
   - websockets (already in base, but verify version match)
   Create `cyrus2/requirements-voice.txt` with format: `package==X.Y.Z`
5. Extract pinned versions for brain requirements:
   - faster-whisper
   - sounddevice
   - numpy
   - torch
   - silero-vad
   - edge-tts
   - kokoro-onnx[gpu]
   - onnxruntime-gpu
   - keyboard
   - pygame-ce
   - pyautogui
   - pyperclip
   - pygetwindow
   - uiautomation
   - python-dotenv
   - websockets
   Create `cyrus2/requirements-brain.txt` with format: `package==X.Y.Z`
6. Cross-verify torch/onnxruntime-gpu/faster-whisper compatibility by checking changelog/issues
7. Test install (if possible):
   ```bash
   pip install -r cyrus2/requirements.txt
   pip install -r cyrus2/requirements-voice.txt
   pip install -r cyrus2/requirements-brain.txt
   ```

## Files to Create/Modify
- `cyrus2/requirements.txt` (create, pinned versions)
- `cyrus2/requirements-voice.txt` (create, pinned versions)
- `cyrus2/requirements-brain.txt` (create, pinned versions)

## Testing
```bash
# Verify files exist and contain pinned versions
cat cyrus2/requirements.txt | head -5
cat cyrus2/requirements-voice.txt | head -5
cat cyrus2/requirements-brain.txt | head -5

# Test syntax (Python can parse requirement files)
python -c "from pip._internal.req import parse_requirements; list(parse_requirements('cyrus2/requirements.txt', session=None))"

# If environment available: test install
pip install -r cyrus2/requirements.txt --dry-run

# Verify key fragile packages are pinned
grep torch cyrus2/requirements-*.txt
grep faster-whisper cyrus2/requirements-*.txt
grep onnxruntime cyrus2/requirements-brain.txt
```

## Notes
- **Fragile packages**: torch, faster-whisper, onnxruntime-gpu frequently have breaking changes. Pin exact versions.
- **Shared packages**: python-dotenv and websockets appear in multiple files. Ensure consistent versions across all three files.
- **GPU support**: kokoro-onnx[gpu] and onnxruntime-gpu are only in brain requirements. Ensure CUDA/cuDNN compatibility with pinned versions.
- **Version sourcing**: Use `pip freeze` from the current working environment. If this environment is known-good, capturing versions ensures reproducibility.
- **Future updates**: Consider `pip-compile` or `uv` for lockfile management if dependency updates become frequent.
- **Documentation**: Add a note in the project README about the three requirement files and when each is used (base, voice-only setup, brain-only setup).

## Fragile Package Guidance
When pinning these versions, verify compatibility:
- **torch**: Check CUDA version compatibility if using GPU (e.g., torch 2.x requires CUDA 11.8+)
- **faster-whisper**: Ensure compatible with the pinned numpy version
- **onnxruntime-gpu**: Must match GPU hardware and CUDA version
- **silero-vad**: Generally stable, but verify with pinned torch version
- **edge-tts**: Usually stable, minimal dependencies
- **kokoro-onnx**: GPU variant; ensure CUDA/ONNXRuntime compatibility
