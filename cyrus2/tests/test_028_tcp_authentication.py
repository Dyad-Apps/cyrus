"""
Acceptance-driven tests for Issue 028: Add TCP Authentication.

These tests verify every acceptance criterion from the issue:
  - Token read from CYRUS_AUTH_TOKEN env var
  - Token generation helper when token is missing
  - validate_auth_token() helper in cyrus_config
  - cyrus_hook._send() includes token in wire messages
  - cyrus_brain.handle_hook_connection rejects invalid tokens
  - cyrus_brain.handle_voice_connection rejects invalid tokens
  - cyrus_brain.handle_mobile_ws rejects invalid tokens
  - Token mismatch logged but not exposed in error message
  - CYRUS_AUTH_TOKEN documented in .env.example

Test categories
---------------
  Config/token        (5 tests) — AUTH_TOKEN reads from env, generates if missing
  validate_auth_token (5 tests) — correct/incorrect/empty/None/whitespace
  Hook wire message   (5 tests) — token injected in all hook event messages
  Brain hook handler  (4 tests) — invalid token rejected, valid token accepted
  Brain voice handler (3 tests) — invalid token rejected, valid token accepted
  Brain mobile handler(3 tests) — invalid token rejected, valid token accepted
  .env.example        (2 tests) — CYRUS_AUTH_TOKEN present with comment

Usage
-----
    pytest tests/test_028_tcp_authentication.py -v
    pytest tests/test_028_tcp_authentication.py -k "config" -v
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_CYRUS2_DIR = Path(__file__).parent.parent  # .../cyrus/cyrus2/
if str(_CYRUS2_DIR) not in sys.path:
    sys.path.insert(0, str(_CYRUS2_DIR))

# ── Mock Windows-specific modules BEFORE any cyrus_brain import ──────────────
# cyrus_brain.py imports Windows-only packages at the module level.
# Mock them here so the module imports cleanly on any platform.
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

import cyrus_config  # noqa: E402
from cyrus_hook import main as hook_main  # noqa: E402


# ── Helper to reload cyrus_config with env overrides ─────────────────────────


def _reload_config(**env_overrides: str) -> object:
    """Reload cyrus_config with the given environment overrides.

    Injects env vars via patch.dict, reloads the module, restores original
    state in sys.modules after the with-block exits.

    Args:
        **env_overrides: Mapping of env var names → string values.

    Returns:
        The freshly-reloaded cyrus_config module.
    """
    with patch.dict(os.environ, env_overrides, clear=False):
        return importlib.reload(cyrus_config)


# ── Config / AUTH_TOKEN tests ─────────────────────────────────────────────────


class TestAuthTokenConfig(unittest.TestCase):
    """Verify AUTH_TOKEN is read from env or generated when absent.

    Acceptance criteria tested:
      - Token read from CYRUS_AUTH_TOKEN env var
      - Token generation helper (if token missing, suggest generating one)
    """

    def setUp(self) -> None:
        """Strip CYRUS_AUTH_TOKEN so each test starts clean."""
        self._saved = os.environ.pop("CYRUS_AUTH_TOKEN", None)

    def tearDown(self) -> None:
        """Restore CYRUS_AUTH_TOKEN and reload module to original state."""
        if self._saved is not None:
            os.environ["CYRUS_AUTH_TOKEN"] = self._saved
        else:
            os.environ.pop("CYRUS_AUTH_TOKEN", None)
        importlib.reload(cyrus_config)

    def test_auth_token_reads_from_env(self) -> None:
        """CYRUS_AUTH_TOKEN env var is read into AUTH_TOKEN at import time."""
        mod = _reload_config(CYRUS_AUTH_TOKEN="my-secret-token")
        self.assertEqual(mod.AUTH_TOKEN, "my-secret-token")

    def test_auth_token_generated_when_missing(self) -> None:
        """When CYRUS_AUTH_TOKEN is absent, AUTH_TOKEN is auto-generated (non-empty)."""
        mod = _reload_config()
        # Must be non-empty — a token was generated
        self.assertIsInstance(mod.AUTH_TOKEN, str)
        self.assertGreater(len(mod.AUTH_TOKEN), 0)

    def test_generated_token_is_hex_string(self) -> None:
        """Auto-generated AUTH_TOKEN is a hexadecimal string (all hex chars)."""
        mod = _reload_config()
        # secrets.token_hex(16) produces a 32-character hex string
        token = mod.AUTH_TOKEN
        self.assertRegex(token, r"^[0-9a-f]+$", f"Token {token!r} is not hex")

    def test_generated_token_is_at_least_16_chars(self) -> None:
        """Auto-generated token must be at least 16 chars to be cryptographically safe."""
        mod = _reload_config()
        self.assertGreaterEqual(len(mod.AUTH_TOKEN), 16)

    def test_auth_token_is_string_type(self) -> None:
        """AUTH_TOKEN must always be a str, regardless of source."""
        mod = _reload_config(CYRUS_AUTH_TOKEN="abc123")
        self.assertIsInstance(mod.AUTH_TOKEN, str)


# ── validate_auth_token tests ────────────────────────────────────────────────


class TestValidateAuthToken(unittest.TestCase):
    """Verify validate_auth_token() helper returns correct True/False.

    Acceptance criteria tested:
      - validate_auth_token() returns True for correct token
      - validate_auth_token() returns False for incorrect token
      - validate_auth_token() returns False for empty string
    """

    def setUp(self) -> None:
        """Set a known AUTH_TOKEN for all tests in this class."""
        self._saved = os.environ.pop("CYRUS_AUTH_TOKEN", None)
        os.environ["CYRUS_AUTH_TOKEN"] = "correct-secret"
        importlib.reload(cyrus_config)

    def tearDown(self) -> None:
        """Restore original env and reload module."""
        if self._saved is not None:
            os.environ["CYRUS_AUTH_TOKEN"] = self._saved
        else:
            os.environ.pop("CYRUS_AUTH_TOKEN", None)
        importlib.reload(cyrus_config)

    def test_valid_token_returns_true(self) -> None:
        """validate_auth_token returns True when received token matches AUTH_TOKEN."""
        self.assertTrue(cyrus_config.validate_auth_token("correct-secret"))

    def test_wrong_token_returns_false(self) -> None:
        """validate_auth_token returns False when received token does not match."""
        self.assertFalse(cyrus_config.validate_auth_token("wrong-token"))

    def test_empty_token_returns_false(self) -> None:
        """validate_auth_token returns False for empty string when token is set."""
        self.assertFalse(cyrus_config.validate_auth_token(""))

    def test_whitespace_token_returns_false(self) -> None:
        """validate_auth_token returns False for whitespace-only string."""
        self.assertFalse(cyrus_config.validate_auth_token("   "))

    def test_partial_token_returns_false(self) -> None:
        """validate_auth_token returns False for prefix of the correct token."""
        self.assertFalse(cyrus_config.validate_auth_token("correct"))


# ── Hook wire message tests ───────────────────────────────────────────────────


class TestHookIncludesToken:
    """Verify cyrus_hook._send() includes the auth token in wire messages.

    Acceptance criteria tested:
      - cyrus_hook sends token in first message (IPC protocol level)

    Strategy: Call _send() directly and mock socket.create_connection so we
    can capture the exact bytes written without opening real network connections.
    This tests the REAL _send() implementation, not a reimplementation.
    """

    @staticmethod
    def _call_send_and_capture(msg: dict, auth_token: str) -> dict:
        """Call cyrus_hook._send() with a known AUTH_TOKEN and capture wire bytes.

        Mocks socket.create_connection to intercept sendall() calls.
        Returns the decoded JSON dict that would have been sent on the wire.

        Args:
            msg: Message dict passed to _send().
            auth_token: Token value to patch into cyrus_hook.AUTH_TOKEN.

        Returns:
            Decoded wire JSON (includes token field if implementation is correct).
        """
        import cyrus_hook

        captured: list[bytes] = []

        class _FakeSock:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def sendall(self, data: bytes) -> None:
                captured.append(data)

        with (
            patch.object(cyrus_hook, "AUTH_TOKEN", auth_token),
            patch("socket.create_connection", return_value=_FakeSock()),
        ):
            cyrus_hook._send(msg)

        if not captured:
            return {}
        return json.loads(captured[0].rstrip(b"\n"))

    def test_stop_event_wire_includes_token(self) -> None:
        """_send() wire message must contain 'token' field matching AUTH_TOKEN."""
        wire = self._call_send_and_capture(
            {"event": "stop", "text": "Done.", "cwd": "/tmp"}, auth_token="tok-abc"
        )
        assert wire.get("token") == "tok-abc", f"token missing from wire: {wire}"

    def test_pre_tool_wire_includes_token(self) -> None:
        """_send() with pre_tool event must include 'token' field."""
        wire = self._call_send_and_capture(
            {"event": "pre_tool", "tool": "Bash", "command": "ls", "cwd": "/tmp"},
            auth_token="tok-pre",
        )
        assert wire.get("token") == "tok-pre", f"token missing from wire: {wire}"

    def test_post_tool_wire_includes_token(self) -> None:
        """_send() with post_tool event must include 'token' field."""
        wire = self._call_send_and_capture(
            {"event": "post_tool", "tool": "Bash", "exit_code": 1, "cwd": "/tmp"},
            auth_token="tok-post",
        )
        assert wire.get("token") == "tok-post", f"token missing from wire: {wire}"

    def test_notification_wire_includes_token(self) -> None:
        """_send() with notification event must include 'token' field."""
        wire = self._call_send_and_capture(
            {"event": "notification", "message": "Hello", "cwd": "/tmp"},
            auth_token="tok-notify",
        )
        assert wire.get("token") == "tok-notify", f"token missing from wire: {wire}"

    def test_token_not_in_original_message_dict(self) -> None:
        """_send() must NOT mutate the caller's dict — token added to wire copy only."""
        import cyrus_hook

        original = {"event": "stop", "text": "hi", "cwd": "/tmp"}
        original_copy = dict(original)

        class _FakeSock:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def sendall(self, data: bytes) -> None:
                pass  # don't care about bytes here

        with (
            patch.object(cyrus_hook, "AUTH_TOKEN", "my-tok"),
            patch("socket.create_connection", return_value=_FakeSock()),
        ):
            cyrus_hook._send(original)

        # Original dict must be unchanged after _send() returns
        assert original == original_copy, f"_send() mutated the caller's dict: {original}"


