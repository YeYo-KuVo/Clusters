import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sounds import SoundPlayer


class SoundTests(unittest.TestCase):
    def make_player(self):
        with patch('sounds.sys.platform', 'darwin'), patch('sounds.Thread'):
            return SoundPlayer()

    def test_library_path_matches_project_sibling(self):
        player = self.make_player()
        self.assertEqual(player.directory, Path(__file__).resolve().parents[3] / 'SOUNDS')

    def test_interactions_and_ambience_use_independent_commands(self):
        player = self.make_player()
        with patch('sounds.sys.platform', 'darwin'):
            player.play()
            player.play('wood_tick')
            player.start_ambience()
        self.assertEqual([player._commands.get_nowait() for _ in range(3)],
                         ['button', 'button', 'start'])

    def test_mute_stops_all_audio_and_blocks_clicks_until_unmuted(self):
        player = self.make_player()
        with patch('sounds.sys.platform', 'darwin'):
            player.start_ambience()
            player.set_muted(True)
            player.play()
            player.set_muted(False)
            player.play()
        commands = []
        while not player._commands.empty():
            commands.append(player._commands.get_nowait())
        self.assertEqual(commands, ['start', 'stop', 'start', 'button'])

    def test_completion_chirp_respects_mute(self):
        player = self.make_player()
        with patch('sounds.sys.platform', 'darwin'):
            player.celebrate()
            player.set_muted(True)
            player.celebrate()
        self.assertEqual(player._commands.get_nowait(), 'chirp')
        self.assertEqual(player._commands.get_nowait(), 'stop')
        self.assertTrue(player._commands.empty())

    def test_close_stops_future_commands(self):
        player = self.make_player()
        player.close()
        with patch('sounds.sys.platform', 'darwin'):
            player.play()
            player.start_ambience()
        self.assertEqual(player._commands.get_nowait(), 'quit')
        self.assertTrue(player._commands.empty())


if __name__ == '__main__':
    unittest.main()
