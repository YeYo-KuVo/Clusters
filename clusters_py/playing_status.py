"""Five stationary leaf frames; the empty position advances once every 1200 ms."""
from pathlib import Path
import tkinter as tk


PLAYING_FRAME_PATHS = tuple(
    Path(__file__).with_name('assets') / 'icons' / 'ui' /
    f'playing_leaf_{number:02d}.png' for number in range(1, 6))
FRAME_INTERVAL_MS = 6000 // len(PLAYING_FRAME_PATHS)


class PlayingStatusAnimation:
    def __init__(self, canvas, size):
        self.canvas = canvas
        self.frames = []
        for path in PLAYING_FRAME_PATHS:
            photo = tk.PhotoImage(master=canvas, file=str(path))
            self.frames.append(photo)
        self.frame = 0
        self.item = None
        self._timer = None

    def show(self, item):
        """Attach to a rebuilt canvas item without restarting the animation."""
        self.item = item
        self.canvas.itemconfigure(item, image=self.frames[self.frame])
        if self._timer is None:
            self._timer = self.canvas.after(FRAME_INTERVAL_MS, self._advance)

    def _advance(self):
        self._timer = None
        if self.item is None:
            return
        self.frame = (self.frame + 1) % len(self.frames)
        self.canvas.itemconfigure(self.item, image=self.frames[self.frame])
        self._timer = self.canvas.after(FRAME_INTERVAL_MS, self._advance)

    def stop(self):
        if self._timer is not None:
            self.canvas.after_cancel(self._timer)
            self._timer = None
        self.item = None
        self.frame = 0
