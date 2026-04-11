"""Generation core: retries, config builder, and the streaming agent loop."""

import os
import random
import sys
import time

from .streaming import strip_think_tags
from .tools import AGENT_TOOLS
from .ui import gray, reset

MAX_RETRIES = 5


def is_retryable(e: Exception) -> bool:
    """Return True if an exception is a transient error worth retrying."""
    err_str = str(e).lower()
    type_name = type(e).__name__.lower()
    retryable_strings = ("429", "resource_exhausted", "ssl", "timeout",
                         "connection", "remotedisconnected", "broken pipe",
                         "reset by peer", "503", "500")
    retryable_types = ("sslerror", "connecterror", "timeout", "readtimeout",
                       "connectionerror", "remotedisconnected", "networkerror")
    return (any(s in err_str for s in retryable_strings) or
            any(t in type_name for t in retryable_types))


def retry_wait(attempt: int) -> float:
    """Exponential backoff with jitter."""
    base = 2 ** attempt
    return base + random.uniform(0, base)


def _execute_tool(function_call) -> str:
    name = function_call.name
    args = dict(function_call.args) if function_call.args else {}
    func_map = {f.__name__: f for f in AGENT_TOOLS}
    fn = func_map.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    return fn(**args)


def _ensure_contents_list(contents):
    from google.genai import types
    if isinstance(contents, str):
        return [types.Content(role="user", parts=[types.Part(text=contents)])]
    if isinstance(contents, types.Content):
        return [contents]
    if isinstance(contents, list):
        return list(contents)
    return [contents]


def build_config(state: dict):
    """Build a GenerateContentConfig from the current session state. Agent mode is always on."""
    from google.genai import types

    config = types.GenerateContentConfig(
        max_output_tokens=state["max_tokens"],
        temperature=state["temperature"],
    )

    if state.get("show_thinking") is not False:
        try:
            config.thinking_config = types.ThinkingConfig(include_thoughts=True)
        except (AttributeError, TypeError):
            pass  # SDK version does not support ThinkingConfig

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
    system_parts = [tool_hint]

    try:
        config.tools = [
            types.Tool(google_search=types.GoogleSearch()),
            *AGENT_TOOLS,
        ]
        config.tool_config = types.ToolConfig(
            include_server_side_tool_invocations=True,
        )
    except (AttributeError, TypeError):
        config.tools = AGENT_TOOLS

    if state.get("system"):
        system_parts.append(state["system"])

    config.system_instruction = "\n\n".join(system_parts)
    return config


def stream_agent(client, model, contents, config, streamer, is_tty, raw=False):
    """
    Run the tool-enabled agent loop, streaming in real time.

    Each turn is streamed; if the model emits function_call parts, the tools
    are executed and the conversation continues. Thought parts and response
    text are routed through the ThinkStreamer when one is provided.

    Returns: (elapsed, prompt_tokens, response_tokens, tool_calls, final_text, updated_contents)
    """
    from google.genai import types

    tool_calls_made = []
    t0 = time.time()
    total_pt = 0
    total_rt = 0
    contents = _ensure_contents_list(contents)
    turn_text = ""

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
                    continue
                text = getattr(part, "text", None)
                if not text:
                    continue
                is_thought = getattr(part, "thought", False)
                if is_thought:
                    if streamer:
                        streamer.feed_thought(text)
                else:
                    if streamer:
                        streamer.feed_response(text)
                    elif not raw:
                        sys.stdout.write(text)
                        sys.stdout.flush()
                    turn_text += text

        if last and getattr(last, "usage_metadata", None):
            total_pt = getattr(last.usage_metadata, "prompt_token_count", 0) or 0
            total_rt += getattr(last.usage_metadata, "candidates_token_count", 0) or 0

        if not turn_fcs:
            if streamer:
                streamer.flush()
            break

        # Record the model's turn (text + function calls) in history
        model_parts = []
        if turn_text:
            model_parts.append(types.Part(text=turn_text))
        for fc in turn_fcs:
            model_parts.append(types.Part(function_call=fc))
        contents.append(types.Content(role="model", parts=model_parts))

        # Execute tools and build the function-response parts for the next turn
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

    # Append the final model answer to history
    if turn_text:
        contents.append(types.Content(
            role="model", parts=[types.Part(text=turn_text)],
        ))

    elapsed = time.time() - t0

    if raw:
        turn_text = strip_think_tags(turn_text)
        sys.stdout.write(turn_text)
        sys.stdout.flush()

    return elapsed, total_pt, total_rt, tool_calls_made, turn_text, contents
