# Network data and coordination (Shahir)

Your part: a bigger, better-documented network for the planner, its disruption
scenarios, and keeping the team (and the mentor log) organised.

## Already in the repo

`data/sample_network.json` (10 synthetic hubs) and
`humanitarian_route_planner/scenarios.py` (preset closures). `RouteNetwork` in
`network.py` loads and validates network data.

## Your tasks

Must do:
- [ ] Build a larger network (about 25–40 hubs) in `hubs_template.csv` and `links_template.csv` (they open in Excel). Use real coordinates from public sources (OurAirports for airports, the World Port Index for ports) and label times, costs and risk scores clearly as assumptions.
- [ ] Write an assumptions table: typical speed and cost per km for each transport mode, with sources.
- [ ] `build_network.py`: read the two CSVs, check them with `RouteNetwork`, and write `data/extended_network.json` in the same format as the sample.
- [ ] Add 3–5 named disruption scenarios for the new network, each with a one-line reason.
- [ ] Keep `meeting_log.md` up to date if the team goes for the industry bonus, including attempts to contact the mentor.
- [ ] Keep the table in `team/README.md` current, and raise any contribution problems with the lab instructor by Week 6.

## Files

- `hubs_template.csv`, `links_template.csv`: the network as two spreadsheets (two example hubs and one link to start from).
- `build_network.py`: CSV to JSON builder (empty for now).
- `meeting_log.md`: mentor meeting log template (Appendix B).
- `test_build_network.py`: tests describing what the builder must do.

## How it plugs in

When `data/extended_network.json` is ready, tell Arwin so the app can offer it,
and give it to Shreya as a "realistic" network for her experiments.

## Report sections you own

Executive summary, motivation, technical requirements, the appendices (Git link
and contribution table, meeting log) and the final edit.

## Viva questions to prepare

- Where does each number in the network come from, and which are assumptions?
- Why are links modelled as two-way, and when would that be wrong?
- How did feedback (from the mentor or the instructor) change the project?
