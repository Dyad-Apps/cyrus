# Implementation Plan: Pin All Production Dependencies

**Issue**: [004-Pin-all-production-dependencies](/home/daniel/Projects/barf/cyrus/issues/004-Pin-all-production-dependencies.md)
**Created**: 2026-03-11
**Updated**: 2026-03-16 (all 17 versions verified against PyPI)

## Gap Analysis

**Already exists**:
- `cyrus2/` directory exists (empty)
- v1 requirements files at project root (all unpinned): `requirements.txt` (16 pkgs), `requirements-voice.txt` (10 pkgs), `requirements-brain.txt` (7 pkgs)

**Needs building**:
- `cyrus2/requirements.txt` — 7 base packages, pinned with `==`
- `cyrus2/requirements-voice.txt` — 10 voice packages, pinned with `==`
- `cyrus2/requirements-brain.txt` — 17 brain packages (superset), pinned with `==`

## Ambiguity Resolution

The issue has three internal conflicts resolved as follows:

1. **Package counts** (AC says 17/10/8, impl steps say 7/10/16, v1 files have 16/10/7): Follow the **restructured layout** — base=7 (UI automation), voice=10 (speech), brain=17 (superset of both + GPU inference). The v1 naming was confusing (`requirements.txt` was the superset); the rewrite fixes this by making `requirements-brain.txt` the superset. Implementation steps listed 16 for brain but omitted `comtypes` (a base dependency). Final counts: **7 / 10 / 17**.

2. **Create vs modify** (AC says "changed files" but cyrus2/ is empty): **Create new files in `cyrus2/`** per implementation steps. This is a rewrite sprint; v1 root files are untouched.

3. **GPU compatibility** (no working Python env to `pip freeze` from): **Use latest stable PyPI versions** cross-checked for CUDA 12 compatibility. Document the compatibility chain so the builder doesn't need to research.

## Approach

Write three plain-text requirements files with exact `package==X.Y.Z` pinning. Versions sourced from PyPI stable releases, verified against PyPI on 2026-03-16, and cross-verified for CUDA 12.x + cuDNN 9 GPU compatibility. This is a text-only change — no code, no tests to write. The builder creates 3 files and runs inline verification scripts.

**Why this approach**: No working Python environment exists, so `pip freeze` isn't viable. Researched versions from PyPI are the next best source, with GPU compatibility chains documented explicitly to prevent silent breakage.

## Version Table

All versions verified against PyPI as of 2026-03-16. Every version confirmed as the latest stable release.

| Package | Version | Verified | Notes |
|---|---|---|---|
| comtypes | 1.4.16 | ✅ | Windows COM interface; required by uiautomation (released 2026-03-02) |
| edge-tts | 7.2.7 | ✅ | Microsoft Edge TTS; minimal deps (released 2025-12-12) |
| faster-whisper | 1.2.1 | ✅ | Uses CTranslate2; needs CUDA 12 + cuDNN 9 for GPU |
| keyboard | 0.13.5 | ✅ | Unmaintained since 2020 but functional (released 2020-03-23) |
| kokoro-onnx[gpu] | 0.5.0 | ✅ | GPU extra pulls onnxruntime-gpu; requires Python >=3.10,<3.14 (released 2026-01-30) |
| numpy | 2.4.3 | ✅ | Compatible with torch 2.10.0 (released 2026-03-09) |
| onnxruntime-gpu | 1.24.3 | ✅ | CUDA 12.x + cuDNN 9; satisfies `onnxruntime` requirement for faster-whisper (released 2026-03-05) |
| pyautogui | 0.9.54 | ✅ | Cross-platform GUI automation (released 2023-05-24) |
| pygame-ce | 2.5.7 | ✅ | Community edition; requires Python >=3.10 (released 2026-03-02) |
| pygetwindow | 0.0.9 | ✅ | Window management (released 2020-10-04) |
| pyperclip | 1.11.0 | ✅ | Clipboard access (released 2025-09-26) |
| python-dotenv | 1.2.2 | ✅ | Shared across all three files (released 2026-03-01) |
| silero-vad | 6.2.1 | ✅ | Requires torch>=1.12.0; compatible with pinned torch |
| sounddevice | 0.5.5 | ✅ | PortAudio bindings (released 2026-01-23) |
| torch | 2.10.0 | ✅ | CUDA 12 support; satisfies silero-vad torch>=1.12.0 (released 2026-01-21) |
| uiautomation | 2.0.29 | ✅ | Windows UI automation; depends on comtypes |
| websockets | 16.0 | ✅ | Shared across all three files; requires Python >=3.10 (released 2026-01-10) |

