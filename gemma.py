#!/usr/bin/env python3
"""Gemma CLI — Gemma 4 via Google AI Studio with agent tools, multimodal input, and streaming."""

import argparse
from dataclasses import dataclass
import glob
import importlib
import os
import random
import re
import shutil
import sys
import time

# ═══════════════════════════════════════════════════════════════════════════════
# Platform setup
# ═══════════════════════════════════════════════════════════════════════════════

# Enable ANSI escape sequences and fix UTF-8 output on Windows
if os.name == "nt":
    os.system("")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ═══════════════════════════════════════════════════════════════════════════════
# ANSI colors
# ═══════════════════════════════════════════════════════════════════════════════

USE_COLOR = False

def _sg(code):
    return f"\033[{code}m" if USE_COLOR else ""

def reset():   return _sg(0)
def dim():     return _sg(2)
def bold():    return _sg(1)
def red():     return _sg("1;31")
def green():   return _sg("1;32")
def yellow():  return _sg("1;33")
def cyan():    return _sg(36)
def gray():    return _sg(90)

def c256(n):
    return f"\033[38;5;{n}m" if USE_COLOR else ""

# ═══════════════════════════════════════════════════════════════════════════════
# Banner
# ═══════════════════════════════════════════════════════════════════════════════

BANNER = [
    "╔════════════════════════════════════════════════════╗",
    "║                                                    ║",
    "║   ██████╗ ███████╗███╗   ███╗███╗   ███╗ █████╗    ║",
    "║  ██╔════╝ ██╔════╝████╗ ████║████╗ ████║██╔══██╗   ║",
    "║  ██║  ███╗█████╗  ██╔████╔██║██╔████╔██║███████║   ║",
    "║  ██║   ██║██╔══╝  ██║╚██╔╝██║██║╚██╔╝██║██╔══██║   ║",
    "║  ╚██████╔╝███████╗██║ ╚═╝ ██║██║ ╚═╝ ██║██║  ██║   ║",
    "║   ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ║",
    "║                                                    ║",
    "╚════════════════════════════════════════════════════╝",
]

GRADIENT = [33, 39, 38, 37, 36, 44]

def gradient_line(text):
    if not USE_COLOR:
        return text
    out = []
    visible = [i for i, ch in enumerate(text) if ch != " "]
    n = max(len(visible) - 1, 1)
    vis_idx = 0
    for i, ch in enumerate(text):
        if ch == " ":
            out.append(ch)
        else:
            t = vis_idx / n
            ci = min(int(t * (len(GRADIENT) - 1)), len(GRADIENT) - 1)
            out.append(f"{c256(GRADIENT[ci])}{ch}")
            vis_idx += 1
    out.append(reset())
    return "".join(out)

def print_banner(model_name):
    print()
    for line in BANNER:
        print(gradient_line(line))
    print(f" {gray()}{model_name} · google ai studio{reset()}")
    print()

# ═══════════════════════════════════════════════════════════════════════════════
# UI helpers
# ═══════════════════════════════════════════════════════════════════════════════

def hr():
    cols = shutil.get_terminal_size((80, 24)).columns
    print(f"{gray()}{'─' * cols}{reset()}")

def print_footer(elapsed, prompt_tokens, response_tokens):
    parts = [f"{green()}✓{reset()} {bold()}{elapsed:.1f}s{reset()}"]
    if prompt_tokens or response_tokens:
        parts.append(f"{cyan()}{prompt_tokens} → {response_tokens} tokens{reset()}")
    print(f" {' · '.join(parts)}")

