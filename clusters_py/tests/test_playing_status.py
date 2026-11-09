from pathlib import Path
import re
import struct
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editor import PlayEditor
from playing_status import PlayingStatusAnimation, PLAYING_FRAME_PATHS, FRAME_INTERVAL_MS
from play_view import GlassPlayView, RESULT_ICON_SIZE


class CanvasDouble:
    def __init__(self):
        self.timers = {}
        self.images = []
        self.serial = 0
        self.after_cancel = Mock(side_effect=self.timers.pop)
        self.itemconfigure = Mock()

    def after(self, delay, callback):
        self.serial += 1
        self.timers[self.serial] = (delay, callback)
        return self.serial

    def tick(self):
        timer = next(iter(self.timers))
        delay, callback = self.timers.pop(timer)
        callback()
        return delay


class PlayingStatusTests(unittest.TestCase):
    def make_animation(self):
        canvas = CanvasDouble()
        photos = [Mock() for _ in range(5)]
        for photo in photos:
            photo.width.return_value = photo.height.return_value = 176
        with patch('playing_status.tk.PhotoImage', side_effect=photos) as load:
            animation = PlayingStatusAnimation(canvas, RESULT_ICON_SIZE)
        self.assertEqual([call.kwargs['file'] for call in load.call_args_list],
                         [str(path) for path in PLAYING_FRAME_PATHS])
        self.assertEqual(animation.frames, photos)
        for photo in photos:
            photo.zoom.assert_not_called()
            photo.subsample.assert_not_called()
        return canvas, animation

    def test_assets_share_dimensions_alpha_and_clockwise_missing_positions(self):
        for index, path in enumerate(PLAYING_FRAME_PATHS):
            data = path.read_bytes()
            self.assertEqual(struct.unpack('>II', data[16:24]), (176, 176))
            self.assertEqual(data[25], 6)  # RGBA transparency.
            # Source artwork confirms fixed 72-degree slots, with a clockwise gap.
            source = (path.parent.parent / 'Clusters_Playing_Leaves_Assets' / f'playing_leaf_{index+1:02d}.svg').read_text()
            visible = [int(angle) for angle in re.findall(r'rotate\((\d+)\)', source)]
            self.assertEqual(set(visible), set(range(0, 360, 72)) - {index*72})
            self.assertEqual(len(visible), 4)

    def test_five_frame_order_six_second_loop_and_single_timer(self):
        canvas, animation = self.make_animation()
        animation.show(10)
        seen = [animation.frame]
        for _ in range(10):
            self.assertEqual(len(canvas.timers), 1)
            self.assertEqual(canvas.tick(), 1200)
            seen.append(animation.frame)
        self.assertEqual(seen, [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0])
        self.assertEqual(5*FRAME_INTERVAL_MS, 6000)
        for call in canvas.itemconfigure.call_args_list:
            self.assertEqual(call.args, (10,))
            self.assertEqual(set(call.kwargs), {'image'})  # No resizing/repositioning.

    def test_redraw_reattaches_without_restart_or_extra_timer(self):
        canvas, animation = self.make_animation()
        animation.show(10)
        canvas.tick()
        timer = animation._timer
        animation.show(20)
        animation.show(20)
        self.assertEqual(animation.frame, 1)
        self.assertEqual(animation._timer, timer)
        self.assertEqual(len(canvas.timers), 1)
        canvas.tick()
        canvas.itemconfigure.assert_called_with(20, image=animation.frames[2])

    def test_stop_cancels_timer_and_restart_shows_first_frame(self):
        canvas, animation = self.make_animation()
        animation.show(10)
        canvas.tick()
        timer = animation._timer
        animation.stop()
        canvas.after_cancel.assert_called_once_with(timer)
        self.assertFalse(canvas.timers)
        animation.stop()  # Cleanup is idempotent.
        animation._advance()  # A late callback cannot start another timer.
        self.assertFalse(canvas.timers)
        animation.show(20)
        canvas.itemconfigure.assert_called_with(20, image=animation.frames[0])
        self.assertEqual(len(canvas.timers), 1)

    def test_completed_and_failed_states_stop_animation(self):
        for state in ('correct', 'incorrect'):
            canvas, animation = self.make_animation()
            animation.show(10)
            view = SimpleNamespace(_result_state='idle', _playing_animation=animation,
                                   _draw_result=Mock(), owner=Mock())
            GlassPlayView.show_result(view, 'idle')
            view._draw_result.assert_not_called()  # Normal play does not redraw/flicker.
            GlassPlayView.show_result(view, state)
            self.assertFalse(canvas.timers)
            self.assertEqual(view._result_state, state)
            view._draw_result.assert_called_once_with()
            GlassPlayView.show_result(view, 'idle')
            self.assertEqual(animation.frame, 0)

    def test_reset_and_destroy_cleanup(self):
        canvas, animation = self.make_animation()
        animation.show(10)
        canvas.tick()
        view = SimpleNamespace(_result_state='idle', _playing_animation=animation,
                               _draw_result=Mock(), _poll_id=999, _pending=998,
                               after_cancel=Mock())
        GlassPlayView.restart_playing_animation(view)
        self.assertEqual(animation.frame, 0)
        view._draw_result.assert_called_once_with()
        animation.show(20)
        GlassPlayView._destroyed(view, SimpleNamespace(widget=object()))
        self.assertTrue(canvas.timers)  # A child widget does not stop Play.
        GlassPlayView._destroyed(view, SimpleNamespace(widget=view))
        self.assertFalse(canvas.timers)
        self.assertTrue(view._closed)
        self.assertEqual([call.args[0] for call in view.after_cancel.call_args_list], [999, 998])
        owner = Mock()
        PlayEditor._on_reset(owner)
        owner.play_view.restart_playing_animation.assert_called_once_with()
        owner.play_view = None
        PlayEditor._on_reset(owner)  # The optional plain Play UI still supports Reset.


if __name__ == '__main__':
    unittest.main()