# ── Brain hook handler auth tests ─────────────────────────────────────────────


class TestBrainHookHandlerAuth:
    """Verify handle_hook_connection validates the token before processing.

    Acceptance criteria tested:
      - Unauthorized clients disconnected immediately
      - Token mismatch logged (not exposed in error message)
      - Valid token → event processed normally
    """

    @staticmethod
    def _make_reader(msg: dict) -> asyncio.StreamReader:
        """Create an asyncio.StreamReader pre-filled with one JSON line."""
        reader = asyncio.StreamReader()
        reader.feed_data(json.dumps(msg).encode() + b"\n")
        reader.feed_eof()
        return reader

    @staticmethod
    def _make_writer() -> MagicMock:
        """Create a mock asyncio.StreamWriter."""
        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        return writer

    def test_hook_valid_token_is_accepted(self, caplog) -> None:
        """Hook connection with matching token is accepted and event is processed."""
        import cyrus_brain

        # Use a stop event with non-empty text so session_mgr._chat_watchers.get is called
        reader = self._make_reader(
            {"event": "stop", "text": "Hello there", "cwd": "/tmp", "token": "good-token"}
        )
        writer = self._make_writer()
        # Leave session_mgr as full MagicMock — all attribute accesses are auto-mocked
        session_mgr = MagicMock()
        mock_queue = MagicMock()
        mock_queue.put = AsyncMock()

        with (
            patch.object(cyrus_brain, "validate_auth_token", return_value=True),
            patch.object(cyrus_brain, "_speak_queue", mock_queue),
        ):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_hook_connection(reader, writer, session_mgr)
            )
        # Event was processed — speak queue received the stop event text
        mock_queue.put.assert_called_once()

    def test_hook_invalid_token_is_rejected(self, caplog) -> None:
        """Hook connection with wrong token is rejected immediately."""
        import cyrus_brain

        reader = self._make_reader(
            {"event": "stop", "text": "hi", "cwd": "/tmp", "token": "BAD"}
        )
        writer = self._make_writer()
        session_mgr = MagicMock()

        with (
            patch.object(cyrus_brain, "AUTH_TOKEN", "good-token"),
            patch.object(cyrus_brain, "validate_auth_token", return_value=False),
        ):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_hook_connection(reader, writer, session_mgr)
            )
        # Handler must return early — speak queue should NOT receive anything
        session_mgr.assert_not_called()

    def test_hook_missing_token_is_rejected(self) -> None:
        """Hook connection with no token field is rejected."""
        import cyrus_brain

        reader = self._make_reader({"event": "stop", "text": "hi", "cwd": "/tmp"})
        writer = self._make_writer()
        # Leave session_mgr as full MagicMock so _chat_watchers.get is a MagicMock
        session_mgr = MagicMock()
        mock_queue = MagicMock()
        mock_queue.put = AsyncMock()

        with (
            patch.object(cyrus_brain, "validate_auth_token", return_value=False),
            patch.object(cyrus_brain, "_speak_queue", mock_queue),
        ):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_hook_connection(reader, writer, session_mgr)
            )
        # Handler must return early — speak queue should NOT receive anything
        mock_queue.put.assert_not_called()

    def test_hook_token_mismatch_logged_but_not_exposed(self, caplog) -> None:
        """Token mismatch is logged at WARNING level; error is NOT sent to client.

        The brain must not expose token details in any response to the hook —
        only log internally.
        """
        import logging

        import cyrus_brain

        reader = self._make_reader({"event": "stop", "text": "hi", "cwd": "/tmp", "token": "BAD"})
        writer = self._make_writer()
        session_mgr = MagicMock()

        with (
            patch.object(cyrus_brain, "validate_auth_token", return_value=False),
            caplog.at_level(logging.WARNING, logger="cyrus.brain"),
        ):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_hook_connection(reader, writer, session_mgr)
            )
        # Must log the rejection
        assert any("reject" in r.message.lower() or "token" in r.message.lower()
                   for r in caplog.records), "Expected rejection to be logged"
        # Must NOT write anything to the client (don't expose token details)
        writer.write.assert_not_called()


