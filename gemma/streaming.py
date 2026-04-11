"""Streamed text rendering with a bordered thinking box."""

import re
import sys

from .ui import dim, gray, reset


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks entirely (for --raw mode)."""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)


class ThinkStreamer:
    """
    Streams text to stdout while rendering `<think>...</think>` blocks in a
    dimmed, bordered box on stderr.

    Two input paths:
      - `feed_response(text)` — response text that may contain inline
        `<think>` tags (legacy behavior for SDK versions that inline them).
      - `feed_thought(text)` — already-classified thought text from the
        Gemini SDK's separate `thought=True` parts.

    Both paths share the same box-open / render / box-close state, so
    mixing them in a single turn produces a single continuous think block.
    """

    _BOX_TOP_LEN = 40
    _BOX_BOTTOM_LEN = 52

    def __init__(self, show: bool = True):
        self.show = show
        self.in_think = False
        self.buffer = ""
        self.at_line_start = True
        self.has_thought = False

    # ── public API ─────────────────────────────────────────────────────

    def feed_response(self, text: str) -> None:
        """Feed response text; inline <think> tags are detected and routed."""
        if self.in_think and not self.buffer:
            # Response text following a thought part — close the box first.
            self._close_box()
        self.buffer += text
        self._process()

    def feed_thought(self, text: str) -> None:
        """Feed pre-classified thought text from the SDK."""
        if not self.show:
            self.has_thought = True
            return
        if not self.in_think:
            self._open_box()
        self._render_think(text)

    def flush(self) -> None:
        """Emit any buffered text and close an open think box."""
        if self.in_think:
            if self.show and self.buffer:
                self._render_think(self.buffer)
            self._close_box()
        else:
            sys.stdout.write(self.buffer)
            sys.stdout.flush()
        self.buffer = ""

    # ── internals ──────────────────────────────────────────────────────

    def _open_box(self) -> None:
        self.in_think = True
        self.has_thought = True
        self.at_line_start = True
        sys.stderr.write(f"\n {gray()}💭 Thinking {'─' * self._BOX_TOP_LEN}{reset()}\n")
        sys.stderr.flush()

    def _close_box(self) -> None:
        if self.in_think:
            sys.stderr.write(f"{reset()}\n {gray()}{'─' * self._BOX_BOTTOM_LEN}{reset()}\n\n")
            sys.stderr.flush()
            self.in_think = False
            self.at_line_start = True

    def _process(self) -> None:
        while True:
            if not self.in_think:
                idx = self.buffer.find("<think>")
                if idx != -1:
                    if idx > 0:
                        sys.stdout.write(self.buffer[:idx])
                        sys.stdout.flush()
                    self.buffer = self.buffer[idx + 7:]
                    if self.show:
                        self._open_box()
                    else:
                        self.in_think = True
                        self.has_thought = True
                else:
                    # Keep last 6 chars to avoid splitting a "<think" boundary.
                    safe = max(0, len(self.buffer) - 6)
                    if safe > 0:
                        sys.stdout.write(self.buffer[:safe])
                        sys.stdout.flush()
                        self.buffer = self.buffer[safe:]
                    break
            else:
                idx = self.buffer.find("</think>")
                if idx != -1:
                    chunk = self.buffer[:idx]
                    if self.show:
                        self._render_think(chunk)
                    self._close_box()
                    self.buffer = self.buffer[idx + 8:].lstrip("\n")
                else:
                    # Keep last 7 chars for a split "</think" boundary.
                    safe = max(0, len(self.buffer) - 7)
                    if safe > 0:
                        if self.show:
                            self._render_think(self.buffer[:safe])
                        self.buffer = self.buffer[safe:]
                    break

    def _render_think(self, text: str) -> None:
        if not text:
            return
        for ch in text:
            if self.at_line_start:
                sys.stderr.write(f" {gray()}│{reset()} {dim()}")
                self.at_line_start = False
            if ch == "\n":
                sys.stderr.write(f"{reset()}\n")
                self.at_line_start = True
            else:
                sys.stderr.write(ch)
        sys.stderr.flush()
