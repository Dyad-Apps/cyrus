"""
cyrus_config.py — Centralized configuration for Cyrus 2.0

All tuneable constants are defined here with environment-variable overrides so
that deployments can adjust behaviour without modifying source code.  Every
constant is read from its corresponding CYRUS_* env var at import time; if the
var is absent the hardcoded default is used.

Usage
-----
    from cyrus_config import BRAIN_PORT, TTS_TIMEOUT, SPEECH_THRESHOLD

Environment variables
---------------------
See .env.example in the cyrus2/ directory for a full listing with defaults and
descriptions.  Any of the variables listed there can be exported in the shell
or placed in a .env file (loaded by your process runner) to override the
defaults at runtime.

No hardware or third-party packages are imported here — this module is safe to
use in CI, headless servers, and test environments.
"""

from __future__ import annotations

import os

# ── Port assignments ───────────────────────────────────────────────────────────
# Each service owns one port.  Override via the corresponding CYRUS_*_PORT var.
# All ports are integers; providing a non-integer value will raise ValueError.

# Brain TCP server — receives voice utterances from cyrus_voice.py
BRAIN_PORT: int = int(os.environ.get("CYRUS_BRAIN_PORT", "8766"))

# Hook TCP server — Claude Code Stop/PreToolUse/PostToolUse hooks connect here
HOOK_PORT: int = int(os.environ.get("CYRUS_HOOK_PORT", "8767"))

# Mobile WebSocket — streams events to the Cyrus mobile companion app
MOBILE_PORT: int = int(os.environ.get("CYRUS_MOBILE_PORT", "8769"))

# VS Code companion extension — brain connects here to submit text without UIA
COMPANION_PORT: int = int(os.environ.get("CYRUS_COMPANION_PORT", "8770"))

# Standalone server (cyrus_server.py) — remote brain for mobile-only setups
SERVER_PORT: int = int(os.environ.get("CYRUS_SERVER_PORT", "8765"))

# ── Timeout constants ──────────────────────────────────────────────────────────
# Timeouts are in seconds unless the name includes a different unit.

# Maximum wall-clock seconds to wait for a TTS synthesis + playback call
TTS_TIMEOUT: float = float(os.environ.get("CYRUS_TTS_TIMEOUT", "25.0"))

# Socket connect/recv timeout used by cyrus_hook.py when reaching the brain
SOCKET_TIMEOUT: int = int(os.environ.get("CYRUS_SOCKET_TIMEOUT", "10"))

# ── VAD (Voice Activity Detection) thresholds ─────────────────────────────────
# These values tune the Silero VAD model behaviour in cyrus_voice.py.

# Silero probability above which a frame is classified as speech (0.0–1.0)
SPEECH_THRESHOLD: float = float(os.environ.get("CYRUS_SPEECH_THRESHOLD", "0.6"))

# Milliseconds of consecutive silence required to end an utterance recording
SILENCE_WINDOW: int = int(os.environ.get("CYRUS_SILENCE_WINDOW", "1500"))

# Minimum milliseconds of speech required before an utterance is submitted
MIN_SPEECH_DURATION: int = int(os.environ.get("CYRUS_MIN_SPEECH_DURATION", "500"))

# ── Watcher poll intervals ─────────────────────────────────────────────────────
# Intervals (in seconds) for the background threads that watch the VS Code UI.

# How often ChatWatcher polls the Claude Code chat output pane for new text
CHAT_WATCHER_POLL_INTERVAL: float = float(
    os.environ.get("CYRUS_CHAT_POLL_MS", "0.5")
)

# How often PermissionWatcher polls for Claude Code permission dialogs
PERMISSION_WATCHER_POLL_INTERVAL: float = float(
    os.environ.get("CYRUS_PERMISSION_POLL_MS", "0.3")
)

# ── Miscellaneous ──────────────────────────────────────────────────────────────

# Hard cap on spoken words in a TTS call (~12 s at 150 wpm)
MAX_SPEECH_WORDS: int = int(os.environ.get("CYRUS_MAX_SPEECH_WORDS", "200"))
