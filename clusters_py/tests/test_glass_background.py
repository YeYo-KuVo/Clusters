import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from glass_background import frost


class GlassBackgroundTests(unittest.TestCase):
    def test_glass_retains_artwork_and_leaves_outside_unchanged(self):
        original = bytearray([40, 100, 60] * 24 * 24)
        result = frost(24, 24, original, [(4, 4, 16, 16)], radius=4)
        self.assertEqual(result[:3], original[:3])
        index = (12*24+12)*3
        for channel in range(3):
            self.assertGreater(result[index+channel], original[index+channel])
            self.assertLess(result[index+channel], 255)
        # Rounded corners expose the original artwork.
        corner = (4*24+4)*3
        self.assertEqual(result[corner:corner+3], original[corner:corner+3])

    def test_frost_blurs_details_instead_of_only_tinting(self):
        original = bytearray([0, 0, 0] * 24 * 24)
        index = (12*24+12)*3
        original[index:index+3] = bytes([255, 255, 255])
        result = frost(24, 24, original, [(0, 0, 24, 24)], opacity=0)
        self.assertLess(result[index], 255)
        self.assertGreater(result[index+3], 0)


if __name__ == '__main__':
    unittest.main()
