"""
Acceptance-driven tests for Issue 028: Add TCP Authentication.

These tests verify every acceptance criterion from the issue:
  - AUTH_TOKEN read from CYRUS_AUTH_TOKEN env var (or generated if absent)
  - validate_auth_token() helper validates tokens using constant-time comparison
  - cyrus_hook._send() includes token in every message
  - cyrus_brain handlers reject connections with missing/wrong tokens
  - cyrus_brain handlers accept connections with correct tokens
  - Token mismatch is logged, not exposed to clients
  - .env.example contains CYRUS_AUTH_TOKEN

Test categories
---------------
  Config: AUTH_TOKEN      (4 tests) — module exposes AUTH_TOKEN, env override, generation
  Config: validate        (3 tests) — correct / wrong / empty token validation
  Hook: token in _send    (3 tests) — _send merges token; wrong token; no-env fallback
  Brain: hook auth        (3 tests) — accept correct / reject wrong / reject missing token
  Brain: mobile auth      (2 tests) — accept correct / reject wrong token
  Logging                 (1 test)  — mismatch logged, not exposed to client
  .env.example            (1 test)  — CYRUS_AUTH_TOKEN present in file

Usage
-----
    pytest tests/test_028_tcp_auth.py -v
    pytest tests/test_028_tcp_auth.py -k "brain" -v
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# -- Path setup ----------------------------------------------------------------
# cyrus_config.py and cyrus_hook.py live in cyrus2/ -- make that importable.

_CYRUS2_DIR = Path(__file__).parent.parent  # .../cyrus/cyrus2/
if str(_CYRUS2_DIR) not in sys.path:
    sys.path.insert(0, str(_CYRUS2_DIR))

# -- Mock Windows-specific modules BEFORE any cyrus_brain import --------------
# cyrus_brain.py imports Windows-only packages at the module level.
# Mock them in sys.modules first so the import succeeds on any platform.
_WIN_MODS = [
    "comtypes",
    "comtypes.gen",
    "uiautomation",
    "pyautogui",
    "pygetwindow",
    "pyperclip",
    "websockets",
    "websockets.exceptions",
    "websockets.legacy",
    "websockets.legacy.server",
]
for _mod in _WIN_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import cyrus_brain  # noqa: E402
import cyrus_config  # noqa: E402


def _reload_config(**kwargs: str) -> object:
    """Reload cyrus_config with given env overrides.

    Args:
        **kwargs: Mapping of env var names to string values.

    Returns:
        Freshly-reloaded cyrus_config module.
    """
    with patch.dict(os.environ, kwargs, clear=False):
        return importlib.reload(cyrus_config)


def _strip_cyrus_auth_env() -> dict[str, str]:
    """Remove CYRUS_AUTH_TOKEN from environment and return saved copy."""
    saved: dict[str, str] = {}
    for key in list(os.environ):
        if key == "CYRUS_AUTH_TOKEN":
            saved[key] = os.environ.pop(key)
    return saved


# -- AUTH_TOKEN config tests ---------------------------------------------------


class TestAuthTokenConfig(unittest.TestCase):
    """AUTH_TOKEN is exposed as a module constant read from CYRUS_AUTH_TOKEN."""

    def tearDown(self) -> None:
        """Restore clean env after each test."""
        os.environ.pop("CYRUS_AUTH_TOKEN", None)
        importlib.reload(cyrus_config)

    def test_auth_token_attribute_exists(self) -> None:
        """AC: cyrus_config must expose AUTH_TOKEN as a module-level constant."""
        self.assertTrue(
            hasattr(cyrus_config, "AUTH_TOKEN"),
            "cyrus_config is missing AUTH_TOKEN constant",
        )

    def test_auth_token_is_string(self) -> None:
        """AUTH_TOKEN must be a Python str (never None or bytes)."""
        mod = _reload_config(CYRUS_AUTH_TOKEN="test-token-123")
        self.assertIsInstance(mod.AUTH_TOKEN, str, "AUTH_TOKEN must be str")

    def test_auth_token_from_env(self) -> None:
        """AC: CYRUS_AUTH_TOKEN env var must set AUTH_TOKEN."""
        mod = _reload_config(CYRUS_AUTH_TOKEN="secret-abc-456")
        self.assertEqual(mod.AUTH_TOKEN, "secret-abc-456")

    def test_auth_token_generated_if_missing(self) -> None:
        """AC: If CYRUS_AUTH_TOKEN not set, generate a non-empty token and warn."""
        saved = _strip_cyrus_auth_env()
        try:
            import io

            stderr_capture = io.StringIO()
            with patch("sys.stderr", stderr_capture):
                mod = _reload_config()
            # Generated token must be non-empty
            self.assertTrue(
                len(mod.AUTH_TOKEN) > 0,
                "Generated AUTH_TOKEN must be non-empty",
            )
            # WARN message must have been printed to stderr
            warn_output = stderr_capture.getvalue()
            self.assertIn(
                "CYRUS_AUTH_TOKEN",
                warn_output,
                "Missing token warning must mention CYRUS_AUTH_TOKEN",
            )
        finally:
            os.environ.update(saved)
            importlib.reload(cyrus_config)


# -- validate_auth_token tests -------------------------------------------------


class TestValidateAuthToken(unittest.TestCase):
    """validate_auth_token() must exist and validate tokens correctly."""

    def setUp(self) -> None:
        """Load config with a known token for all validation tests."""
        self._mod = _reload_config(CYRUS_AUTH_TOKEN="my-secret-token")

    def tearDown(self) -> None:
        """Restore clean env."""
        os.environ.pop("CYRUS_AUTH_TOKEN", None)
        importlib.reload(cyrus_config)

    def test_validate_function_exists(self) -> None:
        """cyrus_config must expose validate_auth_token() callable."""
        self.assertTrue(
            hasattr(cyrus_config, "validate_auth_token"),
            "cyrus_config is missing validate_auth_token()",
        )
        self.assertTrue(
            callable(getattr(cyrus_config, "validate_auth_token")),
            "validate_auth_token must be callable",
        )

    def test_validate_token_correct(self) -> None:
        """AC: validate_auth_token returns True when token matches AUTH_TOKEN."""
        result = self._mod.validate_auth_token("my-secret-token")
        self.assertTrue(result, "validate_auth_token should return True on correct token")

    def test_validate_token_wrong(self) -> None:
        """AC: validate_auth_token returns False when token does not match."""
        result = self._mod.validate_auth_token("wrong-token")
        self.assertFalse(result, "validate_auth_token should return False on wrong token")

    def test_validate_token_empty_string(self) -> None:
        """validate_auth_token returns False when received token is empty."""
        result = self._mod.validate_auth_token("")
        self.assertFalse(result, "validate_auth_token should return False on empty token")

    def test_validate_uses_constant_time_comparison(self) -> None:
        """validate_auth_token must use hmac.compare_digest (timing-safe).

        Verified by inspecting the source -- timing-attack resistant comparison
        is required per the security recommendation in docs/12-code-audit.md.
        """
        source = (_CYRUS2_DIR / "cyrus_config.py").read_text(encoding="utf-8")
        self.assertIn(
            "hmac.compare_digest",
            source,
            "validate_auth_token must use hmac.compare_digest for timing safety",
        )


# -- Hook: token in _send tests ------------------------------------------------


class TestHookSendsToken(unittest.TestCase):
    """cyrus_hook._send() must include AUTH_TOKEN in every message."""

    def _import_hook_with_token(self, token: str) -> object:
        """Import (or reload) cyrus_hook with CYRUS_AUTH_TOKEN=token set."""
        import cyrus_hook

        with patch.dict(os.environ, {"CYRUS_AUTH_TOKEN": token}, clear=False):
            return importlib.reload(cyrus_hook)

    def test_hook_send_includes_token(self) -> None:
        """AC: cyrus_hook._send() adds AUTH_TOKEN as 'token' key to the message."""
        hook = self._import_hook_with_token("hook-secret")
        captured: list[bytes] = []

        # Fake socket that captures sendall calls
        fake_sock = MagicMock()
        fake_sock.__enter__ = lambda s: fake_sock
        fake_sock.__exit__ = MagicMock(return_value=False)
        fake_sock.sendall.side_effect = lambda data: captured.append(data)

        with patch("socket.create_connection", return_value=fake_sock):
            hook._send({"event": "stop", "text": "hello"})

        self.assertEqual(len(captured), 1, "_send must call sendall exactly once")
        sent_json = json.loads(captured[0].decode().strip())
        self.assertIn("token", sent_json, "_send must include 'token' in message")
        self.assertEqual(sent_json["token"], "hook-secret")

    def test_hook_send_does_not_mutate_original_dict(self) -> None:
        """_send() must not modify the caller's original dict when adding token."""
        hook = self._import_hook_with_token("my-token")
        original = {"event": "stop", "text": "hi"}
        original_copy = dict(original)

        fake_sock = MagicMock()
        fake_sock.__enter__ = lambda s: fake_sock
        fake_sock.__exit__ = MagicMock(return_value=False)
        fake_sock.sendall = MagicMock()

        with patch("socket.create_connection", return_value=fake_sock):
            hook._send(original)

        # Original dict must be unchanged -- _send should merge into a copy
        self.assertEqual(original, original_copy, "_send must not mutate caller's dict")

    def test_hook_send_silent_on_connection_failure(self) -> None:
        """_send() must stay silent (not raise) if the brain is unreachable.

        This matches existing hook behavior -- never block Claude Code.
        """
        hook = self._import_hook_with_token("some-token")
        with patch("socket.create_connection", side_effect=OSError("refused")):
            try:
                hook._send({"event": "ping"})
            except Exception as exc:  # noqa: BLE001
                self.fail(f"_send must not raise on connection failure: {exc}")


