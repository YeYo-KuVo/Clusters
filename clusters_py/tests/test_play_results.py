import sys
import struct
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from action_icons import icon_png, draw_action_icon, SKULL_ICON_PATH, SPROUT_ICON_PATH
from editor import PlayEditor
from play_view import GlassPlayView, TOOL_LABEL_FONT, RESULT_ICON_SIZE


class PlayResultTests(unittest.TestCase):
    def test_success_sound_only_on_entry_including_after_edit(self):
        view = SimpleNamespace(_result_state='idle', _draw_result=Mock(), _playing_animation=Mock(),
                               owner=SimpleNamespace(sounds=Mock()))
        for state in ('idle', 'incorrect', 'correct', 'correct'):
            GlassPlayView.show_result(view, state)
        self.assertEqual(view.owner.sounds.celebrate.call_count, 1)
        # Redrawing a completed board must not repeat the sound.
        GlassPlayView.show_result(view, 'correct')
        self.assertEqual(view.owner.sounds.celebrate.call_count, 1)
        GlassPlayView.show_result(view, 'idle')
        GlassPlayView.show_result(view, 'correct')
        self.assertEqual(view.owner.sounds.celebrate.call_count, 2)

    def test_all_three_states_draw_distinct_icons(self):
        view = SimpleNamespace(delete=Mock(), create_text=Mock(), create_image=Mock(), tag_bind=Mock(),
                               _playing_animation=Mock(), home_button=Mock(),
                               _result_center=(100, 30))
        with patch('play_view.draw_action_icon') as draw:
            for state, label in [('idle', 'ResultPlaying'), ('correct', 'ResultCorrect'), ('incorrect', 'ResultRetry')]:
                view._result_state = state
                GlassPlayView._draw_result(view)
                if state == 'idle':
                    view._playing_animation.show.assert_called_once_with(view.create_image.return_value)
                    draw.assert_not_called()
                else:
                    self.assertEqual(draw.call_args.args[1], label)
                view.create_text.assert_not_called()
                view.home_button.set_active.assert_called_with(state == 'correct')
            view.delete.assert_called_with('result-icon')
        icons = [icon_png(label, '#705a51') for label in
                 ('ResultPlaying', 'ResultCorrect', 'ResultRetry')]
        self.assertTrue(all(icons))
        self.assertEqual(len(set(icons)), 3)

    def test_skull_uses_transparent_asset_and_scales_to_fit(self):
        self.assertEqual(icon_png('ResultRetry', '#705a51'), SKULL_ICON_PATH.read_bytes())
        canvas = Mock(spec=['create_image'])
        photo = Mock()
        data = SKULL_ICON_PATH.read_bytes()
        self.assertEqual(data[25], 6)  # RGBA, rather than an opaque white rectangle.
        width, height = struct.unpack('>II', data[16:24])
        photo.width.return_value, photo.height.return_value = width, height
        with patch('action_icons.tk.PhotoImage', return_value=photo) as load:
            self.assertTrue(draw_action_icon(canvas, 'ResultRetry', 20, 30, '#705a51', size=88, tags='result'))
            self.assertEqual(load.call_args.kwargs['data'], SKULL_ICON_PATH.read_bytes())
            photo.subsample.assert_not_called()
            canvas.create_image.assert_called_once_with(20, 30, image=photo, tags='result')
            draw_action_icon(canvas, 'ResultRetry', 20, 30, '#705a51', size=88)
            self.assertEqual(load.call_count, 1)

    def test_success_uses_supplied_sprout_asset(self):
        self.assertEqual(icon_png('ResultCorrect', '#705a51'), SPROUT_ICON_PATH.read_bytes())

    def test_menu_icons_use_antialiased_images(self):
        canvas = Mock(spec=['create_image'])
        with patch('action_icons.tk.PhotoImage') as photo:
            for label in ('SoundOn', 'SoundOff', 'BackgroundOn', 'BackgroundOff',
                          'Undo', 'Lock', 'Unlock', 'Reset', 'Home'):
                with self.subTest(label=label):
                    self.assertTrue(draw_action_icon(canvas, label, 22, 22, '#705a51'))
                    self.assertEqual(photo.call_args.kwargs['data'], icon_png(label, '#705a51'))
                    self.assertEqual(photo.call_args.kwargs['format'], 'PNG')
            self.assertEqual(canvas.create_image.call_count, 9)

    def test_layout_groups_corner_controls_and_scrolls_to_tools(self):
        for cols, rows in ((4, 4), (5, 7), (7, 5), (7, 12)):
            with self.subTest(cols=cols, rows=rows):
                owner = Mock(C=cols, R=rows)
                owner.sounds.muted = False
                owner.puzzle.col_sums = [10]*cols
                owner.puzzle.row_sums = [10]*rows
                owner.allowed_numbers, owner.allowed_colors = {1, 2}, {'B'}
                texts = {}
                def create_text(x, y, **options):
                    item = len(texts)+1
                    texts[item] = (x, y, options)
                    return item
                view = SimpleNamespace(
                    _revision=0, owner=owner, background_visible=False,
                    _word_images=[Mock(), Mock()], create_image=Mock(),
                    background_asset=None, delete=Mock(), configure=Mock(), create_text=create_text,
                    bbox=lambda item: (0, texts[item][1]-15, 100, texts[item][1]+15),
                    _draw_result=Mock(), tag_bind=Mock(), _next_puzzle=Mock(),
                    _toggle_sound=Mock(), _toggle_background=Mock())
                width, height = max(520, cols*46+100), 600
                with patch('play_view.CanvasTile') as tile, patch('play_view.Thread'):
                    GlassPlayView._layout(view, width, height)
                menu = tile.call_args_list[:6]
                self.assertEqual([call.args[2] for call in menu], [11]*6)
                self.assertEqual(menu[0].args[1], 16)
                self.assertEqual(menu[-1].args[1]+44, width-16)
                self.assertLess(menu[2].args[1]+44, width/2-RESULT_ICON_SIZE/2)
                self.assertGreater(menu[3].args[1], width/2+RESULT_ICON_SIZE/2)
                self.assertEqual([call.kwargs['label'] for call in menu],
                                 ['Home', 'SoundOn', 'BackgroundOff', 'Undo', 'Lock', 'Reset'])
                self.assertEqual(len(tile.call_args_list), 6+cols*rows+17)
                self.assertEqual(view._result_center[0], width/2)
                word_calls = view.create_image.call_args_list
                self.assertEqual(len(word_calls), 2)
                self.assertLess(word_calls[0].args[0], view._result_center[0]-RESULT_ICON_SIZE/2)
                self.assertGreater(word_calls[1].args[0], view._result_center[0]+RESULT_ICON_SIZE/2)
                for call in word_calls:
                    self.assertEqual(call.args[1], view._result_center[1])
                self.assertFalse(any('CLUSTERS' in str(text) for text in texts.values()))
                bounds = view.section_bounds
                self.assertEqual(bounds[1][0]-bounds[0][0], 20)
                for previous, following in zip(bounds[1:], bounds[2:]):
                    self.assertLess(previous[1], following[0])
                scroll_height = view.configure.call_args.kwargs['scrollregion'][3]
                self.assertGreaterEqual(scroll_height, bounds[-1][1]+38)
                self.assertGreaterEqual(scroll_height, height)
                self.assertAlmostEqual(bounds[2][0]-bounds[1][1], bounds[3][0]-bounds[2][1])
                self.assertEqual(word_calls[0].kwargs['anchor'], 'e')
                self.assertEqual(word_calls[1].kwargs['anchor'], 'w')
                self.assertEqual(word_calls[1].args[0]-word_calls[0].args[0], RESULT_ICON_SIZE+20)

    def test_mouse_wheel_supports_trackpad_and_wheel_deltas(self):
        view = SimpleNamespace(yview_scroll=Mock())
        for delta, units in ((1, -1), (-3, 1), (120, -1), (-240, 2)):
            GlassPlayView._scroll(view, SimpleNamespace(delta=delta))
            view.yview_scroll.assert_called_with(units, 'units')

    def test_home_returns_to_setup_without_requiring_completion(self):
        owner = SimpleNamespace(sounds=Mock(), destroy=Mock(), next_puzzle_requested=False)
        PlayEditor._on_home(owner)
        owner.sounds.play.assert_called_once_with()
        owner.destroy.assert_called_once_with()
        self.assertTrue(owner.next_puzzle_requested)

    def test_detection_without_bottom_sentence_for_each_state(self):
        owner = SimpleNamespace(play_view=Mock(), status_label=Mock(),
                                _is_complete=Mock(), _is_correct=Mock())
        for complete, correct, state in [(False, False, 'idle'),
                                         (True, False, 'incorrect'), (True, True, 'correct')]:
            with self.subTest(state=state):
                owner._is_complete.return_value = complete
                owner._is_correct.return_value = correct
                PlayEditor._update_status(owner)
                owner.play_view.show_result.assert_called_with(state)
                text = owner.status_label.config.call_args.kwargs['text']
                self.assertEqual(text, '')


if __name__ == '__main__':
    unittest.main()
