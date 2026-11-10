"""Проверки версий Cargo и выбора версий в транзитивном графе."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from versions import VersionError, matches_requirement, version_key


class VersionTests(unittest.TestCase):
    """Проверить границы требований и порядок SemVer."""

    def test_ranges(self):
        """Проверить caret, tilde, wildcard и компараторы Cargo."""
        cases = [
            ("1.9.0", "1.2.3", True), ("2.0.0", "^1.2.3", False),
            ("0.2.9", "^0.2.3", True), ("0.3.0", "^0.2.3", False),
            ("0.0.4", "^0.0.3", False), ("0.0.3", "^0.0.3", True),
            ("0.0.9", "0.0", True), ("0.1.0", "0.0", False),
            ("0.9.0", "0", True), ("1.0.0", "0", False),
            ("1.2.9", "~1.2.3", True), ("1.3.0", "~1.2", False),
            ("1.9.0", "~1", True), ("2.0.0", "~1", False),
            ("1.2.9", "1.2.*", True), ("1.3.0", "1.2.*", False),
            ("1.9.0", "1.*", True), ("2.0.0", "1.x", False),
            ("9.0.0", "*", True), ("1.0.0-beta", "*", False),
            ("1.3.0", ">=1.2, <1.5", True),
            ("1.5.0", ">=1.2, <1.5", False),
            ("1.9.0", ">1", False), ("2.0.0", ">1", True),
            ("1.2.9", "=1.2", True), ("1.3.0", "=1.2", False),
            ("1.2.3+abc", "=1.2.3", True),
            ("1.2.3-beta", "^1.2.3-alpha", True),
            ("1.2.4-beta", "^1.2.3-alpha", False),
            ("1.3.0", "^1.2.3-alpha", True),
        ]
        for version, requirement, expected in cases:
            with self.subTest(version=version, requirement=requirement):
                self.assertEqual(
                    matches_requirement(version, requirement), expected)

    def test_order(self):
        """Числовые компоненты и prerelease сравниваются по SemVer."""
        values = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
                  "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11",
                  "1.0.0-rc.1", "1.0.0", "1.2.0", "1.10.0"]
        self.assertEqual(sorted(reversed(values), key=version_key), values)

    def test_invalid_requirement(self):
        """Не подменять неподдерживаемое требование произвольной версией."""
        for value in ("", "^", "bad", "1.*.2", "1 || 2", "1,", "01.2"):
            with self.subTest(value=value):
                with self.assertRaises(VersionError):
                    matches_requirement("1.2.3", value)


if __name__ == "__main__":
    unittest.main()
