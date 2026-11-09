# Hui Pū

Run the player application on macOS with Tk-enabled Python:

```sh
/opt/homebrew/bin/python3.11 clusters_py/main.py
```

Home contains eight levels with thirty permanent slots each. Level 1 publishes
four 3×3, three 3×4, and three 4×3 puzzles. The other 230 slots are empty and
cannot be selected. Instructions currently shows a placeholder image.

The existing Play canvas, controls, artwork, animation, sounds, and rules are
unchanged. Its Home action returns to level selection. The developer solution
reference is disabled for catalog play. Unfinished boards are not saved.
Home stays alive but hidden during Play; the Play window shares its Tk root and
returns to the same Home window. The standalone developer workflow owns a
separate hidden root when launched without Home.

## Catalog maintenance

- `data/levels.json`: stable level IDs, accepted dimensions, 30 slots, and unlock
  percentage (initially 70%). A null slot is empty; never renumber existing IDs.
- `data/puzzles.json`: saved puzzle definitions and solutions. These solutions
  support the existing desktop correctness check; they are not secrets in a
  locally distributed game. This file is separate from the web puzzle export.
- To publish a puzzle, add its validated record, replace a null slot with its ID,
  and include its dimensions in the level. Run the tests before publishing.
- Only published puzzles count toward a percentage. Completing seven of the
  initial ten earns Level 2; an empty level stays unavailable until populated.
  Earned unlocks remain when a level later grows.
- The initial batch can be reproduced with `tools/build_starter_catalog.py`.
  It intentionally refuses to overwrite an existing catalog. To build a separate
  candidate catalog, import its `build` function and supply a new directory.

Progress is stored outside the project at
`~/Library/Application Support/Hui Pu/progress.json` on macOS, with atomic writes.
It stores completed IDs and earned unlocks, not active boards or undo history.
An unreadable progress file is left unchanged and reported rather than reset.

## Developer tools

Calibration and generation are retained for authoring, with no player-facing
route. The previous Calibration → Play workflow is available with:

```sh
cd clusters_py
/opt/homebrew/bin/python3.11 -c 'from editor import launch_app; launch_app()'
```

Test from the repository root:

```sh
/opt/homebrew/bin/python3.11 -m unittest discover -s clusters_py/tests
```
