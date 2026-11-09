from branding import brand_header
import tkinter as tk
from ui_widgets import (RoundedPanel, GridCell, fit_window_to_content, PlayTool, ActionButton,
                        BG, SUM_TEXT, TEXT_BLACK, CELL_BG_DEFAULT, BORDER_SELECTED, BORDER_NORMAL,
                        TILE_SIZE, TILE_BORDER, TILE_CONTENT, NUMBER_FONT, SUM_FONT, COLOR_HEX, TITLE_FONT)
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Callable

from play_view import GlassPlayView
from nature_background import NatureBackground
from sounds import SoundPlayer
from solver import Puzzle, Coord, Val
from calibration import CalibrationUI, CalibrationResult
from constructor import ConstructConfig, construct_solution
from deconstructor import DeconstructConfig, DeconstructorStepper


# =========================
# Visual theme / colors
# =========================
PALETTE_ORDER = ["B", "R", "Y", "V", "P", "G"]

# Keyboard hint text (no letters for color, but we show label)
COLOR_KEY_HINT = "Colors (tap swatch; numbers can be typed 0–9)"

# Set False to restore the original plain cream Play background.
PLAY_NATURE_BACKGROUND = True

SHOW_SOLUTION_REFERENCE = True  # set False when sharing with testers


# =========================
# Play UI
# =========================
@dataclass
class CellState:
    num: Optional[int] = None
    col: Optional[str] = None  # one of palette codes (e.g., "B","R","Y","V","P","G") or None


