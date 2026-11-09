from branding import brand_header
import tkinter as tk
from ui_widgets import (RoundedPanel, fit_window_to_content, PlayTool, ActionButton,
                        BG, SUM_TEXT, COLOR_HEX, TITLE_FONT)
from sounds import SoundPlayer
from dataclasses import dataclass
from typing import List, Set, Dict, Callable, Optional, Tuple
from datetime import datetime


# =========================
# Visual palette (final)
# Codes: B,R,Y,V,P,G  (V=green, G=gray)
# =========================
COLOR_ORDER = ["B", "R", "Y", "V", "P", "G"]
ROW_COL_OPTIONS = list(range(3, 10))  # 3..9
NUMBER_OPTIONS = list(range(1, 10))   # 1..9

GLOBAL_MAX_COLORS = 6


def default_seed_timestamp_seconds() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S"))


# =========================
# Cascading rules
# =========================
def max_number_allowed(rows: int, cols: int) -> int:
    """
    Simple rule:
      - Numbers 8 and 9 unlock only on large boards:
          min_dim >= 5 AND area >= 49
      - Otherwise cap at 7 (UI shows 1..9 but 8/9 become X).
    """
    A = rows * cols
    min_dim = min(rows, cols)

    if (min_dim >= 5) and (A >= 49):
        return 9
    return 7


def max_distinct_numbers_allowed(A: int) -> int:
    if A <= 9:
        return 2
    if A <= 16:
        return 3
    if A <= 25:
        return 5
    if A <= 36:
        return 6
    return 7


def max_colors_allowed(A: int, min_dim: int) -> int:
    """
    Relaxed area-based unlocks for max selectable colors:
      - min_dim <= 3: cap at 3
      - A <= 16: 3
      - A < 36: 3
      - A < 64: 4
      - A >= 64: 6
    """
    if min_dim <= 3:
        return min(GLOBAL_MAX_COLORS, 3)

    if A <= 16:
        return min(GLOBAL_MAX_COLORS, 3)
    if A < 36:
        return min(GLOBAL_MAX_COLORS, 3)
    if A < 64:
        return min(GLOBAL_MAX_COLORS, 4)
    return min(GLOBAL_MAX_COLORS, 6)


# =========================
# Result object
# =========================
@dataclass
class CalibrationResult:
    rows: int
    cols: int
    numbers: List[int]
    colors: List[str]
    balance: str
    seed: int


# =========================
# UI Widgets
# =========================
class TileButton(PlayTool):
    def __init__(self, master, label, on_click):
        super().__init__(master, label, on_click)

    def set_state(self, enabled, selected):
        self.enabled = enabled
        self.set_active(selected)


class ColorSwatch(TileButton):
    def __init__(self, master, code, on_click):
        PlayTool.__init__(self, master, "", on_click, color=COLOR_HEX[code])


