"""Shared, subtly rounded Tk surfaces."""
import tkinter as tk
from smooth_tiles import smooth_rectangle
from action_icons import draw_action_icon
from title_font import TITLE_FONT, register_title_font

if not register_title_font():
    TITLE_FONT = ("Helvetica", 25, "bold")

CORNER_RADIUS = 8

BG = "#f8f3ee"
SUM_TEXT = "#705a51"
TEXT_BLACK = "#433a35"

CELL_BG_DEFAULT = "#eee6dd"
BORDER_SELECTED = "#705a51"
BORDER_NORMAL = "#ffffff"

TILE_SIZE = 44
TILE_BORDER = 2
TILE_CONTENT = TILE_SIZE - 2 * TILE_BORDER
NUMBER_FONT = ("Helvetica", 14)
SUM_FONT = NUMBER_FONT

# Final palette (6 colors like your mock):
# Blue, Red, Yellow, Green, Purple, Gray
# Codes: B, R, Y, V (verde), P, G (gray)
COLOR_HEX = {
    "B": "#499dbb",  # blue-gray
    "R": "#b77655",  # muted red
    "Y": "#eed06d",  # muted yellow
    "V": "#31865f",  # green (verde)
    "P": "#bb8cc8",  # purple
    "G": "#9b9fa4",  # gray
    # compatibility (if old puzzles still output these)
    "O": "#ffa94d",  # orange
}




def rounded_rectangle(canvas, x1, y1, x2, y2, radius=CORNER_RADIUS, **options):
    options.setdefault("fill", "")
    radius = min(radius, (x2-x1)/2, (y2-y1)/2)
    points = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
              x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
              x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **options)


class RoundedPanel(tk.Frame):
    """Let Tk size the content normally; paint rounded corners behind it."""
    def __init__(self, master, padx=7, pady=7, color="#ffffff"):
        super().__init__(master, bg=master["bg"], bd=0, highlightthickness=0)
        self._surface = tk.Canvas(self, bg=master["bg"], highlightthickness=0, bd=0)
        self._surface.place(x=0, y=0, relwidth=1, relheight=1)
        self.content = tk.Frame(self, bg=color)
        self.grid_columnconfigure(0, weight=1)
        self.content.grid(row=0, column=0, padx=padx, pady=pady, sticky="ew")
        self.content.lift()
        self.bind("<Configure>", lambda event: self._draw_surface(event.width, event.height, color))

    def _draw_surface(self, width, height, color):
        self._surface.delete("all")
        rounded_rectangle(self._surface, 0, 0, width, height, radius=CORNER_RADIUS,
                          fill=color, outline="")


class GridCell(tk.Canvas):
    """Fixed-size cell: only its paint changes when selected or filled."""
    def __init__(self, master, size, color, font):
        super().__init__(master, width=size, height=size, bg=master["bg"],
                         highlightthickness=0, bd=0)
        self.size = size
        self.paint = dict(bg=color, fg="#433a35", text="", font=font,
                          highlightbackground="#ffffff")
        self._draw()

    def config(self, **options):
        self.paint.update(options)
        self._draw()

    def _draw(self):
        self.delete("all")
        smooth_rectangle(self, 1, 1, self.size-1, self.size-1, radius=CORNER_RADIUS,
                          fill=self.paint["bg"], outline=self.paint["highlightbackground"], width=2)
        self.create_text(self.size/2, self.size/2, text=self.paint["text"],
                         fill=self.paint["fg"], font=self.paint["font"])


def fit_window_to_content(window, scrollable=False):
    """Resolve nested layouts before showing the window at its full size."""
    window.update_idletasks()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    if scrollable:
        height = min(height, max(320, window.winfo_screenheight()-100))
    window.geometry(f"{width}x{height}")
    window.minsize(width, min(height, 480) if scrollable else height)
    window.resizable(True, True)
    window.deiconify()


class PlayTool(tk.Canvas):
    """Square palette tile drawn consistently across platforms."""
    def __init__(self, master, label, callback, color="#eee6dd", eraser=False, enabled=True):
        super().__init__(master, width=TILE_SIZE, height=TILE_SIZE, bd=0, bg=master["bg"], highlightthickness=0)
        self.label, self.color, self.eraser = label, color, eraser
        self.enabled, self.active = enabled, False
        self.bind("<Button-1>", lambda event: callback() if self.enabled else None)
        self.set_active(False)

    def set_active(self, active):
        self.active = active
        self.delete("all")
        self.configure(cursor="hand2" if self.enabled else "arrow")
        smooth_rectangle(self, 1, 1, TILE_SIZE-1, TILE_SIZE-1, fill=self.color,
                              outline="#705a51" if active else "#ffffff", width=2)
        if not self.enabled:
            self.create_text(TILE_SIZE/2, TILE_SIZE/2, text="×", fill="#705a51", font=NUMBER_FONT)
        elif self.eraser:
            self.create_polygon(10, 25, 23, 12, 33, 22, 23, 32, 17, 32,
                                fill="#ffffff", outline="#705a51", width=2)
            self.create_line(17, 18, 27, 28, fill="#705a51", width=2)
        else:
            self.create_text(TILE_SIZE/2, TILE_SIZE/2, text=self.label, fill=TEXT_BLACK,
                             font=NUMBER_FONT)


class ActionButton(tk.Canvas):
    """Text action using the same flat tile styling as the palettes."""
    def __init__(self, master, label, callback):
        self.button_width = TILE_SIZE if label in ("Undo", "Lock", "Unlock", "Reset") else 88
        super().__init__(master, width=self.button_width, height=TILE_SIZE,
                         bg=master["bg"], highlightthickness=0, bd=0)
        self.label = label
        self.enabled = True
        self.active = False
        self.bind("<Button-1>", lambda event: callback() if self.enabled else None)
        self.set_state()

    def set_state(self, enabled=None, active=None, label=None):
        if enabled is not None:
            self.enabled = enabled
        if active is not None:
            self.active = active
        if label is not None:
            self.label = label
        self.delete("all")
        self.configure(cursor="hand2" if self.enabled else "arrow")
        smooth_rectangle(self, 1, 1, self.button_width-1, TILE_SIZE-1,
                              fill="#31865f" if self.active else "#ffffff",
                              outline="#28724f" if self.active else "#eee6dd", width=2)
        color = "#bdb1a8" if not self.enabled else ("#ffffff" if self.active else SUM_TEXT)
        if not draw_action_icon(self, self.label, self.button_width/2, TILE_SIZE/2, color):
            self.create_text(self.button_width/2, TILE_SIZE/2, text=self.label, fill=color,
                             font=("Helvetica", 12, "bold"))