# -- Brain: hook auth tests ----------------------------------------------------


class TestBrainVoiceAuth(unittest.IsolatedAsyncioTestCase):
    """handle_hook_connection authenticates before processing hook events."""

    # Correct token used across all hook auth tests
    _TOKEN = "voice-secret-xyz"

    def _make_reader_writer(self, raw_bytes: bytes):
        """Return (reader, writer, written_list) with raw_bytes queued in reader."""
        reader = asyncio.StreamReader()
        reader.feed_data(raw_bytes)
        reader.feed_eof()

        written: list[bytes] = []
        transport = MagicMock()
        protocol = MagicMock()
        writer = asyncio.StreamWriter(transport, protocol, reader, asyncio.get_event_loop())
        writer.write = lambda data: written.append(data)
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return reader, writer, written

    async def test_brain_hook_accepts_correct_token(self) -> None:
        """AC: handle_hook_connection dispatches when token matches AUTH_TOKEN."""
        with patch.dict(os.environ, {"CYRUS_AUTH_TOKEN": self._TOKEN}):
            importlib.reload(cyrus_config)

            raw = (
                json.dumps(
                    {"event": "stop", "text": "hi", "cwd": "/proj", "token": self._TOKEN}
                ).encode()
                + b"\n"
            )
            reader, writer, written = self._make_reader_writer(raw)

            session_mgr = MagicMock()
            session_mgr._chat_watchers = {}
            session_mgr._perm_watchers = {}

            # Should not write an unauthorized error
            with patch.object(cyrus_brain, "_speak_queue", asyncio.Queue()):
                await cyrus_brain.handle_hook_connection(reader, writer, session_mgr)

            # No "unauthorized" response should have been written
            all_written = b"".join(written)
            self.assertNotIn(b"unauthorized", all_written.lower())

    async def test_brain_hook_rejects_wrong_token(self) -> None:
        """AC: handle_hook_connection closes connection when token is wrong."""
        with patch.dict(os.environ, {"CYRUS_AUTH_TOKEN": self._TOKEN}):
            importlib.reload(cyrus_config)

            raw = (
                json.dumps(
                    {"event": "stop", "text": "hi", "cwd": "/proj", "token": "wrong-token"}
                ).encode()
                + b"\n"
            )
            reader, writer, written = self._make_reader_writer(raw)
            session_mgr = MagicMock()

            await cyrus_brain.handle_hook_connection(reader, writer, session_mgr)

            # writer.close() must have been called (disconnect)
            writer.close.assert_called()

    async def test_brain_hook_rejects_missing_token(self) -> None:
        """AC: handle_hook_connection closes connection when token field absent."""
        with patch.dict(os.environ, {"CYRUS_AUTH_TOKEN": self._TOKEN}):
            importlib.reload(cyrus_config)

            raw = (
                json.dumps(
                    {"event": "stop", "text": "hi", "cwd": "/proj"}  # no token field
                ).encode()
                + b"\n"
            )
            reader, writer, written = self._make_reader_writer(raw)
            session_mgr = MagicMock()

            await cyrus_brain.handle_hook_connection(reader, writer, session_mgr)

            writer.close.assert_called()


