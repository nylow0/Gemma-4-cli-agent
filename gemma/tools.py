"""Read-only agent tools: file system access and web fetch."""

import glob
import os
import re

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
        text = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<br[^>]*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = html_mod.unescape(text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        if len(text) > MAX_URL_CHARS:
            text = text[:MAX_URL_CHARS] + f"\n\n[... truncated, page is {len(text)} chars ...]"
        return text
    except Exception as e:
        return f"Error fetching URL: {e}"


AGENT_TOOLS = [read_file, list_directory, search_files, grep_files, fetch_url]
