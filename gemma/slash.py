"""Slash commands and inline prompt session helpers."""

import glob
import importlib
import os
from dataclasses import dataclass

from .ui import bold, cyan, dim, gray, green, red, reset, yellow


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

SLASH_COMMAND_INDEX = {spec.name: spec for spec in SLASH_COMMAND_SPECS}
MAX_VISIBLE_SLASH_ROWS = 9

SLASH_HELP_TEXT = """\
 {h}Available commands:{r}

  {c}/help{r}              Show this message
  {c}/clear{r}             Clear conversation history
  {c}/system{r} [text]     Show or set system instruction
  {c}/file{r} <path>       Attach a file to the next message
  {c}/files{r}             Show currently attached files
  {c}/think{r}             Toggle thinking display
  {c}/temp{r} <value>      Set temperature (0.0-2.0)
  {c}/exit{r}              Exit interactive mode
"""


def match_slash_commands(text: str):
    """Return ranked slash-command matches for the current buffer text."""
    if not text.startswith("/") or " " in text:
        return []

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

    return [spec for _, _, spec in sorted(matches, key=lambda item: item[:2])]


def slash_command_for_text(text: str):
    """Return the slash command spec for the current command token."""
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    command = stripped.split(None, 1)[0].lower()
    return SLASH_COMMAND_INDEX.get(command)


def visible_slash_commands(matches, selected_index: int, max_rows: int = MAX_VISIBLE_SLASH_ROWS):
    """Return the visible slice of matches for the current scroll position."""
    if not matches:
        return [], 0

    selected_index %= len(matches)
    if len(matches) <= max_rows:
        start = 0
    else:
        start = min(max(selected_index - max_rows + 1, 0), len(matches) - max_rows)

    visible = list(matches[start:start + max_rows])
    return visible, selected_index - start


def format_slash_menu(text: str, matches, selected_index: int, max_rows: int = MAX_VISIBLE_SLASH_ROWS) -> str:
    """Render the slash-command list shown directly under the input line."""
    if not text.startswith("/") or " " in text or not matches:
        return ""

    visible, _ = visible_slash_commands(matches, selected_index, max_rows=max_rows)
    lines = []
    for spec in visible:
        lines.append(f"{spec.name}  {spec.description}")
    return "\n".join(lines)


