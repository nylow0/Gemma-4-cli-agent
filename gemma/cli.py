"""Gemma CLI entry point: argparse, main, and interactive/single-shot dispatch."""

import argparse
import os
import sys
import time

from . import ui
from .api import MAX_RETRIES, build_config, is_retryable, retry_wait, stream_agent
from .media import build_user_content, resolve_files
from .slash import create_prompt_session, handle_slash
from .streaming import ThinkStreamer
from .ui import cyan, error, gray, hr, print_banner, print_footer, reset, yellow


def _run_with_retries(call):
    """
    Execute `call()` with retry-on-transient-error.

    `call` is a zero-arg callable that performs one API attempt. On a
    retryable exception it is retried up to MAX_RETRIES times with
    exponential backoff; on a non-retryable exception or exhaustion,
    the last exception is re-raised.
    """
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            return call()
        except Exception as e:
            last_exc = e
            if not is_retryable(e) or attempt == MAX_RETRIES - 1:
                raise
            wait = retry_wait(attempt)
            print(
                f"\n {gray()}error: {e} — retrying in {wait:.1f}s...{reset()}",
                file=sys.stderr,
            )
            time.sleep(wait)
    if last_exc:
        raise last_exc


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
    parser.add_argument("--no-banner", action="store_true", help="Hide ASCII banner")
    parser.add_argument("--raw", action="store_true", help="Raw output, no formatting")
    parser.add_argument("--no-think", action="store_true", help="Hide thinking blocks")
    args = parser.parse_args()

    ui.enable_windows_ansi()

    is_tty = sys.stdout.isatty() and not args.raw
    ui.set_color(is_tty)
    show_banner = is_tty and not args.no_banner
    raw = args.raw

    api_key = os.environ.get("GOOGLE_AI_STUDIO_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        error("Set GOOGLE_AI_STUDIO_KEY or GEMINI_API_KEY environment variable")
        sys.exit(1)

    # Lazy import keeps --help fast.
    from google import genai  # noqa: F401

    client = genai.Client(api_key=api_key)
    model = args.model or os.environ.get("GEMMA_MODEL", "gemma-4-31b-it")

    state = {
        "model": model,
        "system": args.system,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "show_thinking": not args.no_think,
        "history": [],
        "pending_media_paths": [],
    }

    file_context, file_media = resolve_files(args.file, client=client, is_tty=is_tty)
    prompt_text = " ".join(args.prompt).strip()

    # CLI slash commands (e.g., `gemma /help`)
    if prompt_text.startswith("/"):
        if handle_slash(prompt_text, state):
            return

    if file_context:
        prompt_text = file_context + "\n\n" + prompt_text if prompt_text else file_context

    interactive = not bool(prompt_text) and not file_media

    if show_banner:
        print_banner(state["model"])
        hr()

    if interactive:
        _run_interactive(client, state, is_tty)
    else:
        _run_single_shot(client, state, prompt_text, file_media, is_tty, raw)


def _run_interactive(client, state, is_tty):
    session = None
    ansi = None
    if sys.stdin.isatty():
        try:
            session, ansi = create_prompt_session()
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

        if user_input.strip().startswith("/"):
            try:
                handled = handle_slash(user_input.strip(), state)
                if not handled:
                    print(f" {yellow()}Unknown command. Type /help for available commands.{reset()}")
            except SystemExit:
                break
            print()
            continue

        config = build_config(state)

        file_ctx = ""
        pending_media = []
        if state["pending_media_paths"]:
            file_ctx, pending_media = resolve_files(
                state["pending_media_paths"], client=client, is_tty=is_tty,
            )
            state["pending_media_paths"] = []

        msg_text = user_input
        if file_ctx:
            msg_text = file_ctx + "\n\n" + msg_text

        user_content = build_user_content(msg_text, pending_media)
        state["history"].append(user_content)

        try:
            def call():
                # Fresh streamer per attempt so retry state is clean.
                streamer = ThinkStreamer(show=state["show_thinking"]) if is_tty else None
                return stream_agent(
                    client, state["model"], state["history"],
                    config, streamer, is_tty,
                )

            elapsed, pt, rt, _tools, _text, updated = _run_with_retries(call)
            state["history"] = updated

            if is_tty:
                print()
                hr()
                print_footer(elapsed, pt, rt)
                print()
        except Exception as e:
            error(str(e))
            if state["history"]:
                state["history"].pop()
            print()


def _run_single_shot(client, state, prompt_text, file_media, is_tty, raw):
    contents = build_user_content(prompt_text, file_media)

    try:
        def call():
            config = build_config(state)
            streamer = ThinkStreamer(show=state["show_thinking"]) if is_tty else None
            return stream_agent(
                client, state["model"], contents, config,
                streamer, is_tty, raw=raw,
            )

        elapsed, pt, rt, _tools, _text, _ = _run_with_retries(call)

        if is_tty:
            print()
            hr()
            print_footer(elapsed, pt, rt)
            print()
    except Exception as e:
        error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
