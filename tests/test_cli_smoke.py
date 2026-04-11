import subprocess
import sys
import unittest


class CliSmokeTest(unittest.TestCase):
    def test_module_help_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "gemma", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: gemma", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
