"""Small, one-shot completion reactions in the top action row."""
from pathlib import Path
import tkinter as tk


class Toucan:
    def __init__(self, canvas):
        self.canvas = canvas
        folder = Path(__file__).with_name('assets') / 'toucan'
        self.frames = [tk.PhotoImage(master=canvas, file=str(folder/name)).subsample(2)
                       for name in ('idle.png', 'look_down.png', 'wing_up.png', 'wing_down.png')]
        self.state = 'idle'
        self.x = self.y = 0
        self.frame = 0
        self.offset = 0
        self._timer = None
        self._step = 0

    def place(self, x, y):
        self.x, self.y = x, y
        self._draw()

    def _draw(self):
        self.canvas.delete('toucan')
        self.canvas.create_image(self.x, self.y+self.offset, image=self.frames[self.frame],
                                 anchor='center', tags='toucan')

    def react(self, state):
        if state == self.state:
            self._draw()
            return False
        self.cancel()
        self.state, self._step = state, 0
        self.frame, self.offset = (1 if state == 'incorrect' else 0), 0
        self._draw()
        if state == 'correct':
            self._animate()
        return True

    def _animate(self):
        self._timer = None
        if self.state == 'correct':
            if self._step >= 10:
                self.frame, self.offset = 3, 0
                self._draw()
                return
            self.frame = 2 if self._step % 2 == 0 else 3
            self.offset = -3 if self._step % 2 == 0 else 0
        else:
            return
        self._draw()
        self._step += 1
        self._timer = self.canvas.after(160 if self.state == 'correct' else 300, self._animate)

    def cancel(self):
        if self._timer is not None:
            self.canvas.after_cancel(self._timer)
            self._timer = None
