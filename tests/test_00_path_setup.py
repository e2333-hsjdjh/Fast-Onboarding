"""Ensure src layout imports work when tests run without installation."""

from pathlib import Path
import sys
import unittest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class PathSetupTest(unittest.TestCase):
    def test_src_path_is_available(self):
        self.assertIn(str(SRC), sys.path)


if __name__ == "__main__":
    unittest.main()