### GPU Compatibility Chain

All GPU packages target **CUDA 12.x + cuDNN 9**:
- `torch==2.10.0` — built for CUDA 12
- `onnxruntime-gpu==1.24.3` — built for CUDA 12.x + cuDNN 9
- `faster-whisper==1.2.1` — uses CTranslate2 which requires CUDA 12 + cuDNN 9
- `kokoro-onnx[gpu]==0.5.0` — delegates to onnxruntime-gpu for GPU execution
- `silero-vad==6.2.1` — uses torch for inference (CUDA 12 via torch)

Note: `onnxruntime-gpu` and `onnxruntime` provide the same Python module. `faster-whisper` declares a dependency on `onnxruntime`, which is satisfied by `onnxruntime-gpu`. The v1 `requirements.txt` already lists both packages together, confirming this is a working combination.

## Rules to Follow

- No `.claude/rules/` in the cyrus project apply directly — this is a Python project; the rules directory only contains agent profiles
- General principle: exact version pinning is a hard requirement pattern (same philosophy applied to Python deps here)

## Skills & Agents to Use

| Task | Skill/Agent | Purpose |
|------|-------------|---------|
| File creation | Direct `Write` tool | Three plain text files — no complex logic needed |
| Verification | Inline `python3 -c` scripts | Validate pinning format, counts, cross-file consistency |

**Note**: This task is simple enough that a general builder agent can handle it. The files are pre-computed text — no research or package resolution needed at build time.

## Prioritized Tasks

- [ ] Create `cyrus2/requirements.txt` with 7 pinned base packages (alphabetical, `package==version`)
- [ ] Create `cyrus2/requirements-voice.txt` with 10 pinned voice packages
- [ ] Create `cyrus2/requirements-brain.txt` with 17 pinned brain packages (superset)
- [ ] Verify each file: exists, all lines contain `==`, correct package count
- [ ] Cross-file consistency check: shared packages (`python-dotenv`, `websockets`) have same versions, brain is superset of both base and voice
- [ ] Verify fragile packages present in brain: `torch`, `faster-whisper`, `onnxruntime-gpu`, `kokoro-onnx[gpu]`

## Exact File Contents

### `cyrus2/requirements.txt` (base — 7 packages)

```
comtypes==1.4.16
pyautogui==0.9.54
pygetwindow==0.0.9
pyperclip==1.11.0
python-dotenv==1.2.2
uiautomation==2.0.29
websockets==16.0
```

### `cyrus2/requirements-voice.txt` (voice — 10 packages)

```
edge-tts==7.2.7
faster-whisper==1.2.1
keyboard==0.13.5
numpy==2.4.3
pygame-ce==2.5.7
python-dotenv==1.2.2
silero-vad==6.2.1
sounddevice==0.5.5
torch==2.10.0
websockets==16.0
```

### `cyrus2/requirements-brain.txt` (brain — 17 packages, superset)

```
comtypes==1.4.16
edge-tts==7.2.7
faster-whisper==1.2.1
keyboard==0.13.5
kokoro-onnx[gpu]==0.5.0
numpy==2.4.3
onnxruntime-gpu==1.24.3
pyautogui==0.9.54
pygame-ce==2.5.7
pygetwindow==0.0.9
pyperclip==1.11.0
python-dotenv==1.2.2
silero-vad==6.2.1
sounddevice==0.5.5
torch==2.10.0
uiautomation==2.0.29
websockets==16.0
```

## Acceptance-Driven Tests

| Acceptance Criterion | Required Test | Type |
|---------------------|---------------|------|
| AC1: `cyrus2/requirements.txt` exists with pinned versions | File exists, all lines contain `==`, line count = 7 | verification script |
| AC2: `cyrus2/requirements-voice.txt` exists with pinned versions | File exists, all lines contain `==`, line count = 10 | verification script |
| AC3: `cyrus2/requirements-brain.txt` exists with pinned versions | File exists, all lines contain `==`, line count = 17 | verification script |
| AC4: All versions from working environment | N/A — no env available; used latest stable PyPI, all verified 2026-03-16 | documentation |
| AC5: torch/faster-whisper/onnxruntime-gpu compatible | GPU compatibility chain verified; grep fragile packages in brain file | verification script |
| AC6: Each file installable without conflicts | `pip install --dry-run` (may fail on Linux for Windows-only pkgs — expected) | verification script |
| AC7: Git shows changed files | Will be new files (cyrus2/ is empty); AC is incorrect for rewrite sprint | git status |