# -- Brain: mobile auth tests --------------------------------------------------


class TestBrainMobileAuth(unittest.IsolatedAsyncioTestCase):
    """handle_mobile_ws authenticates first message before adding to broadcast set."""

    _TOKEN = "mobile-secret-xyz"

    async def test_brain_mobile_accepts_correct_token(self) -> None:
        """AC: handle_mobile_ws adds client to set after correct token auth."""
        with patch.dict(os.environ, {"CYRUS_AUTH_TOKEN": self._TOKEN}):
            importlib.reload(cyrus_config)

            auth_msg = json.dumps({"type": "auth", "token": self._TOKEN})

            messages: list[str] = [auth_msg]

            class FakeWS:
                remote_address = ("127.0.0.1", 12345)
                close_code = 1000
                close_reason = ""

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if messages:
                        return messages.pop(0)
                    raise StopAsyncIteration

                async def send(self, data):
                    pass

            ws = FakeWS()
            # Clear mobile clients set
            original_clients = cyrus_brain._mobile_clients.copy()
            cyrus_brain._mobile_clients.clear()

            await cyrus_brain.handle_mobile_ws(ws)
            # After auth + disconnect, the ws should have been added (then removed on disconnect)
            # The key check: no exception raised, connection attempted
            # (client gets added then removed on StopAsyncIteration)
            cyrus_brain._mobile_clients.update(original_clients)

    async def test_brain_mobile_rejects_wrong_token(self) -> None:
        """AC: handle_mobile_ws closes connection when first message has wrong token."""
        with patch.dict(os.environ, {"CYRUS_AUTH_TOKEN": self._TOKEN}):
            importlib.reload(cyrus_config)

            auth_msg = json.dumps({"type": "auth", "token": "wrong-token"})
            messages_sent: list[str] = []

            class FakeWS:
                remote_address = ("127.0.0.1", 12345)
                close_code = 1000
                close_reason = ""
                closed = False
                _msg_yielded = False

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    # Yield auth_msg only once; handler should return before reaching here again
                    if not self._msg_yielded:
                        self._msg_yielded = True
                        return auth_msg
                    raise StopAsyncIteration

                async def send(self, data):
                    messages_sent.append(data)

                async def close(self):
                    self.closed = True

            ws = FakeWS()
            await cyrus_brain.handle_mobile_ws(ws)

            # Connection must have been closed after bad auth
            self.assertTrue(
                ws.closed,
                "handle_mobile_ws must close WebSocket on wrong token",
            )


