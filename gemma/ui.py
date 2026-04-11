"""ANSI colors, banner, and terminal UI helpers."""

import os
import shutil
import sys

_USE_COLOR = False


def set_color(enabled: bool) -> None:
    global _USE_COLOR
    _USE_COLOR = enabled


def enable_windows_ansi() -> None:
    """Turn on ANSI escape processing and UTF-8 output on Windows."""
    if os.name == "nt":
        os.system("")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def _sg(code):
    return f"\033[{code}m" if _USE_COLOR else ""


def reset():   return _sg(0)
def dim():     return _sg(2)
def bold():    return _sg(1)
def red():     return _sg("1;31")
def green():   return _sg("1;32")
def yellow():  return _sg("1;33")
def cyan():    return _sg(36)
def gray():    return _sg(90)


def c256(n):
    return f"\033[38;5;{n}m" if _USE_COLOR else ""


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
    if not _USE_COLOR:
        return text
    out = []
    visible = [i for i, ch in enumerate(text) if ch != " "]
    n = max(len(visible) - 1, 1)
    vis_idx = 0
    for ch in text:
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
