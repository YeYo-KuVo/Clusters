import sys
import unittest
from pathlib import Path
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constructor import ConstructConfig, construct_solution
from deconstructor import DeconstructConfig, DeconstructorStepper
from solver import Puzzle, SearchBudgetExceeded, count_solutions, ClustersSolver


class GenerationTests(unittest.TestCase):
    def test_cluster_sizes_are_mixed_and_seeded(self):
        top_left_sizes = set()
        for seed in range(10):
            cfg = ConstructConfig(rows=7, cols=5, numbers=[1, 2, 3, 4, 5],
                                  palette=['B', 'R', 'Y', 'V'], seed=seed)
            solution, puzzle = construct_solution(cfg)
            repeated_solution, _ = construct_solution(cfg)
            self.assertEqual(solution, repeated_solution)
            self.assertEqual(len(solution), 35)
            top_left_sizes.add(solution[0, 0][0])
            checker = ClustersSolver(puzzle)
            for coordinate, value in solution.items():
                checker.assign_val(coordinate, value)
            self.assertTrue(checker.complete_blocks_ok())
            self.assertTrue(checker.sums_exact_ok())
        self.assertIn(1, top_left_sizes)
        self.assertIn(5, top_left_sizes)

    def test_unfinished_search_does_not_report_a_solution_count(self):
        puzzle = Puzzle(1, 1, ['B'], [1], [1], [1], [])
        with self.assertRaises(SearchBudgetExceeded):
            count_solutions(puzzle, timeout_seconds=0)

    def test_timed_out_removals_keep_clues(self):
        solution, base = construct_solution(ConstructConfig(
            rows=4, cols=4, numbers=[1, 2, 3], palette=['B', 'Y', 'V'], seed=42))
        stepper = DeconstructorStepper(base, solution, DeconstructConfig(
            seed=43, uniqueness_timeout_seconds=0))
        puzzle = stepper.run_to_target()
        self.assertEqual(stepper.reveals_count(), 32)
        self.assertEqual(count_solutions(puzzle, timeout_seconds=2), 1)

    def test_large_grid_finishes_and_remains_unique(self):
        start = monotonic()
        solution, base = construct_solution(ConstructConfig(
            rows=7, cols=5, numbers=[1, 2, 3, 4, 5],
            palette=['B', 'R', 'Y', 'V'], seed=42))
        stepper = DeconstructorStepper(base, solution, DeconstructConfig(
            seed=43, difficulty='HARD', generation_timeout_seconds=4))
        puzzle = stepper.run_to_target()
        self.assertLess(monotonic() - start, 6)
        self.assertLess(stepper.reveals_count(), 70)
        self.assertEqual(count_solutions(puzzle, timeout_seconds=2), 1)
        for given in puzzle.givens:
            number, color = solution[given.r, given.c]
            if given.num is not None:
                self.assertEqual(given.num, number)
            if given.col is not None:
                self.assertEqual(given.col, color)


if __name__ == '__main__':
    unittest.main()