# =========================
# Calibrator UI
# =========================
class CalibrationUI(tk.Tk):
    def __init__(self, on_start: Callable[[CalibrationResult], None]):
        super().__init__()
        self.withdraw()
        self.configure(bg=BG)
        self.title("Hui Pu — Calibrate")
        self.sounds = SoundPlayer(self.after)

        self.on_start = on_start
        self.generating = False

        self.rows = 5
        self.cols = 5

        self.selected_numbers: Set[int] = set([1, 2, 3, 4, 5])
        # A default color keeps Play available immediately; users can change it.
        self.selected_colors: List[str] = [COLOR_ORDER[0]]

        # Widgets refs
        self.row_btns: Dict[int, TileButton] = {}
        self.col_btns: Dict[int, TileButton] = {}
        self.num_btns: Dict[int, TileButton] = {}
        self.color_btns: Dict[str, ColorSwatch] = {}

        self.status = tk.Label(self, text="", bg=self["bg"], fg="#888888", font=("Helvetica", 11))
        self.start_btn = ActionButton(self, "Play", self._start)

        self._build()
        self._cascade_all()
        fit_window_to_content(self)

    def destroy(self):
        if hasattr(self, "sounds"):
            self.sounds.close()
        super().destroy()

    def _build(self):
        outer = tk.Frame(self, bg=BG, padx=22, pady=20)
        outer.pack(fill="x")
        brand_header(outer, BG).pack(pady=(0, 12))

        def section(title):
            panel = RoundedPanel(outer, padx=10, pady=10)
            panel.pack(fill="x", pady=(0, 12))
            card = panel.content
            tk.Label(card, text=title, bg="#ffffff", fg=SUM_TEXT,
                     font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 4))
            return card

        board = section("BOARD SIZE")
        for title, buttons, callback in (
            ("Rows", self.row_btns, self._set_rows),
            ("Columns", self.col_btns, self._set_cols),
        ):
            tk.Label(board, text=title, bg="#ffffff", fg=SUM_TEXT,
                     font=("Helvetica", 11)).pack(pady=(4, 2))
            strip = tk.Frame(board, bg="#ffffff")
            strip.pack()
            for v in ROW_COL_OPTIONS:
                btn = TileButton(strip, str(v), lambda vv=v, cb=callback: cb(vv))
                btn.pack(side="left", padx=2, pady=2)
                buttons[v] = btn

        numbers = section("NUMBERS")
        strip = tk.Frame(numbers, bg="#ffffff")
        strip.pack()
        for i, n in enumerate(NUMBER_OPTIONS):
            btn = TileButton(strip, str(n), lambda nn=n: self._toggle_number(nn))
            btn.grid(row=i//3, column=i%3, padx=2, pady=2)
            self.num_btns[n] = btn

        colors = section("COLORS")
        strip = tk.Frame(colors, bg="#ffffff")
        strip.pack()
        for code in COLOR_ORDER:
            sw = ColorSwatch(strip, code, lambda cc=code: self._toggle_color(cc))
            sw.pack(side="left", padx=2, pady=2)
            self.color_btns[code] = sw

        self.status.configure(fg=SUM_TEXT, font=("Helvetica", 12))
        self.status.pack(pady=(0, 8))
        self.start_btn.pack(pady=(0, 20))

    # ---- rows/cols ----
    def _set_rows(self, v: int):
        if self.generating:
            return
        self.sounds.play()
        self.rows = v
        self._cascade_all()

    def _set_cols(self, v: int):
        if self.generating:
            return
        self.sounds.play()
        self.cols = v
        self._cascade_all()

    # ---- numbers ----
    def _toggle_number(self, n: int):
        if self.generating:
            return
        self.sounds.play()
        if n not in self.num_btns:
            return
        # ignore disabled
        if not self.num_btns[n].enabled:
            return

        A = self.rows * self.cols
        cap = max_distinct_numbers_allowed(A)

        if n in self.selected_numbers:
            self.selected_numbers.remove(n)
        else:
            if len(self.selected_numbers) >= cap:
                return
            self.selected_numbers.add(n)

        self._cascade_all()

    # ---- colors ----
    def _toggle_color(self, c: str):
        if self.generating:
            return
        self.sounds.play()
        # ignore disabled
        if not self.color_btns[c].enabled:
            return

        A = self.rows * self.cols
        min_dim = min(self.rows, self.cols)
        cap = max_colors_allowed(A, min_dim)

        if c in self.selected_colors:
            self.selected_colors.remove(c)
        else:
            # Enforce cap: require user to deselect one before selecting another.
            if len(self.selected_colors) >= cap:
                return
            self.selected_colors.append(c)

        self._cascade_all()

    # ---- cascade ----
    def _effective_numbers(self) -> List[int]:
        if self.selected_numbers:
            return sorted(self.selected_numbers)
        return [1, 2, 3]

    def _cascade_all(self):
        rows, cols = self.rows, self.cols
        A = rows * cols
        min_dim = min(rows, cols)

        # numbers allowed
        maxN = max_number_allowed(rows, cols)
        allowed_numbers = set(range(1, maxN + 1))

        # clamp selection
        self.selected_numbers = {n for n in self.selected_numbers if n in allowed_numbers}

        # enforce distinct cap
        capN = max_distinct_numbers_allowed(A)
        if len(self.selected_numbers) > capN:
            self.selected_numbers = set(sorted(self.selected_numbers)[:capN])

        # colors cap (user may choose ANY colors, up to the cap)
        col_cap = max_colors_allowed(A, min_dim)

        # Clamp selection to known palette codes and to cap
        self.selected_colors = [c for c in self.selected_colors if c in COLOR_ORDER]
        if len(self.selected_colors) > col_cap:
            self.selected_colors = self.selected_colors[:col_cap]

        # render everything
        for value, btn in self.row_btns.items():
            btn.set_state(enabled=True, selected=(value == rows))
        for value, btn in self.col_btns.items():
            btn.set_state(enabled=True, selected=(value == cols))
        for n, btn in self.num_btns.items():
            enabled = (n in allowed_numbers)
            selected = (n in self.selected_numbers)
            btn.set_state(enabled=enabled, selected=selected)

        # Color swatches: always show all colors. If cap reached, disable unselected swatches (they show "X").
        cap_reached = (len(self.selected_colors) >= col_cap)
        for code, sw in self.color_btns.items():
            selected = (code in self.selected_colors)
            enabled = selected or (not cap_reached)
            sw.set_state(enabled=enabled, selected=selected)

        # start button gating
        start_ok = True
        if not self.selected_numbers:
            start_ok = False
        if sum(self.selected_numbers) > A:
            start_ok = False
        if not self.selected_colors:
            start_ok = False

        self.start_btn.set_state(enabled=start_ok, active=start_ok)

        if not self.selected_numbers:
            message = "Select at least one number"
        elif sum(self.selected_numbers) > A:
            message = "Choose fewer numbers or a larger board"
        elif not self.selected_colors:
            message = f"Choose up to {col_cap} colors to start"
        else:
            message = f"{rows} × {cols} board  ·  {len(self.selected_numbers)} numbers  ·  {len(self.selected_colors)} colors"
        self.status.config(text=message)

    def set_generating(self, generating: bool):
        self.generating = generating
        self.configure(cursor="watch" if generating else "")
        if generating:
            self.status.config(text="Generating puzzle…")
            self.start_btn.set_state(enabled=False, active=False)
        else:
            self._cascade_all()

    # ---- start ----
    def _start(self):
        if self.generating:
            return
        self.sounds.play()
        rows, cols = self.rows, self.cols
        A = rows * cols

        seed = default_seed_timestamp_seconds()

        result = CalibrationResult(
            rows=rows,
            cols=cols,
            numbers=sorted(self.selected_numbers),
            colors=list(self.selected_colors),
            balance="BALANCED",
            seed=seed
        )

        self.on_start(result)