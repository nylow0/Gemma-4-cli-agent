import argparse
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

# Main

def main():
    parser = argparse.ArgumentParser(
        description="Gemma 4 31B via Google AI Studio",
        prog="gemma",
    )
    parser.add_argument("prompt", nargs="*", help="The prompt to send. If empty, starts interactive mode.")
    parser.add_argument("--system", default=None, help="System instruction")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--model", default=None, help="Model override")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")
    parser.add_argument("--no-banner", action="store_true", help="Hide ASCII banner")
    parser.add_argument("--raw", action="store_true", help="Raw output, no formatting")
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

    prompt = " ".join(args.prompt).strip()
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

                if stream:
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

                if stream:
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