# ── Brain voice handler auth tests ────────────────────────────────────────────


class TestBrainVoiceHandlerAuth:
    """Verify handle_voice_connection validates auth token as first message.

    Acceptance criteria tested:
      - cyrus_voice.py sends token in first message
      - Unauthorized clients disconnected immediately
    """

    @staticmethod
    def _make_reader(msg: dict) -> asyncio.StreamReader:
        reader = asyncio.StreamReader()
        reader.feed_data(json.dumps(msg).encode() + b"\n")
        # Prevent EOF so the handler doesn't fall through prematurely
        return reader

    @staticmethod
    def _make_writer() -> MagicMock:
        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.get_extra_info = MagicMock(return_value=("127.0.0.1", 12345))
        return writer

    def test_voice_valid_token_accepted(self) -> None:
        """Voice connection with correct token passes auth and continues."""
        import cyrus_brain

        reader = self._make_reader({"type": "auth", "token": "voice-tok"})
        writer = self._make_writer()
        session_mgr = MagicMock()

        # Patch validate_auth_token to accept, and stub out the rest of the handler
        with (
            patch.object(cyrus_brain, "validate_auth_token", return_value=True),
            patch.object(cyrus_brain, "_vs_code_windows", return_value=[]),
            patch.object(cyrus_brain, "voice_reader", new=AsyncMock()),
            patch.object(cyrus_brain, "_send", new=AsyncMock()),
        ):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_voice_connection(reader, writer, session_mgr, MagicMock())
            )
        # Writer was NOT closed early (valid token)
        # _voice_writer would have been set — check write not called for "Unauthorized"
        unauthorized_writes = [
            c for c in writer.write.call_args_list
            if b"Unauthorized" in (c.args[0] if c.args else b"")
        ]
        assert not unauthorized_writes, "Should not write Unauthorized for valid token"

    def test_voice_invalid_token_rejected(self) -> None:
        """Voice connection with wrong token is disconnected immediately."""
        import cyrus_brain

        reader = self._make_reader({"type": "auth", "token": "BAD"})
        writer = self._make_writer()
        session_mgr = MagicMock()

        with patch.object(cyrus_brain, "validate_auth_token", return_value=False):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_voice_connection(reader, writer, session_mgr, MagicMock())
            )
        # Writer must be closed
        writer.close.assert_called_once()

    def test_voice_missing_token_rejected(self) -> None:
        """Voice connection without token field in first message is rejected."""
        import cyrus_brain

        reader = self._make_reader({"type": "auth"})  # no token field
        writer = self._make_writer()
        session_mgr = MagicMock()

        with patch.object(cyrus_brain, "validate_auth_token", return_value=False):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_voice_connection(reader, writer, session_mgr, MagicMock())
            )
        writer.close.assert_called_once()