def error(msg):
    print(f"\n {red()}✗ {msg}{reset()}", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════════════════
# ThinkStreamer — renders <think>...</think> blocks in a bordered box
# ═══════════════════════════════════════════════════════════════════════════════

class ThinkStreamer:
    """
    A streaming text processor that intercepts <think>...</think> tags and renders
    them in a dimmed, bordered box — similar to how ChatGPT/Claude/Gemini show
    chain-of-thought reasoning in a collapsible panel.

    Normal response text streams through to stdout unchanged.
    Thinking text is rendered to stderr in a bordered, dimmed format so it is
    visually distinct from the actual answer.
    """

    def __init__(self, show=True):
        self.show = show          # Whether to display thinking (vs suppress it)
        self.in_think = False     # Currently inside a <think> block?
        self.buffer = ""          # Unprocessed text buffer
        self.at_line_start = True # For formatting think lines with │ prefix
        self.has_thought = False  # Did we see any thinking at all?

    def feed(self, text):
        """Feed a chunk of streamed text."""
        self.buffer += text
        self._process()

    def _process(self):
        while True:
            if not self.in_think:
                idx = self.buffer.find("<think>")
                if idx != -1:
                    # Print everything before <think> as normal response
                    if idx > 0:
                        sys.stdout.write(self.buffer[:idx])
                        sys.stdout.flush()
                    self.in_think = True
                    self.has_thought = True
                    self.buffer = self.buffer[idx + 7:]
                    if self.show:
                        sys.stderr.write(f"\n {gray()}💭 Thinking {'─' * 40}{reset()}\n")
                        sys.stderr.flush()
                    self.at_line_start = True
                else:
                    # Keep last 6 chars in buffer to handle split "<think" tags
                    safe = max(0, len(self.buffer) - 6)
                    if safe > 0:
                        sys.stdout.write(self.buffer[:safe])
                        sys.stdout.flush()
                        self.buffer = self.buffer[safe:]
                    break
            else:
                idx = self.buffer.find("</think>")
                if idx != -1:
                    think_chunk = self.buffer[:idx]
                    if self.show:
                        self._render_think(think_chunk)
                        sys.stderr.write(f"{reset()}\n {gray()}{'─' * 52}{reset()}\n\n")
                        sys.stderr.flush()
                    self.in_think = False
                    self.buffer = self.buffer[idx + 8:]
                    # Strip leading newlines after think block closure
                    self.buffer = self.buffer.lstrip("\n")
                else:
                    # Keep last 7 chars for split "</think" tags
                    safe = max(0, len(self.buffer) - 7)
                    if safe > 0:
                        if self.show:
                            self._render_think(self.buffer[:safe])
                        self.buffer = self.buffer[safe:]
                    break

    def _render_think(self, text):
        """Render thinking text with │ prefix on each line, dimmed."""
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

    def flush(self):
        """Flush remaining buffer content."""
        if self.in_think:
            if self.show:
                self._render_think(self.buffer)
                sys.stderr.write(f"{reset()}\n {gray()}{'─' * 52}{reset()}\n\n")
                sys.stderr.flush()
        else:
            sys.stdout.write(self.buffer)
            sys.stdout.flush()
        self.buffer = ""


def _strip_think_tags(text):
    """Remove <think>...</think> blocks entirely (for --raw mode)."""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)

# ═══════════════════════════════════════════════════════════════════════════════
# Multimodal file support
# ═══════════════════════════════════════════════════════════════════════════════

MEDIA_EXTENSIONS = {
    # Images
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    # Video
    ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".avi": "video/x-msvideo", ".webm": "video/webm",
    # Audio
    ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".ogg": "audio/ogg", ".flac": "audio/flac", ".m4a": "audio/mp4",
    # Documents
    ".pdf": "application/pdf",
}

UPLOAD_THRESHOLD = 20 * 1024 * 1024  # 20 MB — inline below, upload above

def _is_media(path):
    return os.path.splitext(path)[1].lower() in MEDIA_EXTENSIONS

def _mime_type(path):
    return MEDIA_EXTENSIONS.get(os.path.splitext(path)[1].lower())

def _resolve_files(patterns, client=None, is_tty=False):
    """
    Expand glob patterns and read files.

    Text files are read and returned as a context string.
    Media files (images, video, audio, PDF) are loaded as Part objects
    for multimodal prompting.

    Returns: (text_context: str, media_parts: list[Part])
    """
    from google.genai import types

    if not patterns:
        return "", []

    paths = []
    for pattern in patterns:
        expanded = glob.glob(pattern, recursive=True)
        if expanded:
            paths.extend(expanded)
        elif os.path.isfile(pattern):
            paths.append(pattern)
        else:
            print(f"Warning: no files matched '{pattern}'", file=sys.stderr)

    if not paths:
        return "", []

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in paths:
        norm = os.path.normpath(p)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)

    text_blocks = []
    media_parts = []

    for filepath in unique:
        if _is_media(filepath):
            mime = _mime_type(filepath)
            try:
                size = os.path.getsize(filepath)
                if size > UPLOAD_THRESHOLD and client:
                    # Large file — use the Files API to upload
                    uploaded = client.files.upload(path=filepath)
                    media_parts.append(types.Part(
                        file_data=types.FileData(
                            file_uri=uploaded.uri, mime_type=uploaded.mime_type,
                        )
                    ))
                else:
                    with open(filepath, "rb") as f:
                        data = f.read()
                    media_parts.append(types.Part(
                        inline_data=types.Blob(data=data, mime_type=mime)
                    ))
                if is_tty:
                    label = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
                    print(f" {gray()}📎 {os.path.basename(filepath)} ({mime}, {label}){reset()}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: could not load '{filepath}': {e}", file=sys.stderr)
        else:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                text_blocks.append(f"### File: {filepath}\n```\n{content}\n```")
            except Exception as e:
                print(f"Warning: could not read '{filepath}': {e}", file=sys.stderr)

    return "\n\n".join(text_blocks), media_parts