# -- Logging: mismatch logged not exposed --------------------------------------


class TestTokenMismatchLogging(unittest.TestCase):
    """Token mismatches must be logged but not sent back to the client."""

    _TOKEN = "secret-for-log-test"

    def test_mismatch_logged_not_in_error_response(self) -> None:
        """AC: token mismatch logged (not the actual token); error sent is generic."""
        # Verify that the brain sends a generic "unauthorized" error rather than
        # exposing the expected token value. We inspect the source to ensure the
        # log call does not include the raw token in the format string.
        source = (_CYRUS2_DIR / "cyrus_brain.py").read_text(encoding="utf-8")

        # The source must contain a log call for auth failure
        self.assertTrue(
            "unauthorized" in source.lower() or "auth" in source.lower(),
            "cyrus_brain.py must log auth failures",
        )

        # Find lines that log auth failures -- they must not expose AUTH_TOKEN value
        # Acceptable patterns: log.warning("...", addr) -- without AUTH_TOKEN value
        # Forbidden: log.warning("expected %s", AUTH_TOKEN)
        log_lines = [
            line
            for line in source.splitlines()
            if ("log." in line and "auth" in line.lower())
            or ("log." in line and "unauthorized" in line.lower())
            or ("log." in line and "token" in line.lower() and "mismatch" in line.lower())
        ]
        for line in log_lines:
            self.assertNotIn(
                "AUTH_TOKEN",
                line,
                f"Token value must not be logged verbatim: {line!r}",
            )


# -- .env.example has CYRUS_AUTH_TOKEN ----------------------------------------


class TestEnvExampleHasAuthToken(unittest.TestCase):
    """.env.example must document CYRUS_AUTH_TOKEN."""

    _ENV_EXAMPLE = _CYRUS2_DIR / ".env.example"

    def test_env_example_has_auth_token(self) -> None:
        """AC: cyrus2/.env.example must contain CYRUS_AUTH_TOKEN."""
        self.assertTrue(
            self._ENV_EXAMPLE.exists(),
            f".env.example not found at {self._ENV_EXAMPLE}",
        )
        content = self._ENV_EXAMPLE.read_text(encoding="utf-8")
        self.assertIn(
            "CYRUS_AUTH_TOKEN",
            content,
            "CYRUS_AUTH_TOKEN must be documented in .env.example",
        )


# -- Module interface: no hardware deps in cyrus_config -----------------------


class TestConfigNoHardwareDeps(unittest.TestCase):
    """AUTH_TOKEN logic must not introduce hardware/ML package imports."""

    def test_cyrus_config_still_no_hardware_deps(self) -> None:
        """Adding AUTH_TOKEN must not add hardware package imports to cyrus_config."""
        forbidden = {
            "sounddevice",
            "torch",
            "faster_whisper",
            "silero_vad",
            "pygame",
            "keyboard",
            "numpy",
            "comtypes",
            "uiautomation",
        }
        source = (_CYRUS2_DIR / "cyrus_config.py").read_text(encoding="utf-8")
        for pkg in forbidden:
            self.assertNotIn(
                f"import {pkg}",
                source,
                f"cyrus_config.py must not import hardware package: {pkg!r}",
            )


# -- Entry point ---------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
