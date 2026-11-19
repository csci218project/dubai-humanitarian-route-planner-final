# Mentor meeting log (Appendix B)

Needed for the industry engagement bonus: at least two logged meetings,
requirements traced back to them, and evidence that feedback changed the
design. Log every attempt to reach the mentor as well; the guidelines say you
won't lose marks for an unavailable mentor if your attempts are documented.

## Meetings

| # | Date | Attendees | Agenda | Decisions | Actions (owner, due) |
|---|---|---|---|---|---|
| 1 | [date] | [names] | [agenda] | [decisions] | [actions] |
| 2 | [date] | [names] | [agenda] | [decisions] | [actions] |

## Contact attempts

| Date | Channel | Who | Outcome |
|---|---|---|---|
| [date] | Email, via the subject coordinator | Muhaimeen Shahir | Dubai Humanitarian sent five points of feedback on the proposal (traced below) |
| [date] | [channel] | Muhaimeen Shahir | Asked Dubai Humanitarian for network data; [their reply] |
| [date] | [channel] | [who] | Dubai Humanitarian provided `hrp_network_data.xlsx`: 23 locations, 36 one-way legs and 10 disruption scenarios |

## Requirements traced to feedback

| Requirement | From | Where it is in the project |
|---|---|---|
| Combine fastest and lowest-risk as a weighted cost the user can adjust | Proposal feedback, point 1 | `CostWeights` in `humanitarian_route_planner/models.py`; the Time, Cost and Risk sliders and presets in the app |
| Include transfer time and cost where cargo changes mode | Proposal feedback, point 2 | Transfer legs in the data; `TransferRule` in `models.py` and `network.py`; "+ transfer" on the app's journey strip |
| Implement Dijkstra and A* ourselves and count nodes explored; NetworkX only for storage and drawing | Proposal feedback, point 3 | `humanitarian_route_planner/algorithms.py` (`nodes_expanded`); the Compare algorithms tab; NetworkX is not used |
| Explain the A* heuristic and why it never overestimates | Proposal feedback, point 4 | `_heuristic_scale` in `algorithms.py`; `docs/architecture.md`; heuristic tests in `tests/test_hrp_network.py` |
| Show live re-planning when an airport, port or road closes, with a before/after comparison | Proposal feedback, point 5 | Scenarios and clickable closures in the app; the before/after table and the faded normal route |
| Use the partner's network data | Data handover | `data/hrp_network_data.xlsx`, converted by `scripts/import_hrp_data.py` |

## Changes made because of feedback

| Feedback | Change | Commit or file |
|---|---|---|
| Before/after comparison (point 5) | The route under normal conditions is drawn faded on the chart, with a comparison table | 1351a9b |
| Transfer time and cost (point 2) | A transfer rule at mode changes, taken from the data's own transfer legs | d92e7c3 |
| Partner data | The app runs on the 23-hub network: one-way legs, the data's scenarios, cost per tonne, slow-case time and reliability | d92e7c3 |
