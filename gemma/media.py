"""Multimodal file input: glob resolution, text context, and media Parts."""

import glob
import os
import sys

from .ui import gray, reset

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

# Files larger than this are uploaded via the Files API; smaller ones go inline.
UPLOAD_THRESHOLD = 20 * 1024 * 1024


def _is_media(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in MEDIA_EXTENSIONS


def _mime_type(path: str) -> str | None:
    return MEDIA_EXTENSIONS.get(os.path.splitext(path)[1].lower())


def resolve_files(patterns, client=None, is_tty: bool = False):
    """
    Expand glob patterns and read files.

    Text files are returned as a context string. Media files (images, video,
    audio, PDF) are loaded as Part objects for multimodal prompting.

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


def build_user_content(text: str, media_parts=None):
    """Build a user Content object, optionally with media parts for multimodal."""
    from google.genai import types

    parts = list(media_parts or [])
    if text:
        parts.append(types.Part(text=text))
    if not parts:
        parts.append(types.Part(text=""))
    return types.Content(role="user", parts=parts)
