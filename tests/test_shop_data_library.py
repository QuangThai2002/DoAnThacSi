from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.shop_data_library import DEMO_ROWS, ShopDataLibrary, clean_and_validate_rows
from agent.shop_data_tool import ShopDataValidationError


class ShopDataLibraryTest(unittest.TestCase):
    def test_demo_data_is_valid_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            library = ShopDataLibrary(Path(directory) / "library.sqlite")
            saved = library.seed_demo()
            self.assertEqual(len(saved["orders.csv"]), 4)
            self.assertEqual(library.load("demo"), saved)

    def test_blank_editor_rows_are_ignored(self) -> None:
        rows = {name: list(values) for name, values in DEMO_ROWS.items()}
        rows["products.csv"].append({key: "" for key in DEMO_ROWS["products.csv"][0]})
        validated = clean_and_validate_rows(rows)
        self.assertEqual(len(validated["products.csv"]), 3)

    def test_required_tables_are_enforced(self) -> None:
        with self.assertRaises(ShopDataValidationError):
            clean_and_validate_rows({"orders.csv": DEMO_ROWS["orders.csv"]})