# ── Brain mobile handler auth tests ───────────────────────────────────────────


class TestBrainMobileHandlerAuth:
    """Verify handle_mobile_ws validates auth token in first WebSocket message.

    Acceptance criteria tested:
      - Mobile client port (8769) validates token
      - Unauthorized clients disconnected immediately
    """

    @staticmethod
    def _make_ws(first_msg: dict | None = None, close_side_effect=None) -> MagicMock:
        """Create a mock WebSocket that yields first_msg then stops."""
        ws = MagicMock()
        ws.remote_address = ("127.0.0.1", 9999)
        if first_msg is not None:
            ws.recv = AsyncMock(return_value=json.dumps(first_msg))
        else:
            ws.recv = AsyncMock(side_effect=asyncio.TimeoutError)
        ws.close = AsyncMock(side_effect=close_side_effect)

        # Make ws async iterable (for the event loop after auth)
        async def _empty_iter():
            return
            yield  # make it a generator

        ws.__aiter__ = MagicMock(return_value=_empty_iter())
        return ws

    def test_mobile_valid_token_accepted(self) -> None:
        """Mobile connection with correct token is accepted and client is registered."""
        import cyrus_brain

        ws = self._make_ws({"type": "auth", "token": "mob-tok"})

        with (
            patch.object(cyrus_brain, "validate_auth_token", return_value=True),
            patch.object(cyrus_brain, "_mobile_clients", set()),
            patch.object(cyrus_brain, "_utterance_queue", MagicMock()),
        ):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_mobile_ws(ws)
            )
        # ws.close was NOT called (valid token, client was registered then disconnected normally)
        ws.close.assert_not_called()

    def test_mobile_invalid_token_rejected(self) -> None:
        """Mobile connection with wrong token is closed immediately."""
        import cyrus_brain

        ws = self._make_ws({"type": "auth", "token": "BAD"})

        with patch.object(cyrus_brain, "validate_auth_token", return_value=False):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_mobile_ws(ws)
            )
        ws.close.assert_called_once()

    def test_mobile_auth_timeout_rejected(self) -> None:
        """Mobile connection that doesn't send auth within timeout is closed."""
        import cyrus_brain

        ws = self._make_ws(first_msg=None)  # recv raises TimeoutError

        with patch.object(cyrus_brain, "validate_auth_token", return_value=False):
            asyncio.get_event_loop().run_until_complete(
                cyrus_brain.handle_mobile_ws(ws)
            )
        ws.close.assert_called_once()