**Note on AC package counts**: The AC says 17/10/8 but the restructured layout is 7/10/17. The AC numbers are errors in the original issue (see Ambiguity Resolution above).

## Validation (Backpressure)

- **File existence**: `test -f` for all three files
- **Pinning format**: Python script checks every line contains `==`
- **Package counts**: 7 / 10 / 17 respectively
- **Cross-file consistency**: Shared packages have identical versions; brain is superset of both base and voice
- **Fragile packages**: `torch`, `faster-whisper`, `onnxruntime-gpu`, `kokoro-onnx[gpu]` all present in brain
- **No build/lint/test**: This is text-only — no code compilation or test suite applies

### Verification Scripts

#### Per-file validation
```bash
python3 -c "
import sys
for fname, expected in [
    ('cyrus2/requirements.txt', 7),
    ('cyrus2/requirements-voice.txt', 10),
    ('cyrus2/requirements-brain.txt', 17),
]:
    with open(fname) as f:
        lines = [l.strip() for l in f if l.strip()]
    for line in lines:
        if '==' not in line:
            print(f'FAIL: {fname}: not pinned: {line}')
            sys.exit(1)
    if len(lines) != expected:
        print(f'FAIL: {fname}: expected {expected} packages, got {len(lines)}')
        sys.exit(1)
    print(f'OK: {fname}: {len(lines)} packages, all pinned')
"
```

#### Cross-file consistency
```bash
python3 -c "
import sys

def parse_reqs(path):
    with open(path) as f:
        return {l.split('==')[0].strip(): l.strip() for l in f if l.strip()}

base = parse_reqs('cyrus2/requirements.txt')
voice = parse_reqs('cyrus2/requirements-voice.txt')
brain = parse_reqs('cyrus2/requirements-brain.txt')
errors = []

for pkg in ['python-dotenv', 'websockets']:
    versions = set()
    for name, reqs in [('base', base), ('voice', voice), ('brain', brain)]:
        if pkg in reqs:
            versions.add(reqs[pkg])
    if len(versions) > 1:
        errors.append(f'{pkg} version mismatch: {versions}')

for pkg in base:
    if pkg not in brain:
        errors.append(f'brain missing base package: {pkg}')
for pkg in voice:
    if pkg not in brain:
        errors.append(f'brain missing voice package: {pkg}')

for pkg in ['torch', 'faster-whisper', 'onnxruntime-gpu', 'kokoro-onnx[gpu]']:
    key = pkg.split('[')[0]
    if key not in brain:
        errors.append(f'brain missing fragile package: {pkg}')

if errors:
    for e in errors:
        print(f'FAIL: {e}')
    sys.exit(1)
print('OK: all cross-file checks pass')
"
```

## Files to Create/Modify

- `cyrus2/requirements.txt` — Create: 7 pinned base packages (UI automation + system)
- `cyrus2/requirements-voice.txt` — Create: 10 pinned voice packages (speech + audio)
- `cyrus2/requirements-brain.txt` — Create: 17 pinned brain packages (full system superset)

## Risk Assessment

**Low risk.** Three new text files with no code changes. Failure modes:
1. **Typo in package name** — caught by pip dry-run
2. **Version doesn't exist on PyPI** — caught by pip dry-run (all verified 2026-03-16)
3. **GPU version incompatibility** — mitigated by CUDA 12 compatibility chain; full verification requires GPU hardware

**Known limitations:**
- `comtypes` and `uiautomation` are Windows-only; pip dry-run will fail on Linux for files containing them (base and brain) — this is expected
- `keyboard==0.13.5` is unmaintained (last release 2020) but is the only version available
- Without a `pip freeze` from a known-good environment, versions are best-effort from PyPI latest stable (all individually verified)

## Build History Note

This issue has been stuck in PLANNED with 70+ build attempts that all consumed 0 tokens (builds fail to start). This suggests a structural issue with the build agent setup for this Python project, not a problem with the plan itself. The plan content is correct and ready for execution.
