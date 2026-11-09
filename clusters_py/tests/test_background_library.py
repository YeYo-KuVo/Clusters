import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from background_library import choose_background


class BackgroundLibraryTests(unittest.TestCase):
    def test_avoids_repeats_and_remembers_previous_game(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            for name in ['garden.png', 'lagoon.png', 'flowers.png']:
                (directory/name).touch()
            history = directory/'history.txt'
            sequence = [choose_background(directory, random.Random(seed), history)
                        for seed in range(20)]
            self.assertTrue(all(a != b for a, b in zip(sequence, sequence[1:])))
            self.assertEqual(history.read_text(), sequence[-1].name)
            self.assertGreater(len(set(sequence)), 1)

    def test_single_background_can_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            image = directory/'only.png'
            image.touch()
            history = directory/'history.txt'
            self.assertEqual(choose_background(directory, history_path=history), image)
            self.assertEqual(choose_background(directory, history_path=history), image)


if __name__ == '__main__':
    unittest.main()
