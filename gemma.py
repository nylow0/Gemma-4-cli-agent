import argparse
import glob
import os
import shutil
import sys
import time

# Enable ANSI escape sequences on Windows
if os.name == "nt":
    os.system("")

# ANSI 

USE_COLOR = False

def _sg(code):
    return f"\033[{code}m" if USE_COLOR else ""

def reset():   return _sg(0)
def dim():     return _sg(2)
def bold():    return _sg(1)
def red():     return _sg("1;31")
def green():   return _sg("1;32")
def cyan():    return _sg(36)
def gray():    return _sg(90)

def c256(n):
    return f"\033[38;5;{n}m" if USE_COLOR else ""

# Banner 

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

# UI helpers

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

# File context

def _resolve_files(patterns):
    """Expand glob patterns, read files, return a single context string."""
    if not patterns:
        return ""
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
        return ""
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in paths:
        norm = os.path.normpath(p)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    blocks = []
    for filepath in unique:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            blocks.append(f"### File: {filepath}\n```\n{content}\n```")
        except Exception as e:
            print(f"Warning: could not read '{filepath}': {e}", file=sys.stderr)
    return "\n\n".join(blocks)

# File system tools (for --agent mode)

MAX_FILE_CHARS = 100_000
MAX_SEARCH_RESULTS = 200

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

AGENT_TOOLS = [read_file, list_directory, search_files]

def _execute_tool(function_call):
    """Execute a function call from the model and return the result string."""
    name = function_call.name
    args = dict(function_call.args) if function_call.args else {}
    func_map = {f.__name__: f for f in AGENT_TOOLS}
    fn = func_map.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    return fn(**args)

def _agent_generate(client, model, contents, config, is_tty):
    """Run a generate-then-tool-call loop until the model produces a text-only response."""
    from google.genai import types

    t0 = time.time()
    tool_calls_made = []

    while True:
        response = client.models.generate_content(
            model=model, contents=contents, config=config,
        )

        # Check if the response contains function calls
        has_function_call = False
        for candidate in (response.candidates or []):
            for part in (candidate.content.parts or []):
                if part.function_call:
                    has_function_call = True
                    fc = part.function_call
                    tool_calls_made.append(fc.name)
                    if is_tty:
                        print(f" {gray()}[tool: {fc.name}({', '.join(f'{k}={v!r}' for k, v in (fc.args or {}).items())})]{reset()}", file=sys.stderr)
                    result_str = _execute_tool(fc)
                    # Build function response and append to contents for next turn
                    contents = [
                        *([contents] if isinstance(contents, str) else contents),
                        response.candidates[0].content,
                        types.Content(
                            role="user",
                            parts=[types.Part(function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result_str},
                            ))],
                        ),
                    ]
                    break  # Process one tool call at a time
            if has_function_call:
                break

        if not has_function_call:
            break

    elapsed = time.time() - t0
    text = response.text or ""
    prompt_tokens = 0
    response_tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        response_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

    return text, elapsed, prompt_tokens, response_tokens, tool_calls_made

# Main

