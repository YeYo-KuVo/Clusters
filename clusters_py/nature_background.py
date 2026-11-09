"""Pastel tropical artwork, with the plain background available in editor.py."""
from pathlib import Path
import subprocess
import tempfile
import tkinter as tk

from ui_widgets import BG


class NatureBackground(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, bg=BG, bd=0, highlightthickness=0, takefocus=False)
        self._asset = Path(__file__).with_name('assets') / 'backgrounds' / 'tropical_pastel.png'
        self._temporary = tempfile.TemporaryDirectory(prefix='clusters-background-')
        self._pending = None
        self._size = None
        self._photo = None
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.tk.call('lower', self._w)
        self.bind('<Configure>', self._request_redraw)
        self.bind('<Destroy>', self._cleanup)

    def _request_redraw(self, event):
        if self._pending is not None:
            self.after_cancel(self._pending)
        self._pending = self.after(100, lambda: self._redraw(event.width, event.height))

    def _redraw(self, width, height):
        self._pending = None
        if width < 2 or height < 2 or self._size == (width, height):
            return
        target = Path(self._temporary.name) / 'background.png'
        try:
            # macOS's built-in image resizer avoids another Python dependency.
            # Fit the full composition so flowers and fruit at the edges stay visible.
            subprocess.run(['/usr/bin/sips', '-z', str(height), str(width),
                            str(self._asset), '--out', str(target)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, timeout=3)
            photo = tk.PhotoImage(master=self, file=str(target))
        except (OSError, subprocess.SubprocessError, tk.TclError):
            return
        self._photo = photo
        self._size = (width, height)
        self.delete('all')
        self.create_image(0, 0, image=photo, anchor='nw')

    def _cleanup(self, event):
        if event.widget is self:
            if self._pending is not None:
                self.after_cancel(self._pending)
            self._temporary.cleanup()
