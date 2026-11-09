"""Stable level slots and saved puzzles, independent of any screen."""
from dataclasses import dataclass
import json
from pathlib import Path

from solver import Given, Puzzle

DATA_DIRECTORY = Path(__file__).with_name('data')


@dataclass(frozen=True)
class Level:
    id: str
    title: str
    dimensions: tuple
    unlock_percent: int
    slots: tuple

    @property
    def puzzle_ids(self):
        return tuple(puzzle_id for puzzle_id in self.slots if puzzle_id is not None)

    @property
    def dimension_label(self):
        return ' · '.join(f'{rows}×{cols}' for rows, cols in self.dimensions) or 'Grid sizes to come'


class PuzzleCatalog:
    def __init__(self, directory=DATA_DIRECTORY):
        directory = Path(directory)
        level_data = json.loads((directory / 'levels.json').read_text())
        puzzle_data = json.loads((directory / 'puzzles.json').read_text())
        if level_data['version'] != 1 or puzzle_data['version'] != 1:
            raise ValueError('Unsupported puzzle catalog version')
        self.levels = tuple(Level(
            entry['id'], entry['title'], tuple(tuple(size) for size in entry['dimensions']),
            entry['unlock_percent'], tuple(entry['slots'])) for entry in level_data['levels'])
        self._puzzles = {}
        for entry in puzzle_data['puzzles']:
            if entry['id'] in self._puzzles:
                raise ValueError('Duplicate puzzle ID')
            self._puzzles[entry['id']] = entry
        seen = set()
        level_ids = set()
        for level in self.levels:
            if level.id in level_ids or len(level.slots) != 30 or not 1 <= level.unlock_percent <= 100:
                raise ValueError('Invalid level definition')
            level_ids.add(level.id)
            for puzzle_id in level.puzzle_ids:
                if puzzle_id in seen or puzzle_id not in self._puzzles:
                    raise ValueError('Duplicate or missing level puzzle')
                seen.add(puzzle_id)
                puzzle, solution = self.load_puzzle(puzzle_id)
                if (puzzle.rows, puzzle.cols) not in level.dimensions:
                    raise ValueError('Puzzle dimensions do not match its level')
        if seen != set(self._puzzles):
            raise ValueError('Unallocated puzzles in catalog')

    def load_puzzle(self, puzzle_id):
        entry = self._puzzles[puzzle_id]
        puzzle = Puzzle(
            rows=entry['grid']['rows'], cols=entry['grid']['cols'],
            palette=entry['allowed']['colors'], numbers=entry['allowed']['numbers'],
            row_sums=entry['constraints']['row_sums'], col_sums=entry['constraints']['col_sums'],
            givens=[Given(**given) for given in entry['givens']])
        cells = entry['solution']
        solution = {(cell['r'], cell['c']): (cell['num'], cell['col']) for cell in cells}
        expected = {(r, c) for r in range(puzzle.rows) for c in range(puzzle.cols)}
        if set(solution) != expected or len(cells) != len(expected):
            raise ValueError('Incomplete or duplicate solution cells')
        if len(puzzle.row_sums) != puzzle.rows or len(puzzle.col_sums) != puzzle.cols:
            raise ValueError('Invalid sum dimensions')
        for number, color in solution.values():
            if number not in puzzle.numbers or color not in puzzle.palette:
                raise ValueError('Invalid solution value')
        for given in puzzle.givens:
            number, color = solution[(given.r, given.c)]
            if (given.num is not None and given.num != number) or (given.col is not None and given.col != color):
                raise ValueError('Given does not match solution')
        return puzzle, solution
