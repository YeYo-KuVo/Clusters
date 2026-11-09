"""Developer-only: build and validate the initial ten fixed puzzles.

Run: python3.11 clusters_py/tools/build_starter_catalog.py
Never runs during player startup. Existing catalog files are not overwritten.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from constructor import ConstructConfig, construct_solution
from deconstructor import DeconstructConfig, DeconstructorStepper
from solver import ClustersSolver, count_solutions


def build(directory):
    directory = Path(directory)
    if any((directory / name).exists() for name in ('levels.json', 'puzzles.json')):
        raise FileExistsError('Catalog already exists; use a new directory to preserve permanent puzzle IDs.')
    puzzles = []
    signatures = set()
    sizes = [(3, 3)]*4 + [(3, 4)]*3 + [(4, 3)]*3
    for index, (rows, cols) in enumerate(sizes, 1):
        seed = 11000 + index
        solution, base = construct_solution(ConstructConfig(
            rows=rows, cols=cols, numbers=[1, 2, 3], palette=['B', 'Y', 'V'], seed=seed))
        puzzle = DeconstructorStepper(base, solution, DeconstructConfig(
            seed=seed+100, difficulty='EASY', generation_timeout_seconds=5)).run_to_target()
        assert count_solutions(puzzle, timeout_seconds=10) == 1
        checker = ClustersSolver(puzzle)
        for coordinate, value in solution.items():
            checker.assign_val(coordinate, value)
        assert checker.complete_blocks_ok() and checker.sums_exact_ok()
        signature = (rows, cols, tuple(solution[r, c] for r in range(rows) for c in range(cols)))
        assert signature not in signatures, 'Duplicate solution; choose another seed'
        signatures.add(signature)
        puzzles.append({
            'id': f'level-01-puzzle-{index:02d}', 'seed': seed, 'bias': 'BALANCED', 'difficulty': 'EASY',
            'grid': {'rows': rows, 'cols': cols},
            'allowed': {'numbers': puzzle.numbers, 'colors': puzzle.palette},
            'constraints': {'row_sums': puzzle.row_sums, 'col_sums': puzzle.col_sums},
            'givens': [vars(given) for given in puzzle.givens],
            'solution': [{'r': r, 'c': c, 'num': solution[r, c][0], 'col': solution[r, c][1]}
                         for r in range(rows) for c in range(cols)]})
        print(f'Validated {index}/10: {rows}×{cols}', flush=True)
    levels = []
    for index in range(1, 9):
        slots = [puzzle['id'] for puzzle in puzzles] + [None]*20 if index == 1 else [None]*30
        levels.append({'id': f'level-{index:02d}', 'title': f'Level {index}',
                       'dimensions': [[3, 3], [3, 4], [4, 3]] if index == 1 else [],
                       'unlock_percent': 70, 'slots': slots})
    directory.mkdir(parents=True, exist_ok=True)
    for name, key, entries in [('levels.json', 'levels', levels), ('puzzles.json', 'puzzles', puzzles)]:
        (directory/name).write_text(json.dumps({'version': 1, key: entries}, indent=2)+'\n')


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1] / 'data')
