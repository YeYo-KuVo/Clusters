"""Shared Hui Pu word artwork, kept alive for the lifetime of its widget."""
from pathlib import Path
import tkinter as tk


WORD_ICON_PATHS = tuple(Path(__file__).with_name('assets') / 'icons' / 'ui' / f'{word}.png'
                        for word in ('Hui', 'Pu'))


def load_word_images(master):
    return [tk.PhotoImage(master=master, file=str(path)) for path in WORD_ICON_PATHS]


def brand_header(parent, bg):
    frame = tk.Frame(parent, bg=bg)
    frame._word_images = load_word_images(frame)
    for photo in frame._word_images:
        tk.Label(frame, image=photo, bg=bg, bd=0).pack(side='left', padx=4)
    return frame
