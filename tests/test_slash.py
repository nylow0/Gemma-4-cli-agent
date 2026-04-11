import unittest

from gemma.slash import format_slash_menu, match_slash_commands, visible_slash_commands


class SlashUiTest(unittest.TestCase):
    def test_match_slash_commands_prioritizes_prefixes(self):
        matches = match_slash_commands("/fi")
        self.assertEqual([spec.name for spec in matches], ["/file", "/files"])

    def test_format_slash_menu_renders_vertical_list(self):
        matches = match_slash_commands("/")
        menu = format_slash_menu("/", matches, 0)

        self.assertIn("/clear  Clear conversation history and start fresh", menu)
        self.assertIn("/help  Show available slash commands", menu)
        self.assertNotIn("Up/Down", menu)
        self.assertNotIn("Enter", menu)
        self.assertEqual(len(menu.splitlines()), 9)

    def test_format_slash_menu_hides_after_command_selection(self):
        matches = match_slash_commands("/file")
        menu = format_slash_menu("/file ", matches, 0)
        self.assertEqual(menu, "")

    def test_visible_slash_commands_scrolls_after_five_rows(self):
        matches = match_slash_commands("/")
        visible, local_index = visible_slash_commands(matches, 6, max_rows=5)

        self.assertEqual([spec.name for spec in visible], ["/file", "/files", "/help", "/quit", "/system"])
        self.assertEqual(local_index, 4)


if __name__ == "__main__":
    unittest.main()
