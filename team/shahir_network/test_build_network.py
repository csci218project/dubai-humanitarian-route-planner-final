"""Tests for Shahir's network builder. Remove each skip once that part works."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from humanitarian_route_planner.network import RouteNetwork
from team.shahir_network.build_network import build_network, write_network_json

HERE = Path(__file__).resolve().parent


class BuilderTests(unittest.TestCase):
    @unittest.skip("TODO (Shahir): remove once build_network works")
    def test_templates_build_a_valid_network(self):
        network = build_network(HERE / "hubs_template.csv", HERE / "links_template.csv")
        self.assertIn("DUBAI_HUB", network.nodes)
        self.assertIn("E01_DUBAI_DWC", network.edges)

    @unittest.skip("TODO (Shahir): remove once write_network_json works")
    def test_written_file_loads_like_the_sample(self):
        network = build_network(HERE / "hubs_template.csv", HERE / "links_template.csv")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "network.json"
            write_network_json(network, path, {"title": "Test", "disclaimer": "Illustrative values."})
            reloaded = RouteNetwork.from_json(path)
        self.assertEqual(sorted(reloaded.nodes), sorted(network.nodes))


if __name__ == "__main__":
    unittest.main()
