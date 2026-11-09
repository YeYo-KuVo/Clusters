"""Single-page placeholder for the future visual gameplay guide."""
import tkinter as tk

from branding import brand_header
from ui_widgets import BG, SUM_TEXT


class InstructionsView(tk.Frame):
    def __init__(self, parent, on_home):
        super().__init__(parent, bg=BG, padx=20, pady=20)
        brand_header(self, BG).pack(pady=(0, 16))
        tk.Label(self, text='How to play', bg=BG, fg=SUM_TEXT,
                 font=('Helvetica', 22, 'bold')).pack(pady=(0, 8))
        tk.Label(self, text='Your visual guide is coming soon.', bg=BG, fg=SUM_TEXT,
                 font=('Helvetica', 12)).pack(pady=(0, 20))
        preview = tk.Canvas(self, width=600, height=280, bg=BG, bd=0, highlightthickness=0)
        preview.pack(fill='x', expand=True)
        # A code-generated neutral placeholder image, not final instructional art.
        self._placeholder = tk.PhotoImage(master=self, width=600, height=280)
        self._placeholder.put('#eee6dd', to=(0, 0, 600, 280))
        self._placeholder.put('#f5f0e9', to=(12, 12, 588, 268))
        image = preview.create_image(300, 140, image=self._placeholder, anchor='center')
        title = preview.create_text(300, 126, text='GAMEPLAY INFOGRAPHIC', fill=SUM_TEXT,
                            font=('Helvetica', 15, 'bold'))
        subtitle = preview.create_text(300, 156, text='Placeholder · artwork to follow', fill='#9b8b7a',
                            font=('Helvetica', 12))
        def center_placeholder(event):
            preview.coords(image, event.width/2, 140)
            preview.coords(title, event.width/2, 126)
            preview.coords(subtitle, event.width/2, 156)
        preview.bind('<Configure>', center_placeholder)
        tk.Button(self, text='Back to Home', command=on_home, fg=SUM_TEXT).pack(pady=(20, 0))
