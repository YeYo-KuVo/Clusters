"""Player-facing level selection; no calibration or generation controls."""
import tkinter as tk

from branding import brand_header
from ui_widgets import BG, SUM_TEXT, CELL_BG_DEFAULT


class HomeView(tk.Frame):
    def __init__(self, parent, catalog, progress, on_puzzle, on_instructions):
        super().__init__(parent, bg=BG)
        brand_header(self, BG).pack(pady=(20, 6))
        tk.Label(self, text='A little focus. A little discovery.', bg=BG, fg=SUM_TEXT,
                 font=('Helvetica', 12)).pack()
        tk.Button(self, text='How to play', command=on_instructions, fg=SUM_TEXT,
                  highlightthickness=0).pack(pady=(10, 16))
        canvas = tk.Canvas(self, bg=BG, bd=0, highlightthickness=0, yscrollincrement=24)
        canvas.pack(fill='both', expand=True)
        self._hint = tk.Label(self, text='', bg=BG, fg=SUM_TEXT, font=('Helvetica', 10), height=2)
        self._hint.pack(fill='x')
        cards = tk.Frame(canvas, bg=BG)
        window = canvas.create_window(0, 0, window=cards, anchor='nw')
        self._canvas = canvas
        self._cards = []
        self._columns = 0
        self._window = window
        for index, level in enumerate(catalog.levels):
            self._cards.append(self._level_card(cards, level, index, catalog, progress, on_puzzle))
        cards.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', self._resize)
        # The root binding also receives wheel events over child labels/buttons.
        parent.bind('<MouseWheel>', self._scroll)
        parent.bind('<Button-4>', lambda event: canvas.yview_scroll(-1, 'units'))
        parent.bind('<Button-5>', lambda event: canvas.yview_scroll(1, 'units'))

    def _level_card(self, parent, level, index, catalog, progress, on_puzzle):
        available = progress.is_playable(level)
        card = tk.Frame(parent, bg='#ffffff', padx=20, pady=16,
                        highlightbackground='#e4d9cc', highlightthickness=1)
        heading = tk.Frame(card, bg='#ffffff')
        heading.pack(fill='x')
        tk.Label(heading, text=level.title, bg='#ffffff', fg=SUM_TEXT,
                 font=('Helvetica', 17, 'bold')).pack(side='left')
        state = 'Play' if available else ('Coming soon' if not level.puzzle_ids else 'Locked')
        tk.Label(heading, text=state, bg='#ffffff', fg='#31865f' if available else '#9b8b7a',
                 font=('Helvetica', 10)).pack(side='right')
        tk.Label(card, text=level.dimension_label, bg='#ffffff', fg=SUM_TEXT,
                 font=('Helvetica', 11)).pack(anchor='w', pady=(4, 10))
        slots = tk.Frame(card, bg='#ffffff')
        slots.pack()
        for slot, puzzle_id in enumerate(level.slots):
            completed = puzzle_id in progress.completed if puzzle_id else False
            color = '#dcebdc' if completed else (CELL_BG_DEFAULT if puzzle_id else '#f5f2ed')
            tile = tk.Canvas(slots, width=42, height=36, bg='#ffffff', bd=0,
                             highlightthickness=0, cursor='hand2' if available and puzzle_id else '')
            tile.grid(row=slot//6, column=slot%6, padx=3, pady=3)
            tile.create_rectangle(1, 1, 41, 35, fill=color, outline='#e4d9cc')
            if puzzle_id:
                tile.create_text(21, 18, text=f'{slot+1} ✓' if completed else str(slot+1),
                                 fill=SUM_TEXT if available else '#aa9e91', font=('Helvetica', 11))
                if available:
                    tile.bind('<Button-1>', lambda event, pid=puzzle_id: on_puzzle(pid))
                    puzzle, _ = catalog.load_puzzle(puzzle_id)
                    tile.bind('<Enter>', lambda event, p=puzzle: self._hint.configure(
                        text=f'{p.rows}×{p.cols} puzzle · Select a number or color, then a cell'))
                    tile.bind('<Leave>', lambda event: self._hint.configure(text=''))
        count = progress.completed_count(level)
        caption = f'{count} / {len(level.puzzle_ids)} completed' if level.puzzle_ids else '30 spaces for future puzzles'
        tk.Label(card, text=caption, bg='#ffffff', fg=SUM_TEXT,
                 font=('Helvetica', 11)).pack(anchor='w', pady=(10, 0))
        if available and index < len(catalog.levels)-1:
            required = progress.required_count(level)
            caption = ('Next level earned · puzzles coming soon' if
                       catalog.levels[index+1].id in progress.unlocked and not catalog.levels[index+1].puzzle_ids
                       else f'Complete {required} puzzles ({level.unlock_percent}%) to unlock the next level')
        elif level.puzzle_ids and not available:
            caption = 'Complete the previous level’s target to unlock'
        else:
            caption = 'More puzzles will be added later'
        tk.Label(card, text=caption, bg='#ffffff', fg='#9b8b7a',
                 font=('Helvetica', 10), wraplength=290, justify='left').pack(anchor='w', pady=(4, 0))
        return card

    def _resize(self, event):
        columns = 2 if event.width >= 730 else 1
        if columns != self._columns:
            for card in self._cards:
                card.grid_forget()
            for index, card in enumerate(self._cards):
                card.grid(row=index//columns, column=index%columns, padx=10, pady=10, sticky='n')
            self._columns = columns
        self._canvas.itemconfigure(self._window, width=event.width)
        for column in range(2):
            self._cards[0].master.grid_columnconfigure(column, weight=1 if column < columns else 0)

    def _scroll(self, event):
        if event.delta:
            units = int(event.delta/120) if abs(event.delta) >= 120 else (1 if event.delta > 0 else -1)
            self._canvas.yview_scroll(-units, 'units')
        return 'break'
