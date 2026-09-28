from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.shop_data_library import (
    DEMO_PERIODS,
    DEMO_ROWS,
    ShopDataLibrary,
    clean_and_validate_rows,
    demo_catalog,
    random_demo_product_ids,
)
from agent.shop_data_tool import ShopDataValidationError


class ShopDataLibraryTest(unittest.TestCase):
    def test_demo_data_is_valid_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            library = ShopDataLibrary(Path(directory) / "library.sqlite")
            saved = library.seed_demo()
            self.assertEqual(len(saved["products.csv"]), 50)
            self.assertEqual(len({row["category"] for row in saved["products.csv"]}), 50)
            self.assertEqual(len(saved["orders.csv"]), 50 * 12)
            self.assertEqual(len(DEMO_PERIODS), 12)
            self.assertEqual(library.load("demo"), saved)

    def test_demo_catalog_can_build_a_random_small_assortment(self) -> None:
        selection = random_demo_product_ids(5)
        self.assertEqual(len(selection), 5)
        self.assertEqual(len({item["id"] for item in demo_catalog()}), 50)
        with tempfile.TemporaryDirectory() as directory:
            saved = ShopDataLibrary(Path(directory) / "library.sqlite").seed_demo(selection)
        self.assertEqual(len(saved["products.csv"]), 5)
        self.assertEqual(len(saved["orders.csv"]), 5 * 12)

    def test_blank_editor_rows_are_ignored(self) -> None:
        rows = {name: list(values) for name, values in DEMO_ROWS.items()}
        rows["products.csv"].append({key: "" for key in DEMO_ROWS["products.csv"][0]})
        validated = clean_and_validate_rows(rows)
        self.assertEqual(len(validated["products.csv"]), 50)

    def test_required_tables_are_enforced(self) -> None:
        with self.assertRaises(ShopDataValidationError):
            clean_and_validate_rows({"orders.csv": DEMO_ROWS["orders.csv"]})
