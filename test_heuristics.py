"""Tests for Mohammed's heuristics. Remove each skip once that function works."""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork
from heuristics import (
    check_admissible, check_consistent, survival_weight, time_lower_bound_heuristic, zero_heuristic,
)

ROOT = Path(__file__).resolve().parent
NETWORK = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
GOAL = "RELIEF_DESTINATION"
WEIGHTS = CostWeights()


class AdmissibilityTests(unittest.TestCase):
    @unittest.skip("TODO (Mohammed): remove once check_admissible works")
    def test_zero_heuristic_is_admissible(self):
        self.assertEqual(check_admissible(NETWORK, GOAL, WEIGHTS, zero_heuristic), [])

    @unittest.skip("TODO (Mohammed): remove once check_admissible works")
    def test_checker_catches_an_overestimate(self):
        def too_big(node_id: str) -> float:
            return 0.0 if node_id == GOAL else 1e9

        self.assertTrue(check_admissible(NETWORK, GOAL, WEIGHTS, too_big))

    @unittest.skip("TODO (Mohammed): remove once time_lower_bound_heuristic and both checks work")
    def test_time_bound_is_admissible_and_consistent(self):
        h = time_lower_bound_heuristic(NETWORK, GOAL, WEIGHTS)
        self.assertEqual(check_admissible(NETWORK, GOAL, WEIGHTS, h), [])
        self.assertEqual(check_consistent(NETWORK, WEIGHTS, h), [])


class SurvivalWeightTests(unittest.TestCase):
    @unittest.skip("TODO (Mohammed): remove once survival_weight works")
    def test_weight_grows_with_risk_and_stays_finite(self):
        self.assertEqual(survival_weight(0.0), 0.0)
        self.assertLess(survival_weight(2.0), survival_weight(8.0))
        self.assertTrue(math.isfinite(survival_weight(10.0)))


if __name__ == "__main__":
    unittest.main()
