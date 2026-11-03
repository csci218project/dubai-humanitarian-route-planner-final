# Team folders

Each member works in their own folder, so nobody overwrites anyone else's work
and the commit history shows who did what (the marking guide uses it as
evidence of individual contribution).

| Folder | Owner | Work | Report sections |
|---|---|---|---|
| `team/shahir_network/` | Shahir | Bigger documented network, CSV-to-JSON builder, disruption scenarios, mentor log, coordination | Executive summary, motivation, requirements, appendices, final edit |
| `team/koushik_search/` | Koushik | BFS, Greedy best-first and Weighted A* baselines, with instrumentation | Algorithm design and complexity |
| `team/mohammed_heuristics/` | Mohammed | Heuristic checks, alternative heuristics, risk as probability, sensitivity | Heuristic justification, trade-offs, limitations |
| `team/shreya_experiments/` | Shreya | Synthetic networks, scaling and Monte Carlo experiments, plots | Experiments and results |
| `ui/`, `app.py` | Arwin | Front end (done) | Implementation, screenshots, demo script |

Each folder has its own README with tasks, a starter file with empty functions
to fill in, and tests that describe what the code must do. The tests are skipped
until you remove the `@unittest.skip` line above each one.

## One-time setup

You need to be a member of the `csci218project` GitHub organisation first.

```
git clone https://github.com/csci218project/dubai-humanitarian-route-planner-final.git
cd dubai-humanitarian-route-planner-final
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Every work session

1. Get everyone's latest work, then switch to your branch:
   ```
   git checkout main
   git pull
   git checkout -b koushik/search      (first time; afterwards: git checkout koushik/search, then git merge main)
   ```
   Use your own name and topic in the branch name.
2. Work inside your own folder.
3. Run the tests:
   ```
   python -m unittest discover -s tests
   python -m unittest discover -s team -t .
   ```
4. Commit small steps with clear messages, then push:
   ```
   git add team\koushik_search
   git commit -m "Add breadth-first search baseline"
   git push -u origin koushik/search    (afterwards just: git push)
   ```
5. On GitHub, open a pull request from your branch into `main`, ask one teammate to review it, then merge.

## Rules

- Change only your own folder. Shared files need a word with their owner first:
  search code in `humanitarian_route_planner/algorithms.py` (Koushik), data and
  `network.py` (Shahir), `ui/` and `app.py` (Arwin).
- Commit often, in your own name. Don't commit work for someone else.
- Never commit `.venv`, passwords or personal data.
- When your part is ready, tell Arwin so it can appear in the app.
- Everyone should be able to explain every part in the viva, so review each other's pull requests.

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
