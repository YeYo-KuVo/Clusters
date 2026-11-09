"""Navigation regression tests, including an opt-in live Tk event-loop check."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import editor
from progress_store import ProgressStore
from puzzle_catalog import PuzzleCatalog


class NavigationTests(unittest.TestCase):
    def test_selection_hides_home_without_destroying_it(self):
        level = SimpleNamespace(puzzle_ids=('puzzle',))
        home = SimpleNamespace(catalog=SimpleNamespace(levels=[level]),
                               progress=SimpleNamespace(is_playable=lambda level: True),
                               withdraw=Mock(), quit=Mock(), destroy=Mock())
        app.HomeWindow._select_puzzle(home, 'puzzle')
        self.assertEqual(home.selected_puzzle, 'puzzle')
        home.withdraw.assert_called_once()
        home.quit.assert_called_once()
        home.destroy.assert_not_called()

    def test_app_restores_same_home_after_completed_play(self):
        catalog = PuzzleCatalog()
        puzzle_id = catalog.levels[0].puzzle_ids[0]
        with TemporaryDirectory() as directory:
            progress = ProgressStore(Path(directory)/'progress.json')
            home = Mock(closed=False, selected_puzzle=None)
            def select_or_close():
                if home.return_from_play.called:
                    home.closed = True
                    home.selected_puzzle = None
                else:
                    home.selected_puzzle = puzzle_id
            home.mainloop.side_effect = select_or_close
            def play(*args, **kwargs):
                kwargs['on_complete'](puzzle_id)
                return True
            with patch.object(app, 'HomeWindow', return_value=home) as create_home, \
                    patch.object(app, 'ProgressStore', return_value=progress), \
                    patch.object(app, 'launch_play_editor', side_effect=play) as launch:
                app.launch_app()
            create_home.assert_called_once()
            home.return_from_play.assert_called_once()
            home.destroy.assert_called_once()
            self.assertTrue(launch.call_args.kwargs['wait_for_close'])
            self.assertIs(launch.call_args.kwargs['master'], home)
            self.assertIn(puzzle_id, ProgressStore(progress.path).completed)

    def test_play_waits_for_its_own_window_when_home_is_alive(self):
        play = Mock(next_puzzle_requested=True)
        with patch.object(editor, 'PlayEditor', return_value=play):
            self.assertTrue(editor.launch_play_editor(None, None, 'BALANCED', 'id', wait_for_close=True))
        play.wait_window.assert_called_once()
        play.mainloop.assert_not_called()

    @unittest.skipUnless(os.environ.get('HUI_PU_GUI_TESTS') == '1', 'Requires a desktop Tk session')
    def test_live_completion_home_second_puzzle_home(self):
        events = []
        errors = []
        base_home, base_play = app.HomeWindow, editor.PlayEditor

        class Home(base_home):
            def report_callback_exception(self, kind, value, traceback):
                errors.append(value)
                self.close()

            def return_from_play(self):
                super().return_from_play()
                events.append(('home', self.state()))
                if len([event for event in events if event[0] == 'home']) == 1:
                    self.after(250, lambda: self._select_puzzle(self.catalog.levels[0].puzzle_ids[1]))
                else:
                    self.after(250, self.close)

            def __init__(self, *args):
                super().__init__(*args)
                self.after(250, lambda: self._select_puzzle(self.catalog.levels[0].puzzle_ids[0]))
                self.after(15000, self.close)

        class Play(base_play):
            def report_callback_exception(self, kind, value, traceback):
                errors.append(value)
                self.destroy()

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.after(400, self.complete_and_click_home)
                self.after(5000, self.destroy)

            def complete_and_click_home(self):
                for (r, c), (number, color) in self.solution.items():
                    self.state[r][c].num = number
                    self.state[r][c].col = color
                self._update_status()
                events.append(('complete', self.puzzle_id))
                self.after(150, self.click_home)

            def click_home(self):
                view = self.play_view
                button = view.home_button
                # Exercise the actual canvas event binding, not just _on_home.
                view.event_generate('<Button-1>', x=round(button.x+22), y=round(button.y+22))

        with TemporaryDirectory() as directory:
            progress_path = Path(directory)/'progress.json'
            progress = ProgressStore(progress_path)
            with patch.object(app, 'HomeWindow', Home), patch.object(editor, 'PlayEditor', Play), \
                    patch.object(app, 'ProgressStore', return_value=progress), \
                    patch.object(editor, 'SoundPlayer'):
                app.launch_app()
            self.assertEqual(errors, [])
            self.assertEqual([event[0] for event in events], ['complete', 'home', 'complete', 'home'])
            self.assertTrue(all(event[1] == 'normal' for event in events if event[0] == 'home'))
            self.assertEqual(len(ProgressStore(progress_path).completed), 2)

    @unittest.skipUnless(os.environ.get('HUI_PU_GUI_TESTS') == '1', 'Requires a desktop Tk session')
    def test_live_standalone_play_owns_and_closes_its_root(self):
        catalog = PuzzleCatalog()
        puzzle, solution = catalog.load_puzzle(catalog.levels[0].puzzle_ids[0])
        for return_home in (True, False):
            class Play(editor.PlayEditor):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.after(150, self._on_home if return_home else self.destroy)
            with patch.object(editor, 'PlayEditor', Play), patch.object(editor, 'SoundPlayer'):
                result = editor.launch_play_editor(puzzle, solution, 'BALANCED', 'standalone',
                                                   show_solution_reference=False)
            self.assertEqual(result, return_home)


if __name__ == '__main__':
    unittest.main()