def create_prompt_session(input_obj=None, output_obj=None):
    """Build a prompt-toolkit session with slash suggestions below the input line."""
    try:
        prompt_module = importlib.import_module("prompt_toolkit.shortcuts.prompt")
        filters_module = importlib.import_module("prompt_toolkit.filters")
        formatted_text_module = importlib.import_module("prompt_toolkit.formatted_text")
        key_binding_module = importlib.import_module("prompt_toolkit.key_binding")
        layout_module = importlib.import_module("prompt_toolkit.layout")
        containers_module = importlib.import_module("prompt_toolkit.layout.containers")
        controls_module = importlib.import_module("prompt_toolkit.layout.controls")
        dimension_module = importlib.import_module("prompt_toolkit.layout.dimension")
        layout_layout_module = importlib.import_module("prompt_toolkit.layout.layout")
        processors_module = importlib.import_module("prompt_toolkit.layout.processors")
        lexers_module = importlib.import_module("prompt_toolkit.lexers")
        styles_module = importlib.import_module("prompt_toolkit.styles")
        widgets_module = importlib.import_module("prompt_toolkit.widgets")
        toolbars_module = importlib.import_module("prompt_toolkit.widgets.toolbars")
        utils_module = importlib.import_module("prompt_toolkit.utils")
        app_current_module = importlib.import_module("prompt_toolkit.application.current")
    except ImportError as exc:
        raise RuntimeError(
            "prompt-toolkit is required for interactive mode. "
            "Install it with `python -m pip install -e .`."
        ) from exc

    PromptSession = getattr(prompt_module, "PromptSession")
    split_multiline_prompt = getattr(prompt_module, "_split_multiline_prompt")
    RPrompt = getattr(prompt_module, "_RPrompt")
    ANSI = getattr(formatted_text_module, "ANSI")
    fragment_list_to_text = getattr(formatted_text_module, "fragment_list_to_text")
    Style = getattr(styles_module, "Style")
    KeyBindings = getattr(key_binding_module, "KeyBindings")
    Condition = getattr(filters_module, "Condition")
    has_arg = getattr(filters_module, "has_arg")
    has_focus = getattr(filters_module, "has_focus")
    is_done = getattr(filters_module, "is_done")
    renderer_height_is_known = getattr(filters_module, "renderer_height_is_known")
    get_app = getattr(app_current_module, "get_app")
    Float = getattr(layout_module, "Float")
    FloatContainer = getattr(layout_module, "FloatContainer")
    HSplit = getattr(layout_module, "HSplit")
    ConditionalContainer = getattr(containers_module, "ConditionalContainer")
    Window = getattr(containers_module, "Window")
    BufferControl = getattr(controls_module, "BufferControl")
    FormattedTextControl = getattr(controls_module, "FormattedTextControl")
    SearchBufferControl = getattr(controls_module, "SearchBufferControl")
    Dimension = getattr(dimension_module, "Dimension")
    Layout = getattr(layout_layout_module, "Layout")
    AfterInput = getattr(processors_module, "AfterInput")
    AppendAutoSuggestion = getattr(processors_module, "AppendAutoSuggestion")
    ConditionalProcessor = getattr(processors_module, "ConditionalProcessor")
    DisplayMultipleCursors = getattr(processors_module, "DisplayMultipleCursors")
    DynamicProcessor = getattr(processors_module, "DynamicProcessor")
    HighlightIncrementalSearchProcessor = getattr(processors_module, "HighlightIncrementalSearchProcessor")
    HighlightSelectionProcessor = getattr(processors_module, "HighlightSelectionProcessor")
    PasswordProcessor = getattr(processors_module, "PasswordProcessor")
    ReverseSearchProcessor = getattr(processors_module, "ReverseSearchProcessor")
    merge_processors = getattr(processors_module, "merge_processors")
    DynamicLexer = getattr(lexers_module, "DynamicLexer")
    Frame = getattr(widgets_module, "Frame")
    SearchToolbar = getattr(toolbars_module, "SearchToolbar")
    SystemToolbar = getattr(toolbars_module, "SystemToolbar")
    ValidationToolbar = getattr(toolbars_module, "ValidationToolbar")
    get_cwidth = getattr(utils_module, "get_cwidth")

    menu_state = {
        "query": None,
        "selected_index": 0,
        "dismissed": False,
        "matches": [],
    }

    def refresh_menu_state(buffer):
        text = buffer.document.text_before_cursor
        query = text if text.startswith("/") and " " not in text else None

        if query != menu_state["query"]:
            menu_state["query"] = query
            menu_state["selected_index"] = 0
            menu_state["dismissed"] = False

        if not query or menu_state["dismissed"]:
            menu_state["matches"] = []
            return text, []

        matches = match_slash_commands(text)
        menu_state["matches"] = matches
        if matches:
            menu_state["selected_index"] %= len(matches)
        else:
            menu_state["selected_index"] = 0
        return text, matches

    def selected_match(buffer):
        _, matches = refresh_menu_state(buffer)
        if not matches:
            return slash_command_for_text(buffer.document.text_before_cursor)
        return matches[menu_state["selected_index"]]

    def apply_match(buffer, spec):
        new_text = spec.name + (" " if spec.arg_hint else "")
        buffer.text = new_text
        buffer.cursor_position = len(new_text)

    @Condition
    def slash_menu_active():
        buffer = get_app().current_buffer
        text, matches = refresh_menu_state(buffer)
        return text.startswith("/") and " " not in text and bool(matches)

    def slash_menu_fragments():
        buffer = get_app().current_buffer
        text, matches = refresh_menu_state(buffer)
        if not text.startswith("/") or " " in text or not matches:
            return []

        visible, local_index = visible_slash_commands(matches, menu_state["selected_index"])
        fragments = []
        for idx, spec in enumerate(visible):
            command_style = "class:slash-menu.selected" if idx == local_index else "class:slash-menu.item"
            desc_style = "class:slash-menu.desc-selected" if idx == local_index else "class:slash-menu.desc"
            fragments.append((command_style, spec.name.ljust(10)))
            fragments.append(("", "  "))
            fragments.append((desc_style, spec.description))
            if idx != len(visible) - 1:
                fragments.append(("", "\n"))
        return fragments

    show_slash_menu = slash_menu_active & ~is_done & renderer_height_is_known

    class InlineSlashPromptSession(PromptSession):
        def _create_layout(self):
            dyncond = self._dyncond
            has_before_fragments, get_prompt_text_1, get_prompt_text_2 = split_multiline_prompt(self._get_prompt)

            default_buffer = self.default_buffer
            search_buffer = self.search_buffer

            @Condition
            def display_placeholder() -> bool:
                return self.placeholder is not None and self.default_buffer.text == ""

            all_input_processors = [
                HighlightIncrementalSearchProcessor(),
                HighlightSelectionProcessor(),
                ConditionalProcessor(
                    AppendAutoSuggestion(), has_focus(default_buffer) & ~is_done
                ),
                ConditionalProcessor(PasswordProcessor(), dyncond("is_password")),
                DisplayMultipleCursors(),
                DynamicProcessor(lambda: merge_processors(self.input_processors or [])),
                ConditionalProcessor(
                    AfterInput(lambda: self.placeholder),
                    filter=display_placeholder,
                ),
            ]

            search_toolbar = SearchToolbar(
                search_buffer, ignore_case=dyncond("search_ignore_case")
            )
            search_buffer_control = SearchBufferControl(
                buffer=search_buffer,
                input_processors=[ReverseSearchProcessor()],
                ignore_case=dyncond("search_ignore_case"),
            )

            system_toolbar = SystemToolbar(
                enable_global_bindings=dyncond("enable_system_prompt")
            )

            def get_search_buffer_control():
                if self.multiline:
                    return search_toolbar.control
                return search_buffer_control

            default_buffer_control = BufferControl(
                buffer=default_buffer,
                search_buffer_control=get_search_buffer_control,
                input_processors=all_input_processors,
                include_default_input_processors=False,
                lexer=DynamicLexer(lambda: self.lexer),
                preview_search=True,
            )

            default_buffer_window = Window(
                default_buffer_control,
                height=self._get_default_buffer_control_height,
                get_line_prefix=lambda lineno, wrap_count: self._get_line_prefix(
                    lineno,
                    wrap_count,
                    get_prompt_text_2=get_prompt_text_2,
                ),
                wrap_lines=dyncond("wrap_lines"),
            )

            def slash_menu_prefix(_lineno, _wrap_count):
                prompt_text = fragment_list_to_text(get_prompt_text_2())
                return [("", " " * get_cwidth(prompt_text))]

            slash_menu_window = ConditionalContainer(
                Window(
                    FormattedTextControl(slash_menu_fragments),
                    dont_extend_height=True,
                    height=Dimension(max=MAX_VISIBLE_SLASH_ROWS),
                    get_line_prefix=slash_menu_prefix,
                ),
                filter=show_slash_menu,
            )

            main_input_container = FloatContainer(
                HSplit(
                    [
                        ConditionalContainer(
                            Window(
                                FormattedTextControl(get_prompt_text_1),
                                dont_extend_height=True,
                            ),
                            Condition(has_before_fragments),
                        ),
                        ConditionalContainer(
                            default_buffer_window,
                            Condition(
                                lambda: get_app().layout.current_control != search_buffer_control
                            ),
                        ),
                        ConditionalContainer(
                            Window(search_buffer_control),
                            Condition(
                                lambda: get_app().layout.current_control == search_buffer_control
                            ),
                        ),
                        slash_menu_window,
                    ]
                ),
                [
                    Float(
                        right=0,
                        top=0,
                        hide_when_covering_content=True,
                        content=RPrompt(lambda: self.rprompt),
                    ),
                ],
            )

            layout = HSplit(
                [
                    ConditionalContainer(
                        Frame(main_input_container),
                        filter=dyncond("show_frame"),
                        alternative_content=main_input_container,
                    ),
                    ConditionalContainer(ValidationToolbar(), filter=~is_done),
                    ConditionalContainer(
                        system_toolbar, dyncond("enable_system_prompt") & ~is_done
                    ),
                    ConditionalContainer(
                        Window(FormattedTextControl(self._get_arg_text), height=1),
                        dyncond("multiline") & has_arg,
                    ),
                    ConditionalContainer(search_toolbar, dyncond("multiline") & ~is_done),
                ]
            )

            return Layout(layout, default_buffer_window)

    bindings = KeyBindings()

    @bindings.add("enter")
    def _(event):
        buffer = event.current_buffer
        text = buffer.document.text_before_cursor
        if text.startswith("/") and " " not in text:
            spec = selected_match(buffer)
            if spec:
                apply_match(buffer, spec)
                if not spec.arg_hint:
                    buffer.validate_and_handle()
                return
        buffer.validate_and_handle()

    @bindings.add("tab")
    def _(event):
        buffer = event.current_buffer
        text = buffer.document.text_before_cursor
        if text.startswith("/") and " " not in text:
            spec = selected_match(buffer)
            if spec:
                apply_match(buffer, spec)
                return
        buffer.insert_text("    ")

    @bindings.add("up", filter=slash_menu_active)
    def _(event):
        menu_state["selected_index"] = (menu_state["selected_index"] - 1) % len(menu_state["matches"])
        event.app.invalidate()

    @bindings.add("down", filter=slash_menu_active)
    def _(event):
        menu_state["selected_index"] = (menu_state["selected_index"] + 1) % len(menu_state["matches"])
        event.app.invalidate()

    @bindings.add("escape")
    def _(event):
        buffer = event.current_buffer
        text = buffer.document.text_before_cursor
        if text.startswith("/") and " " not in text:
            menu_state["dismissed"] = True
            menu_state["matches"] = []
            event.app.invalidate()

    session = InlineSlashPromptSession(
        key_bindings=bindings,
        style=Style.from_dict({
            "slash-menu.item": "fg:#cbd5e1",
            "slash-menu.desc": "fg:#94a3b8",
            "slash-menu.selected": "fg:#3b82f6 bold",
            "slash-menu.desc-selected": "fg:#cbd5e1",
        }),
        mouse_support=True,
        input=input_obj,
        output=output_obj,
    )
    return session, ANSI