def _build_user_content(text, media_parts=None):
    """Build a user Content object, optionally with media parts for multimodal."""
    from google.genai import types

    parts = list(media_parts or [])
    if text:
        parts.append(types.Part(text=text))
    if not parts:
        parts.append(types.Part(text=""))
    return types.Content(role="user", parts=parts)

# ═══════════════════════════════════════════════════════════════════════════════
# Agent tools (read-only file system + web)
# ═══════════════════════════════════════════════════════════════════════════════

MAX_FILE_CHARS = 100_000
MAX_SEARCH_RESULTS = 200
MAX_URL_CHARS = 80_000

def read_file(path: str) -> str:
    """Read the contents of a file at the given path and return the text."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + f"\n\n[... truncated, file is {len(content)} chars ...]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"

def list_directory(path: str) -> str:
    """List all files and directories at the given path. Returns one entry per line with [DIR] prefix for directories."""
    try:
        entries = []
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            prefix = "[DIR]  " if os.path.isdir(full) else "       "
            entries.append(f"{prefix}{entry}")
        return "\n".join(entries) if entries else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"

def search_files(pattern: str, directory: str = ".") -> str:
    """Search for files matching a glob pattern recursively starting from directory. Returns matching file paths."""
    try:
        matches = glob.glob(os.path.join(directory, pattern), recursive=True)
        if not matches:
            return f"No files matched pattern '{pattern}' in '{directory}'"
        return "\n".join(sorted(matches[:MAX_SEARCH_RESULTS]))
    except Exception as e:
        return f"Error searching: {e}"

def grep_files(pattern: str, directory: str = ".", file_glob: str = "**/*") -> str:
    """Search file contents for lines matching a regex pattern. Returns matching lines with file paths and line numbers."""
    try:
        matches = []
        for filepath in glob.glob(os.path.join(directory, file_glob), recursive=True):
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line):
                            matches.append(f"{filepath}:{i}: {line.rstrip()}")
                            if len(matches) >= MAX_SEARCH_RESULTS:
                                return "\n".join(matches) + f"\n[... truncated at {MAX_SEARCH_RESULTS} matches]"
            except (OSError, IOError):
                continue
        return "\n".join(matches) if matches else f"No matches for pattern '{pattern}'"
    except Exception as e:
        return f"Error searching: {e}"

def fetch_url(url: str) -> str:
    """Fetch a webpage at the given URL and return its text content with HTML tags stripped."""
    try:
        import urllib.request
        import html as html_mod
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; GemmaAgent/1.0)",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        # Strip script/style blocks, convert block tags to newlines, remove remaining tags
        text = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<br[^>]*/?>',  '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = html_mod.unescape(text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        if len(text) > MAX_URL_CHARS:
            text = text[:MAX_URL_CHARS] + f"\n\n[... truncated, page is {len(text)} chars ...]"
        return text
    except Exception as e:
        return f"Error fetching URL: {e}"

AGENT_TOOLS = [read_file, list_directory, search_files, grep_files, fetch_url]

# ═══════════════════════════════════════════════════════════════════════════════
# API helpers
# ═══════════════════════════════════════════════════════════════════════════════

MAX_RETRIES = 5

def _is_retryable(e):
    """Check if an exception is a transient error worth retrying."""
    err_str = str(e).lower()
    type_name = type(e).__name__.lower()
    retryable_strings = ["429", "resource_exhausted", "ssl", "timeout",
                         "connection", "remotedisconnected", "broken pipe",
                         "reset by peer", "503", "500"]
    retryable_types = ["sslerror", "connecterror", "timeout", "readtimeout",
                       "connectionerror", "remotedisconnected", "networkerror"]
    return (any(s in err_str for s in retryable_strings) or
            any(t in type_name for t in retryable_types))

def _retry_wait(attempt):
    """Exponential backoff with jitter."""
    base = 2 ** attempt
    return base + random.uniform(0, base)

def _execute_tool(function_call):
    """Execute a function call from the model and return the result string."""
    name = function_call.name
    args = dict(function_call.args) if function_call.args else {}
    func_map = {f.__name__: f for f in AGENT_TOOLS}
    fn = func_map.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    return fn(**args)

def _ensure_contents_list(contents):
    """Normalize contents to a list suitable for the API."""
    from google.genai import types
    if isinstance(contents, str):
        return [types.Content(role="user", parts=[types.Part(text=contents)])]
    elif isinstance(contents, types.Content):
        return [contents]
    elif isinstance(contents, list):
        return list(contents)  # shallow copy
    return [contents]

# ═══════════════════════════════════════════════════════════════════════════════
# Generation core
# ═══════════════════════════════════════════════════════════════════════════════

def _stream_simple(client, model, contents, config, streamer, raw=False):
    """
    Stream a response without tool-call handling.
    Returns (elapsed, prompt_tokens, response_tokens, full_text).
    """
    t0 = time.time()
    last = None
    full_text = ""

    for chunk in client.models.generate_content_stream(
        model=model, contents=contents, config=config,
    ):
        last = chunk
        if not chunk.candidates:
            continue
        for part in (chunk.candidates[0].content.parts or []):
            is_thought = getattr(part, "thought", False)
            text = getattr(part, "text", None)
            if text:
                if is_thought:
                    # Thinking part — render in the think box
                    if streamer and streamer.show:
                        if not streamer.in_think and not streamer.has_thought:
                            sys.stderr.write(f"\n {gray()}💭 Thinking {'─' * 40}{reset()}\n")
                            sys.stderr.flush()
                            streamer.in_think = True
                            streamer.has_thought = True
                            streamer.at_line_start = True
                        if streamer.in_think:
                            streamer._render_think(text)
                elif streamer:
                    # Close any open think box before printing response text
                    if streamer.in_think:
                        sys.stderr.write(f"{reset()}\n {gray()}{'─' * 52}{reset()}\n\n")
                        sys.stderr.flush()
                        streamer.in_think = False
                    streamer.feed(text)
                else:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                if not is_thought:
                    full_text += text

    if streamer:
        # Close any unclosed think box
        if streamer.in_think:
            sys.stderr.write(f"{reset()}\n {gray()}{'─' * 52}{reset()}\n\n")
            sys.stderr.flush()
            streamer.in_think = False
        streamer.flush()

    elapsed = time.time() - t0
    pt = rt = 0
    if last and hasattr(last, "usage_metadata") and last.usage_metadata:
        pt = getattr(last.usage_metadata, "prompt_token_count", 0) or 0
        rt = getattr(last.usage_metadata, "candidates_token_count", 0) or 0

    if raw:
        full_text = _strip_think_tags(full_text)

    return elapsed, pt, rt, full_text


def _stream_agent(client, model, contents, config, streamer, is_tty, raw=False):
    """
    Stream agent responses with tool-call loop.

    Each turn is streamed in real time. If the model emits function_call parts,
    the tools are executed and the conversation continues. Text (including
    <think> blocks) is piped through the ThinkStreamer for live rendering.

    Returns (elapsed, prompt_tokens, response_tokens, tool_calls, final_text, updated_contents).
    """
    from google.genai import types

    tool_calls_made = []
    t0 = time.time()
    total_pt = 0
    total_rt = 0
    contents = _ensure_contents_list(contents)

    while True:
        turn_text = ""
        turn_fcs = []
        last = None

        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=config,
        ):
            last = chunk
            if not chunk.candidates:
                continue
            for part in (chunk.candidates[0].content.parts or []):
                if part.function_call:
                    turn_fcs.append(part.function_call)
                else:
                    is_thought = getattr(part, "thought", False)
                    text = getattr(part, "text", None)
                    if text:
                        if is_thought:
                            if streamer and streamer.show:
                                if not streamer.in_think and not streamer.has_thought:
                                    sys.stderr.write(f"\n {gray()}💭 Thinking {'─' * 40}{reset()}\n")
                                    sys.stderr.flush()
                                    streamer.in_think = True
                                    streamer.has_thought = True
                                    streamer.at_line_start = True
                                if streamer.in_think:
                                    streamer._render_think(text)
                        elif streamer:
                            if streamer.in_think:
                                sys.stderr.write(f"{reset()}\n {gray()}{'─' * 52}{reset()}\n\n")
                                sys.stderr.flush()
                                streamer.in_think = False
                            streamer.feed(text)
                        elif not raw:
                            sys.stdout.write(text)
                            sys.stdout.flush()
                        if not is_thought:
                            turn_text += text

        # Token counts — prompt count from last turn reflects full history
        if last and hasattr(last, "usage_metadata") and last.usage_metadata:
            total_pt = getattr(last.usage_metadata, "prompt_token_count", 0) or 0
            total_rt += getattr(last.usage_metadata, "candidates_token_count", 0) or 0

        if not turn_fcs:
            # Final answer — done
            if streamer:
                if streamer.in_think:
                    sys.stderr.write(f"{reset()}\n {gray()}{'─' * 52}{reset()}\n\n")
                    sys.stderr.flush()
                    streamer.in_think = False
                streamer.flush()
            break

        # Build model's response content for conversation history
        model_parts = []
        if turn_text:
            model_parts.append(types.Part(text=turn_text))
        for fc in turn_fcs:
            model_parts.append(types.Part(function_call=fc))
        contents.append(types.Content(role="model", parts=model_parts))

        # Execute tool calls, show indicators, and build function responses
        response_parts = []
        for fc in turn_fcs:
            tool_calls_made.append(fc.name)
            args_str = ", ".join(f"{k}={v!r}" for k, v in (fc.args or {}).items())
            if is_tty and not raw:
                sys.stderr.write(f" {gray()}⚡ {fc.name}({args_str}){reset()}\n")
                sys.stderr.flush()
            result_str = _execute_tool(fc)
            response_parts.append(types.Part(function_response=types.FunctionResponse(
                name=fc.name,
                response={"result": result_str},
            )))

        contents.append(types.Content(role="user", parts=response_parts))

    # Append the final model answer to the contents for history tracking
    if turn_text:
        contents.append(types.Content(
            role="model", parts=[types.Part(text=turn_text)],
        ))

    elapsed = time.time() - t0

    if raw:
        turn_text = _strip_think_tags(turn_text)
        sys.stdout.write(turn_text)
        sys.stdout.flush()

    return elapsed, total_pt, total_rt, tool_calls_made, turn_text, contents


def _generate_no_stream(client, model, contents, config, streamer, raw=False):
    """
    Non-streaming generation without tools.
    Returns (elapsed, prompt_tokens, response_tokens, full_text).
    """
    t0 = time.time()
    response = client.models.generate_content(
        model=model, contents=contents, config=config,
    )
    elapsed = time.time() - t0

    text = ""
    try:
        text = "".join(
            p.text for p in response.candidates[0].content.parts
            if hasattr(p, "text") and p.text
        )
    except (AttributeError, IndexError):
        pass

    pt = rt = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        pt = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        rt = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

    if raw:
        text = _strip_think_tags(text)
        sys.stdout.write(text)
        sys.stdout.flush()
    elif streamer:
        streamer.feed(text)
        streamer.flush()
    else:
        sys.stdout.write(text)
        sys.stdout.flush()

    return elapsed, pt, rt, text

# ═══════════════════════════════════════════════════════════════════════════════
# Agent config builder
# ═══════════════════════════════════════════════════════════════════════════════

def _build_config(state):
    """Build a GenerateContentConfig from the current session state."""
    from google.genai import types

    config = types.GenerateContentConfig(
        max_output_tokens=state["max_tokens"],
        temperature=state["temperature"],
    )

    # Enable thinking mode — thoughts are returned as separate parts
    if state.get("show_thinking") is not False:
        try:
            config.thinking_config = types.ThinkingConfig(include_thoughts=True)
        except (AttributeError, TypeError):
            pass  # SDK version doesn't support ThinkingConfig

    system_parts = []

    # Agent mode — inject tool descriptions and CWD into system prompt
    if state["agent"]:
        cwd = os.getcwd()
        tool_hint = (
            f"You are an autonomous agent with read-only access to the user's file system and the internet.\n"
            f"Current working directory: {cwd}\n\n"
            f"Available tools:\n"
            f"- read_file(path): Read a file's contents\n"
            f"- list_directory(path): List files and subdirectories\n"
            f"- search_files(pattern, directory): Find files by glob pattern\n"
            f"- grep_files(pattern, directory, file_glob): Search file contents by regex\n"
            f"- fetch_url(url): Fetch a webpage and return its text\n"
            f"- google_search: Search Google for information (built-in)\n\n"
            f"Use these tools when the task genuinely requires them (e.g. reading files, browsing the web).\n"
            f"Do NOT use tools for tasks you can answer from your own knowledge."
        )
        system_parts.append(tool_hint)

        try:
            config.tools = [
                types.Tool(google_search=types.GoogleSearch()),
                *AGENT_TOOLS,
            ]
            config.tool_config = types.ToolConfig(
                include_server_side_tool_invocations=True,
            )
        except (AttributeError, TypeError):
            # google_search not supported for this model/SDK version
            config.tools = AGENT_TOOLS

    # Custom system instruction
    if state.get("system"):
        system_parts.append(state["system"])

    if system_parts:
        config.system_instruction = "\n\n".join(system_parts)

    return config

# ═══════════════════════════════════════════════════════════════════════════════
# Slash commands
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SlashCommandSpec:
    name: str
    description: str
    arg_hint: str = ""


SLASH_COMMAND_SPECS = (
    SlashCommandSpec("/help", "Show available slash commands"),
    SlashCommandSpec("/clear", "Clear conversation history and start fresh"),
    SlashCommandSpec("/system", "Show or update the system instruction", "[text]"),
    SlashCommandSpec("/file", "Attach a file or glob to the next message", "<path>"),
    SlashCommandSpec("/files", "Show files currently attached for the next turn"),
    SlashCommandSpec("/think", "Toggle thinking block visibility"),
    SlashCommandSpec("/temp", "Set the generation temperature", "<0.0-2.0>"),
    SlashCommandSpec("/exit", "Exit interactive mode"),
    SlashCommandSpec("/quit", "Exit interactive mode"),
)

SLASH_COMMANDS = [spec.name for spec in SLASH_COMMAND_SPECS]
SLASH_COMMAND_INDEX = {spec.name: spec for spec in SLASH_COMMAND_SPECS}

SLASH_HELP_TEXT = """\
 {h}Available commands:{r}

  {c}/help{r}              Show this message
  {c}/clear{r}             Clear conversation history
  {c}/system{r} [text]     Show or set system instruction
  {c}/file{r} <path>       Attach a file to the next message
  {c}/files{r}             Show currently attached files
  {c}/think{r}             Toggle thinking display
  {c}/temp{r} <value>      Set temperature (0.0–2.0)
  {c}/exit{r}              Exit interactive mode