def main():
    parser = argparse.ArgumentParser(
        description="Gemma 4 31B via Google AI Studio",
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
    parser.add_argument("--agent", action="store_true",
                        help="Enable file system tools (read, list, search)")
    args = parser.parse_args()

    # Determine display mode
    global USE_COLOR
    is_tty = sys.stdout.isatty() and not args.raw
    USE_COLOR = is_tty
    show_banner = is_tty and not args.no_banner
    stream = is_tty and not args.no_stream

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

    config = types.GenerateContentConfig(
        max_output_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    if args.system:
        config.system_instruction = args.system

    # Agent mode: attach file system tools
    if args.agent:
        config.tools = AGENT_TOOLS
        cwd = os.getcwd()
        tool_hint = (
            f"You have read-only access to the user's file system. "
            f"Current working directory: {cwd}\n"
            f"Use the available tools (read_file, list_directory, search_files) "
            f"to browse and read files when needed to answer the user's question."
        )
        if config.system_instruction:
            config.system_instruction = tool_hint + "\n\n" + config.system_instruction
        else:
            config.system_instruction = tool_hint

    # Resolve --file patterns and read contents
    file_context = _resolve_files(args.file)

    prompt = " ".join(args.prompt).strip()
    if file_context:
        prompt = file_context + "\n\n" + prompt if prompt else file_context
    interactive = not bool(prompt)

    # Banner
    if show_banner:
        print_banner(model)
        hr()

    if interactive:
        if is_tty:
            print(f" {gray()}Entering interactive mode. Press Ctrl+C to exit.{reset()}")
            print()
        chat = client.chats.create(model=model, config=config)
        while True:
            try:
                user_msg = input(f" {cyan()}❯{reset()} ")
                if not user_msg.strip():
                    continue
            except (KeyboardInterrupt, EOFError):
                print()
                break

            try:
                t0 = time.time()
                prompt_tokens = 0
                response_tokens = 0

                if args.agent:
                    # Agent mode uses non-streaming to support tool calls
                    response = chat.send_message(user_msg)
                    elapsed = time.time() - t0
                    text = response.text or ""
                    print(text, end="")
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                        response_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                elif stream:
                    last = None
                    for chunk in chat.send_message_stream(user_msg):
                        if chunk.text:
                            sys.stdout.write(chunk.text)
                            sys.stdout.flush()
                        last = chunk
                    elapsed = time.time() - t0
                    if last and hasattr(last, "usage_metadata") and last.usage_metadata:
                        prompt_tokens = getattr(last.usage_metadata, "prompt_token_count", 0) or 0
                        response_tokens = getattr(last.usage_metadata, "candidates_token_count", 0) or 0
                else:
                    response = chat.send_message(user_msg)
                    elapsed = time.time() - t0
                    text = response.text or ""
                    print(text, end="")
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                        response_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

                # Footer
                if is_tty:
                    print()
                    hr()
                    print_footer(elapsed, prompt_tokens, response_tokens)
                    print()

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"\n {red()}✗ Rate limited by API.{reset()}", file=sys.stderr)
                else:
                    error(str(e))
                print()

    else:
        # Retry with exponential backoff for single-shot command
        for attempt in range(3):
            try:
                t0 = time.time()
                prompt_tokens = 0
                response_tokens = 0

                if args.agent:
                    # Agent mode: non-streaming with tool-call loop
                    text, elapsed, prompt_tokens, response_tokens, tool_calls = \
                        _agent_generate(client, model, prompt, config, is_tty)
                    print(text, end="")
                elif stream:
                    last = None
                    for chunk in client.models.generate_content_stream(
                        model=model, contents=prompt, config=config,
                    ):
                        if chunk.text:
                            sys.stdout.write(chunk.text)
                            sys.stdout.flush()
                        last = chunk
                    elapsed = time.time() - t0
                    if last and hasattr(last, "usage_metadata") and last.usage_metadata:
                        prompt_tokens = getattr(last.usage_metadata, "prompt_token_count", 0) or 0
                        response_tokens = getattr(last.usage_metadata, "candidates_token_count", 0) or 0
                else:
                    response = client.models.generate_content(
                        model=model, contents=prompt, config=config,
                    )
                    elapsed = time.time() - t0
                    text = response.text or ""
                    print(text, end="")
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                        response_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

                # Footer
                if is_tty:
                    print()
                    hr()
                    print_footer(elapsed, prompt_tokens, response_tokens)
                    print()

                return

            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < 2:
                    wait = 2 ** attempt
                    if is_tty:
                        print(f"\n {gray()}rate limited, retrying in {wait}s...{reset()}", file=sys.stderr)
                    else:
                        print(f"Rate limited, retrying in {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                else:
                    error(str(e))
                    sys.exit(1)


if __name__ == "__main__":
    main()
