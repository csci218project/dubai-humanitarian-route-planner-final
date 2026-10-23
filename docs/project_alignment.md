# Alignment with the supplied CSCI218 brief

## Selected use case

The supplied workbook `Dubai_Humanitarian_AI_Student_Projects.xlsx` lists Project B, “Humanitarian Route Planner,” under “Gaza Humanitarian Air Bridge Optimization.” Its problem statement asks for fastest or lowest-risk multimodal paths from Dubai to a crisis destination when airports, ports, or roads are unavailable, and names A*, Dijkstra, heuristic search, and planning. This repository implements a demonstrator of that use case using **synthetic data only**.

## Rubric-to-artifact mapping

| Requirement in the CSCI218 grading criteria | Supporting material in this repository |
|---|---|
| Problem understanding and motivation | README problem/use-case framing; dynamic closures and multimodal objective trade-offs |
| Technical depth and algorithm design | Dijkstra, A*, hierarchical search, weighted edge objective, heuristic explanation |
| Implementation quality | Separate model, network, algorithm, scenario, visualization, UI, benchmark and test modules |
| Reproducibility | JSON input, dependency list, seeded benchmark runner and explicit CLI options |
| Functional tests and edge cases | `tests/test_algorithms.py`, `tests/test_network.py` |
| Results and baseline analysis | `scripts/run_benchmarks.py`, two CSV output files, `docs/experiment_plan.md` |
| Demonstration | Streamlit interface with route comparisons, disruptions, route legs and network figure |
| Limitations and constraints | README and architecture document disclose synthetic data and missing operational constraints |
| Git contribution evidence | README recommends shared Git use; group must record genuine individual commits |
| Report structure | Architecture and experiment documentation support the required report sections |

## Suggested report sections

1. Executive summary
2. Motivation and problem statement
3. Technical requirements and assumptions
4. Main constructs: graph, objective, Dijkstra, A*, hierarchical search
5. Implementation with screenshots and selected code excerpts
6. Experiments and results: seeded trials, means/standard deviations, baseline comparison
7. Limitations, difficulties, constraints, and data caveats
8. Conclusion and discussion
9. References
10. Appendices: repository URL, team contribution table, and relevant supporting logs where applicable

This mapping is a planning aid, not a guarantee of a particular grade and not a substitute for the group's own report, screenshots, measured results, honest contribution record, or viva preparation. Follow the course's policy on AI tools and disclose assistance as required.
