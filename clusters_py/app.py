"""Keep Home alive while the existing Play window runs, then restore it."""
import tkinter as tk
from tkinter import messagebox

from editor import launch_play_editor
from home_view import HomeView
from instructions_view import InstructionsView
from progress_store import ProgressStore
from puzzle_catalog import PuzzleCatalog
from ui_widgets import BG


class HomeWindow(tk.Tk):
    def __init__(self, catalog, progress):
        super().__init__()
        self.title('Hui Pū')
        self.configure(bg=BG)
        self.geometry(f'800x{min(800, max(480, self.winfo_screenheight()-100))}')
        self.minsize(680, 480)
        self.catalog, self.progress = catalog, progress
        self.selected_puzzle = None
        self._screen = None
        self.closed = False
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.show_home()

    def close(self):
        self.closed = True
        self.withdraw()
        self.quit()

    def _replace(self, screen_type, *args):
        for event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.unbind(event)
        if self._screen is not None:
            self._screen.destroy()
        self._screen = screen_type(self, *args)
        self._screen.pack(fill='both', expand=True)

    def show_home(self):
        self._replace(HomeView, self.catalog, self.progress, self._select_puzzle, self.show_instructions)

    def show_instructions(self):
        self._replace(InstructionsView, self.show_home)

    def _select_puzzle(self, puzzle_id):
        # Recheck availability at the navigation boundary as well as in the UI.
        if any(puzzle_id in level.puzzle_ids and self.progress.is_playable(level)
               for level in self.catalog.levels):
            self.selected_puzzle = puzzle_id
            self.withdraw()
            self.quit()

    def return_from_play(self):
        self.selected_puzzle = None
        self.show_home()
        self.deiconify()
        self.lift()


def launch_app():
    catalog = PuzzleCatalog()
    try:
        progress = ProgressStore()
    except (OSError, ValueError) as error:
        # Preserve an unreadable file rather than silently overwriting history.
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Progress could not be loaded',
                             f'Your progress file was left unchanged.\n\n{error}', parent=root)
        root.destroy()
        return
    progress.refresh_unlocks(catalog.levels)

    def completed(puzzle_id):
        try:
            progress.record_completion(puzzle_id, catalog)
        except OSError as error:
            messagebox.showerror('Progress could not be saved',
                                 f'This completion is remembered for this session only.\n\n{error}')

    home = HomeWindow(catalog, progress)
    try:
        while not home.closed:
            home.mainloop()
            puzzle_id = home.selected_puzzle
            if home.closed or puzzle_id is None:
                return
            puzzle, solution = catalog.load_puzzle(puzzle_id)
            if not launch_play_editor(puzzle, solution, bias_label='BALANCED', puzzle_id=puzzle_id,
                                      on_complete=completed, show_solution_reference=False,
                                      wait_for_close=True, master=home):
                return
            home.return_from_play()
    finally:
        home.destroy()
