"""Tests for the spreadsheet checks in scripts/validate_data.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "hrp_network_data.xlsx"


@unittest.skipIf(importlib.util.find_spec("openpyxl") is None,
                 "openpyxl not installed (pip install -r requirements-dev.txt)")
class ValidateDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pandas as pd
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import validate_data
        finally:
            sys.path.pop(0)
        cls.validate = validate_data
        cls.sheets = pd.read_excel(SOURCE, sheet_name=None)

    def edited(self) -> dict:
        """A fresh copy of the three sheets to break on purpose."""
        return {name: sheet.copy() for name, sheet in self.sheets.items()}

    def failures(self, sheets: dict) -> dict[str, list[str]]:
        return {name: problems for name, problems in self.validate.run_checks(sheets) if problems}

    def test_the_real_data_passes_every_check(self):
        self.assertEqual(self.failures(self.sheets), {})

    def test_the_command_line_reports_success(self):
        self.assertEqual(self.validate.main(["--file", str(SOURCE)]), 0)

    def test_a_leg_to_an_unknown_location_is_caught(self):
        sheets = self.edited()
        sheets["network_legs"].loc[0, "to_node"] = "NOWHERE"
        self.assertIn("Every leg starts and ends at a known location", self.failures(sheets))

    def test_a_slow_case_below_the_typical_time_is_caught(self):
        sheets = self.edited()
        legs = sheets["network_legs"]
        legs.loc[0, "transit_hours_p90"] = legs.loc[0, "transit_hours_typical"] - 1
        self.assertIn("Times, costs, capacities, risk and reliability are in range", self.failures(sheets))

    def test_a_duplicate_leg_id_is_caught(self):
        sheets = self.edited()
        sheets["network_legs"].loc[1, "leg_id"] = sheets["network_legs"].loc[0, "leg_id"]
        self.assertIn("Leg IDs are unique", self.failures(sheets))

    def test_a_scenario_naming_an_unknown_leg_is_caught(self):
        sheets = self.edited()
        scenarios = sheets["disruption_scenarios"]
        row = scenarios.index[scenarios.action == "CLOSE"][0]
        scenarios.loc[row, "leg_id"] = "L99"
        self.assertIn("Scenarios only name known legs", self.failures(sheets))

    def test_a_location_cut_off_from_the_origin_is_caught(self):
        sheets = self.edited()
        legs = sheets["network_legs"]
        sheets["network_legs"] = legs[legs.to_node != "ELO"].reset_index(drop=True)
        failed = self.failures(sheets)
        self.assertIn("Every location can be reached from the origin", failed)
        self.assertIn("legs_out and legs_in match the legs sheet", failed)


if __name__ == "__main__":
    unittest.main()