def handle_slash(cmd_line: str, state: dict) -> bool:
    """
    Handle a slash command, mutating `state` in place.

    Returns True if the command was recognized, regardless of success.
    """
    parts = cmd_line.strip().split(None, 1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/help":
        print(SLASH_HELP_TEXT.format(h=bold(), r=reset(), c=cyan()))
        return True

    if cmd == "/clear":
        state["history"] = []
        state["pending_media_paths"] = []
        print(f" {green()}OK{reset()} Conversation cleared")
        return True

    if cmd == "/system":
        if arg:
            state["system"] = arg
            state["history"] = []
            print(f" {green()}OK{reset()} System instruction updated")
        else:
            si = state.get("system") or "(none)"
            print(f" System: {dim()}{si}{reset()}")
        return True

    if cmd == "/file":
        if not arg:
            print(f" {yellow()}Usage: /file <path>{reset()}")
            return True
        path = arg.strip("\"'")
        if os.path.isfile(path):
            state["pending_media_paths"].append(path)
            print(f" {green()}Attached{reset()}: {os.path.basename(path)}")
        else:
            matches = glob.glob(path, recursive=True)
            if matches:
                for match in matches:
                    state["pending_media_paths"].append(match)
                    print(f" {green()}Attached{reset()}: {match}")
            else:
                print(f" {red()}File not found: {path}{reset()}")
        return True

    if cmd == "/files":
        pending = state.get("pending_media_paths", [])
        if pending:
            print(" Attached files:")
            for path in pending:
                print(f"   - {path}")
        else:
            print(f" {gray()}No files attached{reset()}")
        return True

    if cmd == "/think":
        state["show_thinking"] = not state["show_thinking"]
        status = f"{green()}shown{reset()}" if state["show_thinking"] else f"{gray()}hidden{reset()}"
        print(f" {green()}OK{reset()} Thinking: {status}")
        return True

    if cmd == "/temp":
        if arg:
            try:
                val = float(arg)
                if 0.0 <= val <= 2.0:
                    state["temperature"] = val
                    print(f" {green()}OK{reset()} Temperature -> {val}")
                else:
                    print(f" {red()}Must be between 0.0 and 2.0{reset()}")
            except ValueError:
                print(f" {red()}Invalid number: {arg}{reset()}")
        else:
            print(f" Temperature: {state.get('temperature', 0.7)}")
        return True

    if cmd in ("/exit", "/quit"):
        raise SystemExit(0)

    return False
