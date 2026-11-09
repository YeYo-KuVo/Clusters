import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editor import PlayEditor
from progress_store import ProgressStore
from puzzle_catalog import PuzzleCatalog, Level
from solver import count_solutions, ClustersSolver


class CatalogTests(unittest.TestCase):
    def test_all_slots_and_starter_puzzles_are_valid_unique_and_solvable(self):
        catalog = PuzzleCatalog()
        self.assertEqual(len(catalog.levels), 8)
        self.assertEqual(sum(len(level.slots) for level in catalog.levels), 240)
        self.assertEqual(sum(slot is None for level in catalog.levels for slot in level.slots), 230)
        self.assertEqual(len(catalog.levels[0].puzzle_ids), 10)
        dimensions = []
        signatures = set()
        for puzzle_id in catalog.levels[0].puzzle_ids:
            puzzle, solution = catalog.load_puzzle(puzzle_id)
            dimensions.append((puzzle.rows, puzzle.cols))
            self.assertEqual(count_solutions(puzzle, timeout_seconds=5), 1)
            checker = ClustersSolver(puzzle)
            for coordinate, value in solution.items():
                checker.assign_val(coordinate, value)
            self.assertTrue(checker.complete_blocks_ok())
            self.assertTrue(checker.sums_exact_ok())
            signature = (puzzle.rows, puzzle.cols, tuple(sorted(solution.items())))
            self.assertNotIn(signature, signatures)
            signatures.add(signature)
            self.assertTrue(any(g.num is None or g.col is None for g in puzzle.givens))
        self.assertEqual(dimensions.count((3, 3)), 4)
        self.assertEqual(dimensions.count((3, 4)), 3)
        self.assertEqual(dimensions.count((4, 3)), 3)
        self.assertTrue(all(not level.puzzle_ids for level in catalog.levels[1:]))

    def test_missing_or_duplicate_slot_reference_rejected(self):
        source = Path(__file__).resolve().parents[1] / 'data'
        for replacement in ('missing-id', 'level-01-puzzle-01'):
            with TemporaryDirectory() as directory:
                path = Path(directory)
                levels = json.loads((source/'levels.json').read_text())
                levels['levels'][0]['slots'][1] = replacement
                (path/'levels.json').write_text(json.dumps(levels))
                (path/'puzzles.json').write_text((source/'puzzles.json').read_text())
                with self.assertRaises(ValueError):
                    PuzzleCatalog(path)


class ProgressTests(unittest.TestCase):
    def test_threshold_duplicates_empty_levels_and_restart(self):
        catalog = PuzzleCatalog()
        with TemporaryDirectory() as directory:
            path = Path(directory)/'progress.json'
            progress = ProgressStore(path)
            progress.refresh_unlocks(catalog.levels)
            first, second = catalog.levels[:2]
            self.assertTrue(progress.is_playable(first))
            self.assertEqual(progress.required_count(first), 7)
            for puzzle_id in first.puzzle_ids[:6]:
                progress.record_completion(puzzle_id, catalog)
            progress.record_completion(first.puzzle_ids[0], catalog)
            self.assertEqual(progress.completed_count(first), 6)
            self.assertNotIn(second.id, progress.unlocked)
            progress.record_completion(first.puzzle_ids[6], catalog)
            restored = ProgressStore(path)
            self.assertEqual(restored.completed_count(first), 7)
            self.assertIn(second.id, restored.unlocked)
            self.assertFalse(restored.is_playable(second))
            self.assertNotIn(catalog.levels[2].id, restored.unlocked)
            self.assertEqual(list(path.parent.glob('*.tmp')), [])
            # Future catalog growth cannot revoke an earned unlock.
            expanded = Level(first.id, first.title, first.dimensions, 70,
                             first.puzzle_ids + tuple(f'future-{i}' for i in range(20)))
            restored.refresh_unlocks((expanded, second))
            self.assertIn(second.id, restored.unlocked)
            with self.assertRaises(ValueError):
                restored.record_completion('unknown', catalog)

    def test_failed_atomic_write_preserves_previous_progress(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'progress.json'
            progress = ProgressStore(path)
            progress.save()
            original = path.read_bytes()
            progress.completed.add('example')
            with patch('progress_store.os.replace', side_effect=OSError('disk unavailable')):
                with self.assertRaises(OSError):
                    progress.save()
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob('*.tmp')), [])

    def test_malformed_progress_is_not_overwritten(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'progress.json'
            for invalid in ('{invalid', '[]', '{"version":1,"completed":"wrong"}'):
                path.write_text(invalid)
                with self.assertRaises(ValueError):
                    ProgressStore(path)
                self.assertEqual(path.read_text(), invalid)

    def test_completion_hook_is_once_per_play_session(self):
        owner = SimpleNamespace(_on_complete=Mock(), _completion_recorded=False, puzzle_id='example')
        PlayEditor._record_completion(owner)
        PlayEditor._record_completion(owner)
        owner._on_complete.assert_called_once_with('example')


if __name__ == '__main__':
    unittest.main()