"""


def _create_prompt_session(input_obj=None, output_obj=None):
    try:
        prompt_module = importlib.import_module("prompt_toolkit.shortcuts.prompt")
        completion_module = importlib.import_module("prompt_toolkit.completion")
        formatted_text_module = importlib.import_module("prompt_toolkit.formatted_text")
        styles_module = importlib.import_module("prompt_toolkit.styles")
        key_binding_module = importlib.import_module("prompt_toolkit.key_binding")
        app_current_module = importlib.import_module("prompt_toolkit.application.current")
    except ImportError as exc:
        raise RuntimeError(
            "prompt-toolkit is required for interactive mode. "
            "Install it with `python -m pip install -e .`."
        ) from exc

    prompt_session_cls = getattr(prompt_module, "PromptSession")
    completer_base_cls = getattr(completion_module, "Completer")
    completion_cls = getattr(completion_module, "Completion")
    ansi_cls = getattr(formatted_text_module, "ANSI")
    complete_style_enum = getattr(prompt_module, "CompleteStyle")
    style_cls = getattr(styles_module, "Style")
    key_bindings_cls = getattr(key_binding_module, "KeyBindings")
    get_app = getattr(app_current_module, "get_app")

    class SlashCommandCompleter(completer_base_cls):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/") or " " in text:
                return

            query = text[1:].lower()
            matches = []
            for spec in SLASH_COMMAND_SPECS:
                name = spec.name[1:].lower()
                if not query:
                    rank = 0
                elif name.startswith(query):
                    rank = 1
                elif query in name:
                    rank = 2
                else:
                    continue
                matches.append((rank, spec.name, spec))

            for _, _, spec in sorted(matches, key=lambda item: item[:2]):
                insert_text = spec.name + (" " if spec.arg_hint else "")
                display_text = spec.name
                if spec.arg_hint:
                    display_text = f"{display_text} {spec.arg_hint}"
                yield completion_cls(
                    insert_text,
                    start_position=-len(text),
                    display=display_text,
                    display_meta=spec.description,
                    selected_style="fg:#ffffff bg:#0b5cad",
                )

    def current_slash_spec():
        buffer = get_app().current_buffer
        state = buffer.complete_state
        if state and state.current_completion:
            completion = state.current_completion
            return SLASH_COMMAND_INDEX.get(completion.text.rstrip())

        text = buffer.text.strip()
        if text.startswith("/") and " " not in text:
            return SLASH_COMMAND_INDEX.get(text)
        return None

    def slash_toolbar():
        buffer = get_app().current_buffer
        text = buffer.document.text_before_cursor
        if not text.startswith("/"):
            return ""

        spec = current_slash_spec()
        if spec:
            hint = spec.arg_hint or "no arguments"
            return ansi_cls(
                f" {bold()}{spec.name}{reset()}  {dim()}{spec.description}{reset()}  "
                f"{gray()}args:{reset()} {hint}  "
                f"{gray()}Enter{reset()} apply  {gray()}↑↓{reset()} navigate  "
                f"{gray()}Esc{reset()} dismiss"
            )

        return ansi_cls(
            f" {bold()}Slash commands{reset()}  {dim()}type to filter{reset()}  "
            f"{gray()}Enter{reset()} apply  {gray()}↑↓{reset()} navigate  "
            f"{gray()}Esc{reset()} dismiss"
        )

    bindings = key_bindings_cls()

    @bindings.add("enter")
    def _(event):
        buffer = event.current_buffer
        state = buffer.complete_state
        if (
            state
            and state.current_completion
            and buffer.text.startswith("/")
            and " " not in buffer.document.text_before_cursor
        ):
            completion = state.current_completion
            buffer.apply_completion(completion)
            spec = SLASH_COMMAND_INDEX.get(completion.text.rstrip())
            if spec and not spec.arg_hint:
                buffer.validate_and_handle()
            return
        buffer.validate_and_handle()

    @bindings.add("tab")
    def _(event):
        buffer = event.current_buffer
        state = buffer.complete_state
        if state and state.current_completion:
            buffer.apply_completion(state.current_completion)
            return
        if buffer.text.startswith("/"):
            buffer.start_completion(select_first=True)

    @bindings.add("escape")
    def _(event):
        buffer = event.current_buffer
        if buffer.complete_state:
            buffer.cancel_completion()

    session = prompt_session_cls(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        complete_style=complete_style_enum.COLUMN,
        reserve_space_for_menu=8,
        bottom_toolbar=slash_toolbar,
        key_bindings=bindings,
        style=style_cls.from_dict({
            "completion-menu.completion": "bg:#101418 #c9d1d9",
            "completion-menu.completion.current": "bg:#0b5cad #ffffff",
            "completion-menu.meta.completion": "bg:#161b22 #7d8590",
            "completion-menu.meta.completion.current": "bg:#0b5cad #dbeafe",
            "scrollbar.background": "bg:#161b22",
            "scrollbar.button": "bg:#3b82f6",
            "bottom-toolbar": "bg:#0f141a #c9d1d9",
        }),
        mouse_support=True,
        input=input_obj,
        output=output_obj,
    )
    return session, ansi_cls


def _handle_slash(cmd_line, state):
    """
    Handle a slash command. Modifies state dict in place.

    Returns True if the command was handled, False if not a known command.
    """
    parts = cmd_line.strip().split(None, 1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/help":
        print(SLASH_HELP_TEXT.format(h=bold(), r=reset(), c=cyan()))
        return True

    elif cmd == "/clear":
        state["history"] = []
        state["pending_media_paths"] = []
        print(f" {green()}✓{reset()} Conversation cleared")
        return True


    elif cmd == "/system":
        if arg:
            state["system"] = arg
            state["history"] = []
            print(f" {green()}✓{reset()} System instruction updated")
        else:
            si = state.get("system") or "(none)"
            print(f" System: {dim()}{si}{reset()}")
        return True

    elif cmd == "/file":
        if not arg:
            print(f" {yellow()}Usage: /file <path>{reset()}")
            return True
        path = arg.strip("\"'")
        if os.path.isfile(path):
            state["pending_media_paths"].append(path)
            print(f" {green()}📎{reset()} Attached: {os.path.basename(path)}")
        else:
            matches = glob.glob(path, recursive=True)
            if matches:
                for m in matches:
                    state["pending_media_paths"].append(m)
                    print(f" {green()}📎{reset()} Attached: {m}")
            else:
                print(f" {red()}✗ File not found: {path}{reset()}")
        return True

    elif cmd == "/files":
        pending = state.get("pending_media_paths", [])
        if pending:
            print(f" Attached files:")
            for p in pending:
                print(f"   📎 {p}")
        else:
            print(f" {gray()}No files attached{reset()}")
        return True


    elif cmd == "/think":
        state["show_thinking"] = not state["show_thinking"]
        status = f"{green()}shown{reset()}" if state["show_thinking"] else f"{gray()}hidden{reset()}"
        print(f" {green()}✓{reset()} Thinking: {status}")
        return True

    elif cmd == "/temp":
        if arg:
            try:
                val = float(arg)
                if 0.0 <= val <= 2.0:
                    state["temperature"] = val
                    print(f" {green()}✓{reset()} Temperature → {val}")
                else:
                    print(f" {red()}✗ Must be between 0.0 and 2.0{reset()}")
            except ValueError:
                print(f" {red()}✗ Invalid number: {arg}{reset()}")
        else:
            print(f" Temperature: {state.get('temperature', 0.7)}")
        return True

    elif cmd in ("/exit", "/quit"):
        raise SystemExit(0)

    return False

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Gemma 4 via Google AI Studio",
        prog="gemma",
    )
    parser.add_argument("prompt", nargs="*", help="The prompt to send. If empty, starts interactive mode.")
    parser.add_argument("--file", action="append", default=[], metavar="PATH",
                        help="File path or glob pattern to include as context (repeatable)")
    parser.add_argument("--system", default=None, help="System instruction")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--model", default=None, help="Model override")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")
    parser.add_argument("--no-banner", action="store_true", help="Hide ASCII banner")
    parser.add_argument("--raw", action="store_true", help="Raw output, no formatting")

    parser.add_argument("--no-think", action="store_true",
                        help="Hide thinking blocks")
    args = parser.parse_args()

    # Display mode
    global USE_COLOR
    is_tty = sys.stdout.isatty() and not args.raw
    USE_COLOR = is_tty
    show_banner = is_tty and not args.no_banner
    stream = not args.no_stream
    raw = args.raw

    # API key
    api_key = os.environ.get("GOOGLE_AI_STUDIO_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        error("Set GOOGLE_AI_STUDIO_KEY or GEMINI_API_KEY environment variable")
        sys.exit(1)

    # Lazy import (keeps --help fast)
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model = args.model or os.environ.get("GEMMA_MODEL", "gemma-4-31b-it")

    # Session state — shared between main loop and slash commands
    state = {
        "model": model,
        "agent": True,
        "system": args.system,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "show_thinking": not args.no_think,
        "stream": stream,
        "history": [],
        "pending_media_paths": [],
    }

    # Resolve --file patterns (text + media)
    file_context, file_media = _resolve_files(args.file, client=client, is_tty=is_tty)

    # Build prompt from positional args
    prompt_text = " ".join(args.prompt).strip()

    # ── CLI slash commands (e.g., `gemma /help`) ──────────────────────────
    if prompt_text.startswith("/"):
        if _handle_slash(prompt_text, state):
            return

    # Merge file context into prompt
    if file_context:
        prompt_text = file_context + "\n\n" + prompt_text if prompt_text else file_context

    interactive = not bool(prompt_text) and not file_media

    # Banner
    if show_banner:
        print_banner(state["model"])
        hr()

    if interactive:
        # ══════════════════════════════════════════════════════════════════
        # Interactive mode
        # ══════════════════════════════════════════════════════════════════

        session = None
        ansi = None
        if sys.stdin.isatty():
            try:
                session, ansi = _create_prompt_session()
            except RuntimeError as e:
                error(str(e))
                sys.exit(1)

        if is_tty:
            print(f" {gray()}Interactive mode · type /help for commands · Ctrl+C to exit{reset()}")
            print()

        while True:
            try:
                if session and ansi:
                    user_input = session.prompt(ansi(f" {cyan()}❯{reset()} "))
                else:
                    user_input = input(f" {cyan()}❯{reset()} ")
                if not user_input.strip():
                    continue
            except (KeyboardInterrupt, EOFError):
                print()
                break

            # Slash command?
            if user_input.strip().startswith("/"):
                try:
                    handled = _handle_slash(user_input.strip(), state)
                    if not handled:
                        print(f" {yellow()}Unknown command. Type /help for available commands.{reset()}")
                except SystemExit:
                    break
                print()
                continue

            # Build config for this turn
            config = _build_config(state)

            # Resolve any pending file attachments from /file commands
            file_ctx = ""
            pending_media = []
            if state["pending_media_paths"]:
                file_ctx, pending_media = _resolve_files(
                    state["pending_media_paths"], client=client, is_tty=is_tty,
                )
                state["pending_media_paths"] = []

            # Prepend text file context to user's message
            msg_text = user_input
            if file_ctx:
                msg_text = file_ctx + "\n\n" + msg_text

            try:
                user_content = _build_user_content(msg_text, pending_media)
                state["history"].append(user_content)

                streamer = ThinkStreamer(show=state["show_thinking"]) if is_tty else None

                # Always use agent mode with streaming
                elapsed, pt, rt, tools, text, updated = _stream_agent(
                    client, state["model"], state["history"],
                    config, streamer, is_tty,
                )
                state["history"] = updated

                # Footer
                if is_tty:
                    print()
                    hr()
                    print_footer(elapsed, pt, rt)
                    print()

            except Exception as e:
                if _is_retryable(e):
                    wait = _retry_wait(0)
                    print(f"\n {red()}✗ {e} — retrying in {wait:.1f}s...{reset()}", file=sys.stderr)
                    time.sleep(wait)
                else:
                    error(str(e))
                    # Remove the failed user message from history
                    if state["history"]:
                        state["history"].pop()
                print()

    else:
        # ══════════════════════════════════════════════════════════════════
        # Single-shot mode
        # ══════════════════════════════════════════════════════════════════
        contents = _build_user_content(prompt_text, file_media)

        for attempt in range(MAX_RETRIES):
            try:
                config = _build_config(state)

                if state["agent"]:
                    streamer = ThinkStreamer(show=state["show_thinking"]) if is_tty else None
                    elapsed, pt, rt, tools, text, _ = _stream_agent(
                        client, state["model"], contents, config,
                        streamer, is_tty, raw=raw,
                    )

                elif stream:
                    streamer = ThinkStreamer(show=state["show_thinking"]) if is_tty else None
                    elapsed, pt, rt, text = _stream_simple(
                        client, state["model"], contents, config,
                        streamer, raw=raw,
                    )

                else:
                    streamer = ThinkStreamer(show=state["show_thinking"]) if is_tty else None
                    elapsed, pt, rt, text = _generate_no_stream(
                        client, state["model"], contents, config,
                        streamer, raw=raw,
                    )

                # Footer
                if is_tty:
                    print()
                    hr()
                    print_footer(elapsed, pt, rt)
                    print()

                return

            except Exception as e:
                if _is_retryable(e) and attempt < MAX_RETRIES - 1:
                    wait = _retry_wait(attempt)
                    if is_tty:
                        print(f"\n {gray()}error: {e}, retrying in {wait:.1f}s...{reset()}", file=sys.stderr)
                    else:
                        print(f"Error: {e}, retrying in {wait:.1f}s...", file=sys.stderr)
                    time.sleep(wait)
                else:
                    error(str(e))
                    sys.exit(1)


if __name__ == "__main__":
    main()