class PlayEditor(tk.Tk):
    """
    Mobile-style interaction:
      - Select ONE tool (number OR color) from palettes
      - Click cell to apply tool
      - Disabled palette items show "X"
      - Keyboard digits select number tool

    Includes:
      - Undo (multi-step)
      - Reset
      - Auto-check on completion
    """

    def __init__(self, puzzle: Puzzle, solution: Dict[Coord, Val], bias_label: str, puzzle_id: str):
        super().__init__()
        self.withdraw()
        self.configure(bg=BG)
        self.title("Hui Pu — Play")
        self.sounds = SoundPlayer(self.after)

        self.next_puzzle_requested = False
        self.puzzle = puzzle
        self.solution = solution
        self.bias_label = bias_label  # "SMALL" / "BALANCED" / "BIG"
        self.puzzle_id = puzzle_id

        self.R = puzzle.rows
        self.C = puzzle.cols

        # Allowed sets from puzzle definition
        self.allowed_numbers = set(puzzle.numbers)
        self.allowed_colors = set(puzzle.palette)

        # Givens map (r,c)->(num?, col?)
        self.givens_map: Dict[Tuple[int, int], Tuple[Optional[int], Optional[str]]] = {}
        for g in puzzle.givens:
            self.givens_map[(g.r, g.c)] = (g.num, g.col)

        # Locks per cell
        self.lock_num = [[False] * self.C for _ in range(self.R)]
        self.lock_col = [[False] * self.C for _ in range(self.R)]
        for (r, c), (n, col) in self.givens_map.items():
            if n is not None:
                self.lock_num[r][c] = True
            if col is not None:
                self.lock_col[r][c] = True

        # Player state starts with givens
        self.state: List[List[CellState]] = [[CellState() for _ in range(self.C)] for _ in range(self.R)]
        for r in range(self.R):
            for c in range(self.C):
                n, col = self.givens_map.get((r, c), (None, None))
                self.state[r][c].num = n
                self.state[r][c].col = col

        # Undo
        self.initial_state = self._snapshot_state()
        self.undo_stack: List[List[List[Tuple[Optional[int], Optional[str]]]]] = []
        # Optional checkpoint: when set, Undo cannot go earlier than this snapshot.
        # Implementation: locking saves a snapshot and clears undo history so the earliest reachable state becomes the lock.
        self.lock_state: Optional[List[List[Tuple[Optional[int], Optional[str]]]]] = None

        # Selection
        self.selected_cell: Optional[Tuple[int, int]] = None

        # Active tool (exclusive)
        self.active_tool_type: Optional[str] = None  # "num" | "col" | None
        self.active_tool_value: Optional[object] = None  # int for num, str for col, or None for clears

        # UI refs
        self.cells: List[List[GridCell]] = []
        self.status_label: Optional[tk.Label] = None
        self.undo_btn: Optional[ActionButton] = None
        self.lock_btn: Optional[ActionButton] = None
        self.lock_status_lbl: Optional[tk.Label] = None

        self.num_tool_btns: Dict[int, PlayTool] = {}   # 0..9 (0 clears number)
        self.col_tool_btns: Dict[str, PlayTool] = {}   # palette codes + "CLEAR"

        self._build_ui()
        self._render_all()
        self._update_status()
        self._update_undo_button()
        self._update_tool_highlights()
        fit_window_to_content(self, scrollable=hasattr(self, 'play_view'))
        self.sounds.start_ambience()
        if SHOW_SOLUTION_REFERENCE:
            self._open_solution_reference_window()

        # Key bindings
        self.bind("<Escape>", self._clear_tool)
        self.bind("<Delete>", self._on_delete_color)
        self.bind("<BackSpace>", self._on_delete_color)
        self.bind_all("<Command-z>", self._on_undo)
        self.bind_all("<Control-z>", self._on_undo)

        # Keyboard numbers select number tool (0 clears number)
        self.bind("<KeyPress>", self._on_keypress)

        self.focus_force()

    def _on_home(self):
        self.sounds.play()
        self.next_puzzle_requested = True
        self.destroy()

    # ---------- snapshots / undo ----------
    def destroy(self):
        if hasattr(self, "sounds"):
            self.sounds.close()
        super().destroy()

    def _snapshot_state(self) -> List[List[Tuple[Optional[int], Optional[str]]]]:
        snap = []
        for r in range(self.R):
            row = []
            for c in range(self.C):
                st = self.state[r][c]
                row.append((st.num, st.col))
            snap.append(row)
        return snap

    def _restore_snapshot(self, snap: List[List[Tuple[Optional[int], Optional[str]]]]) -> None:
        for r in range(self.R):
            for c in range(self.C):
                n, col = snap[r][c]
                self.state[r][c].num = n
                self.state[r][c].col = col

    def _push_undo(self) -> None:
        self.undo_stack.append(self._snapshot_state())
        self._update_undo_button()

    def _update_undo_button(self) -> None:
        if self.undo_btn is None:
            return
        self.undo_btn.set_state(enabled=bool(self.undo_stack))

    def _update_lock_ui(self) -> None:
        if self.lock_btn is not None:
            # Show whether a checkpoint exists
            self.lock_btn.set_state(label=("Unlock" if self.lock_state is not None else "Lock"),
                                    active=(self.lock_state is not None))
        if self.lock_status_lbl is not None:
            self.lock_status_lbl.config(text=("🔒 Locked" if self.lock_state is not None else ""))

    def _on_lock(self) -> None:
        self.sounds.play()
        # Toggle lock: if currently unlocked, create checkpoint; if locked, clear checkpoint.
        if self.lock_state is None:
            self.lock_state = self._snapshot_state()
            # Clear undo history so user can only undo back to this checkpoint
            self.undo_stack.clear()
        else:
            # Unlock returns to normal undo behavior (still limited by available history)
            self.lock_state = None
        self._update_undo_button()
        self._update_lock_ui()
        self._update_status()

    def _on_undo(self, _event=None) -> None:
        if not self.undo_stack:
            return
        self.sounds.play()
        snap = self.undo_stack.pop()
        self._restore_snapshot(snap)
        self.selected_cell = None
        self._render_all()
        self._update_status()
        self._update_undo_button()
        self._update_lock_ui()

    # ---------- tool handling ----------
    def _set_num_tool(self, n: int) -> None:
        # allow selecting even if not allowed? as instrument, show X for disabled; clicking does nothing.
        if n != 0 and n not in self.allowed_numbers:
            return
        self.active_tool_type = "num"
        self.active_tool_value = n  # 0 means clear number
        self._update_tool_highlights()
        self.sounds.play()

    def _set_color_tool(self, code: str) -> None:
        # code can be "CLEAR" or a color code like "B"
        if code != "CLEAR" and code not in self.allowed_colors:
            return
        self.active_tool_type = "col"
        self.active_tool_value = code
        self._update_tool_highlights()
        self.sounds.play()

    def _clear_tool(self, _event=None) -> None:
        self.active_tool_type = None
        self.active_tool_value = None
        self._update_tool_highlights()

    def _update_tool_highlights(self) -> None:
        # Number tools
        for n, btn in self.num_tool_btns.items():
            active = (self.active_tool_type == "num" and self.active_tool_value == n)
            btn.set_active(active)

        # Color tools
        for code, btn in self.col_tool_btns.items():
            active = (self.active_tool_type == "col" and self.active_tool_value == code)
            btn.set_active(active)

        # Also refresh status line (shows tool)
        self._update_status()

    # ---------- applying tools ----------
    def _apply_tool_to_cell(self, r: int, c: int) -> None:
        if self.active_tool_type is None:
            return  # no tool selected; just selection highlight

        st = self.state[r][c]
        changed = False

        # Apply number tool
        if self.active_tool_type == "num":
            n = int(self.active_tool_value)
            if self.lock_num[r][c]:
                return
            new_num = None if n == 0 else n
            if st.num != new_num:
                self._push_undo()
                st.num = new_num
                changed = True

        # Apply color tool
        elif self.active_tool_type == "col":
            code = str(self.active_tool_value)
            if self.lock_col[r][c]:
                return
            new_col = None if code == "CLEAR" else code
            if st.col != new_col:
                self._push_undo()
                st.col = new_col
                changed = True

        if changed:
            self._render_cell(r, c)
            self._update_status()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        if PLAY_NATURE_BACKGROUND:
            self.cell_spacer = tk.PhotoImage(master=self, width=TILE_CONTENT, height=TILE_CONTENT)
            self.play_view = GlassPlayView(self)
            self._update_status()
            return
        outer = tk.Frame(self, padx=48 if PLAY_NATURE_BACKGROUND else 22, pady=20, bg=BG)
        outer.pack(fill="both", expand=True)
        self.nature_background = NatureBackground(outer) if PLAY_NATURE_BACKGROUND else None
        brand_header(outer, BG).pack()

        topbar = tk.Frame(outer, bg=BG)
        topbar.pack(pady=(0, 12))
        self.undo_btn = ActionButton(topbar, "Undo", self._on_undo)
        self.undo_btn.pack(side="left", padx=4)
        self.lock_btn = ActionButton(topbar, "Lock", self._on_lock)
        self.lock_btn.pack(side="left", padx=4)
        ActionButton(topbar, "Reset", self._on_reset).pack(side="left", padx=4)
        # Keep exactly three equal-width actions: Lock shares the window's
        # centerline with the board and palettes. Its active style shows lock state.

        board_area = tk.Frame(outer, bg=BG)
        board_area.pack()
        # Equal side gutters center the playable board, independently of the sums.
        sum_gutter = 30
        # A shared uniform group keeps the gutters equal even when text or
        # display scaling makes the sums wider than their minimum size.
        board_area.grid_columnconfigure(0, minsize=sum_gutter, uniform="sum_gutters")
        board_area.grid_columnconfigure(2, minsize=sum_gutter, uniform="sum_gutters")
        tk.Frame(board_area, bg=BG, width=sum_gutter, height=1).grid(row=1, column=2)
        column_sums = tk.Frame(board_area, bg=BG, padx=7)
        column_sums.grid(row=0, column=1)
        row_sums = tk.Frame(board_area, bg=BG, pady=7)
        row_sums.grid(row=1, column=0)
        board_panel = RoundedPanel(board_area, padx=7, pady=7)
        board_panel.grid(row=1, column=1)
        frame = board_panel.content
        # A transparent image makes label dimensions pixels, keeping every cell square.
        self.cell_spacer = tk.PhotoImage(master=self, width=TILE_CONTENT, height=TILE_CONTENT)
        def sum_tile(parent, value, row, column):
            is_column_sum = parent is column_sums
            tk.Label(parent, image=self.cell_spacer, compound="center", text=str(value),
                     width=TILE_CONTENT if is_column_sum else 24,
                     height=24 if is_column_sum else TILE_CONTENT, padx=0, pady=0,
                     bg=BG, fg=SUM_TEXT, font=SUM_FONT,
                     relief="flat", bd=0, highlightthickness=TILE_BORDER,
                     highlightbackground=BG).grid(row=row, column=column, padx=1, pady=1)

        for c in range(self.C):
            sum_tile(column_sums, self.puzzle.col_sums[c], 0, c)
        self.cells = []
        for r in range(self.R):
            row_widgets = []
            for c in range(self.C):
                lbl = GridCell(frame, size=TILE_SIZE, color=CELL_BG_DEFAULT, font=NUMBER_FONT)
                lbl.grid(row=r, column=c, padx=1, pady=1)
                lbl.bind("<Button-1>", lambda e, rr=r, cc=c: self._on_cell_click(rr, cc))
                row_widgets.append(lbl)
            self.cells.append(row_widgets)
            sum_tile(row_sums, self.puzzle.row_sums[r], r, 0)

        self.status_label = tk.Label(outer, text="", bg=BG, fg=SUM_TEXT,
                                     font=("Helvetica", 12), wraplength=410, pady=12)
        self.status_label.pack()
        tools_panel = RoundedPanel(outer, padx=10, pady=10)
        tools_panel.pack()
        card = tools_panel.content
        nums = tk.Frame(card, bg="#ffffff")
        nums.pack(pady=(4, 30))
        for i, n in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]):
            btn = PlayTool(nums, "" if n == 0 else str(n),
                           lambda nn=n: self._set_num_tool(nn), eraser=(n == 0),
                           enabled=(n == 0 or n in self.allowed_numbers))
            btn.grid(row=i//5, column=i%5, padx=2, pady=2)
            self.num_tool_btns[n] = btn
        colors = tk.Frame(card, bg="#ffffff")
        colors.pack(pady=(4, 0))
        for code in PALETTE_ORDER + ["CLEAR"]:
            btn = PlayTool(colors, "", lambda cc=code: self._set_color_tool(cc),
                           color=COLOR_HEX.get(code, "#eee6dd"), eraser=(code == "CLEAR"),
                           enabled=(code == "CLEAR" or code in self.allowed_colors))
            btn.pack(side="left", padx=2)
            self.col_tool_btns[code] = btn
        if PLAY_NATURE_BACKGROUND:
            # Leave space for the fruit and flowers along the lower border.
            tk.Frame(outer, width=1, height=44, bg=BG).pack()
        self._update_lock_ui()

    def _open_solution_reference_window(self) -> None:
        win = tk.Toplevel(self)
        win.withdraw()
        win.title("Hui Pu — Solution")
        win.configure(bg=BG)

        outer = tk.Frame(win, padx=22, pady=20, bg=BG)
        outer.pack(fill="x")
        brand_header(outer, BG).pack()
        tk.Label(outer, text="Solution", bg=BG, fg=SUM_TEXT,
                 font=("Helvetica", 12)).pack(pady=(4, 12))

        board_area = tk.Frame(outer, bg=BG)
        board_area.pack()
        for column in (0, 2):
            board_area.grid_columnconfigure(column, minsize=30, uniform="sum_gutters")
        tk.Frame(board_area, bg=BG, width=30, height=1).grid(row=1, column=2)
        column_sums = tk.Frame(board_area, bg=BG, padx=7)
        column_sums.grid(row=0, column=1)
        row_sums = tk.Frame(board_area, bg=BG, pady=7)
        row_sums.grid(row=1, column=0)
        panel = RoundedPanel(board_area, padx=7, pady=7)
        panel.grid(row=1, column=1)

        def sum_label(parent, value, row, column):
            is_column_sum = parent is column_sums
            tk.Label(parent, image=self.cell_spacer, compound="center", text=str(value),
                     width=TILE_CONTENT if is_column_sum else 24,
                     height=24 if is_column_sum else TILE_CONTENT, padx=0, pady=0,
                     bg=BG, fg=SUM_TEXT, font=SUM_FONT, relief="flat", bd=0,
                     highlightthickness=TILE_BORDER, highlightbackground=BG).grid(
                         row=row, column=column, padx=1, pady=1)

        for c in range(self.C):
            sum_label(column_sums, self.puzzle.col_sums[c], 0, c)
        for r in range(self.R):
            sum_label(row_sums, self.puzzle.row_sums[r], r, 0)
            for c in range(self.C):
                number, color = self.solution[(r, c)]
                cell = GridCell(panel.content, size=TILE_SIZE,
                                color=COLOR_HEX.get(color, CELL_BG_DEFAULT), font=NUMBER_FONT)
                cell.config(text=str(number),
                            fg="#ffffff" if color in {"B", "R", "V", "P", "G"} else TEXT_BLACK)
                cell.grid(row=r, column=c, padx=1, pady=1)

        tk.Label(outer, text="Solution reference · Read only", bg=BG, fg="#917c72",
                 font=("Helvetica", 11)).pack(pady=(12, 8))
        ActionButton(outer, "Close", win.destroy).pack()
        fit_window_to_content(win)
        win.lift()

    # ---------- events ----------
    def _on_cell_click(self, r: int, c: int) -> None:
        self.sounds.play()
        # select cell
        prev = self.selected_cell
        self.selected_cell = (r, c)
        if prev is not None:
            self._render_cell(prev[0], prev[1])
        self._render_cell(r, c)

        # apply tool if any
        self._apply_tool_to_cell(r, c)

    def _on_keypress(self, event: tk.Event) -> None:
        ch = (event.char or "").strip()
        if not ch:
            return
        if ch.isdigit():
            self._set_num_tool(int(ch))  # 0 clears number

    def _on_delete_color(self, _event=None) -> None:
        # Treat Delete as selecting CLEAR color tool and applying if cell selected
        if self.selected_cell is None:
            return
        r, c = self.selected_cell
        if self.lock_col[r][c]:
            return
        if self.state[r][c].col is None:
            return
        self._push_undo()
        self.state[r][c].col = None
        self._render_cell(r, c)
        self._update_status()

    def _on_reset(self) -> None:
        self.sounds.play()
        self._restore_snapshot(self.initial_state)
        self.undo_stack.clear()
        self.lock_state = None
        self.selected_cell = None
        self._render_all()
        self._update_status()
        view = getattr(self, 'play_view', None)
        if view is not None:
            view.restart_playing_animation()
        self._update_undo_button()
        self._update_lock_ui()

    # ---------- rendering ----------
    def _render_all(self) -> None:
        for r in range(self.R):
            for c in range(self.C):
                self._render_cell(r, c)

    def _render_cell(self, r: int, c: int) -> None:
        st = self.state[r][c]
        lbl = self.cells[r][c]

        bg = CELL_BG_DEFAULT
        if st.col and st.col in COLOR_HEX:
            bg = COLOR_HEX[st.col]
        lbl.config(bg=bg)

        lbl.config(text="" if st.num is None else str(st.num),
                   fg=("#ffffff" if st.col in {"B", "R", "V", "P", "G"} else TEXT_BLACK))

        # Keep border width fixed: selection changes color, never geometry.
        border = BORDER_SELECTED if self.selected_cell == (r, c) else BORDER_NORMAL
        lbl.config(highlightthickness=2, highlightbackground=border, highlightcolor=border)

        # All grid numbers use the same font, including givens.
        lbl.config(relief="flat", bd=0,
                   font=NUMBER_FONT)

    # ---------- status ----------
    def _is_complete(self) -> bool:
        for r in range(self.R):
            for c in range(self.C):
                if self.state[r][c].num is None:
                    return False
                if self.state[r][c].col is None:
                    return False
        return True

    def _is_correct(self) -> bool:
        for r in range(self.R):
            for c in range(self.C):
                n_truth, col_truth = self.solution[(r, c)]
                st = self.state[r][c]
                if st.num != n_truth:
                    return False
                if st.col != col_truth:
                    return False
        return True

    def _update_status(self) -> None:
        view = getattr(self, 'play_view', None)
        if view is not None:
            state = 'idle' if not self._is_complete() else ('correct' if self._is_correct() else 'incorrect')
            view.show_result(state)
            self.status_label.config(text="")
            return
        if not self._is_complete():
            self.status_label.config(text="")
            return

        if self._is_correct():
            self.status_label.config(text="Congratulations — you successfully filled this Hui Pu grid!")
        else:
            self.status_label.config(text="Incorrect")


def launch_play_editor(puzzle: Puzzle, solution: Dict[Coord, Val], bias_label: str, puzzle_id: str) -> bool:
    editor = PlayEditor(puzzle, solution, bias_label, puzzle_id)
    editor.mainloop()
    return editor.next_puzzle_requested


# =========================
# App entry: calibration -> generate -> play
# =========================
def launch_app():
    from queue import Queue, Empty
    from threading import Thread
    from tkinter import messagebox

    def on_start(cfg: CalibrationResult):
        ui.set_generating(True)
        results = Queue()

        def generate():
            try:
                results.put(generate_puzzle_from_calibration(cfg))
            except Exception as error:
                results.put(error)

        def check_result():
            try:
                result = results.get_nowait()
            except Empty:
                ui.after(80, check_result)
                return
            if isinstance(result, Exception):
                ui.set_generating(False)
                messagebox.showerror("Puzzle generation failed", str(result), parent=ui)
                return
            puzzle, solution, style, puzzle_id, _difficulty = result
            selection.append((puzzle, solution, style, puzzle_id))
            ui.destroy()

        Thread(target=generate, daemon=True).start()
        ui.after(80, check_result)

    while True:
        selection = []
        ui = CalibrationUI(on_start)
        ui.mainloop()
        if not selection:
            return
        puzzle, solution, style, puzzle_id = selection[0]
        if not launch_play_editor(puzzle, solution, bias_label=style, puzzle_id=puzzle_id):
            return

# =========================
# Puzzle generation (reusable)
# =========================

def generate_puzzle_from_calibration(cfg: CalibrationResult) -> Tuple[Puzzle, Dict[Coord, Val], str, str, str]:
    """
    Runs: calibration -> constructor -> deconstructor.

    Returns:
      - puzzle: the deconstructed (playable) Puzzle
      - sol: full solution dict (r,c)->(num,col)
      - style: bias label ("SMALL"/"BALANCED"/"BIG")
      - puzzle_id: human-readable identifier string
      - difficulty: difficulty label string (e.g. "HARD")

    Raises RuntimeError with a user-friendly message if generation fails.

    NOTE: This function does not open any UI windows; it is safe to call from a CLI exporter.
    """

    # All puzzles use the balanced generator mode.
    style = "BALANCED"

    MAX_CONSTRUCT_TRIES = 25
    MAX_DECONSTRUCT_TRIES = 10

    c_cfg = ConstructConfig(
        rows=cfg.rows,
        cols=cfg.cols,
        palette=cfg.colors,
        numbers=cfg.numbers,
        seed=cfg.seed,
        style=style,
        require_all_numbers=True,
        require_all_colors=True,
        max_attempts=300,
    )

    # --- constructor retries (vary seed) ---
    sol = None
    base_puzzle = None
    base_seed = cfg.seed
    for i in range(MAX_CONSTRUCT_TRIES):
        try_seed = base_seed + i
        c_cfg.seed = try_seed
        try:
            sol, base_puzzle = construct_solution(c_cfg)
            break
        except RuntimeError:
            continue

    if sol is None or base_puzzle is None:
        raise RuntimeError(
            "Hui Pu couldn't generate a puzzle for this exact configuration.\n\n"
            "Try one of these:\n"
            "• Add a larger number (e.g., include 4 on 4×4)\n"
            "• Increase the grid size\n"
            "• Select more colors (if available)\n"
        )

    difficulty = "HARD"
    d_cfg = DeconstructConfig(
        seed=c_cfg.seed + 1,
        difficulty=difficulty,
        max_steps=50_000,
        strategy="any",
    )

    # --- deconstructor retries (vary seed) ---
    puzzle = None
    for j in range(MAX_DECONSTRUCT_TRIES):
        try:
            d_cfg.seed = (c_cfg.seed + 1) + j
            stepper = DeconstructorStepper(base_puzzle=base_puzzle, solution=sol, cfg=d_cfg)
            puzzle = stepper.run_to_target()
            break
        except RuntimeError:
            continue

    if puzzle is None:
        raise RuntimeError(
            "A solution grid was found, but Hui Pu couldn't deconstruct it into a unique puzzle.\n\n"
            "Try selecting more numbers/colors, or a different grid size."
        )

    puzzle_id = (
        f"{c_cfg.seed} | {cfg.rows}x{cfg.cols} | nums={','.join(map(str, cfg.numbers))} | "
        f"cols={''.join(cfg.colors)} | bias={style}"
    )

    return puzzle, sol, style, puzzle_id, difficulty