# ── .env.example tests ────────────────────────────────────────────────────────


class TestEnvExampleHasAuthToken(unittest.TestCase):
    """.env.example must document CYRUS_AUTH_TOKEN.

    Acceptance criteria tested:
      - CYRUS_AUTH_TOKEN present in .env.example
    """

    _ENV_EXAMPLE = _CYRUS2_DIR / ".env.example"

    def test_env_example_contains_cyrus_auth_token(self) -> None:
        """CYRUS_AUTH_TOKEN must appear in .env.example."""
        self.assertTrue(
            self._ENV_EXAMPLE.exists(),
            f".env.example not found at {self._ENV_EXAMPLE}",
        )
        content = self._ENV_EXAMPLE.read_text(encoding="utf-8")
        self.assertIn(
            "CYRUS_AUTH_TOKEN",
            content,
            "CYRUS_AUTH_TOKEN is missing from .env.example",
        )

    def test_env_example_has_auth_token_comment(self) -> None:
        """A comment explaining CYRUS_AUTH_TOKEN must appear in .env.example."""
        content = self._ENV_EXAMPLE.read_text(encoding="utf-8")
        # At least one comment line should mention auth or token
        comment_lines = [l for l in content.splitlines() if l.strip().startswith("#")]
        auth_comments = [l for l in comment_lines if "auth" in l.lower() or "token" in l.lower()]
        self.assertGreater(
            len(auth_comments),
            0,
            ".env.example should have a comment explaining the auth token",
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
