"""The Play scene uses one canvas so artwork is continuous behind controls."""
from queue import Queue, Empty
import tempfile
from threading import Thread
import tkinter as tk

from branding import load_word_images
from playing_status import PlayingStatusAnimation
from background_library import choose_background
from smooth_tiles import smooth_rectangle
from glass_background import render_background
from ui_widgets import (BG, SUM_TEXT, TEXT_BLACK, CELL_BG_DEFAULT, COLOR_HEX,
                        NUMBER_FONT, SUM_FONT, TILE_SIZE, draw_action_icon)


TOOL_LABEL_FONT = ('Helvetica', 10)
RESULT_ICON_SIZE = 176
RESULT_COLOR = '#4c261b'


class CanvasLabel:
    def __init__(self, canvas, item):
        self.canvas, self.item = canvas, item

    def config(self, **options):
        self.canvas.itemconfigure(self.item, **{k: v for k, v in options.items()
                                                if k in ('text', 'fill', 'font')})


class CanvasTile:
    def __init__(self, canvas, x, y, width=44, height=44, label='', color=CELL_BG_DEFAULT,
                 callback=None, kind='cell', enabled=True, eraser=False):
        self.canvas, self.x, self.y, self.width, self.height = canvas, x, y, width, height
        self.label, self.color, self.callback, self.kind = label, color, callback, kind
        self.enabled, self.active, self.eraser = enabled, False, eraser
        self.tag = f'control-{id(self)}'
        self.paint = dict(text=label, bg=color, fg=TEXT_BLACK, font=NUMBER_FONT,
                          highlightbackground='#ffffff')
        self._draw()
        canvas.tag_bind(self.tag, '<Button-1>', self._click)

    def _click(self, event):
        if self.enabled and self.callback:
            self.callback()

    def config(self, **options):
        self.paint.update(options)
        self._draw()

    def set_active(self, active):
        self.active = active
        self._draw()

    def set_state(self, enabled=None, active=None, label=None):
        if enabled is not None:
            self.enabled = enabled
        if active is not None:
            self.active = active
        if label is not None:
            self.label = label
        self._draw()

    def _draw(self):
        c, x, y = self.canvas, self.x, self.y
        c.delete(self.tag)
        is_action = self.kind == 'action'
        color = self.paint['bg']
        border = self.paint['highlightbackground'] if self.kind == 'cell' else (
            SUM_TEXT if self.active else '#ffffff')
        if is_action:
            # Neutral buttons expose the same frosted surface as the panels.
            color = '#31865f' if self.active else ''
            border = '#28724f' if self.active else '#ffffff'
        smooth_rectangle(c, x+1, y+1, x+self.width-1, y+self.height-1,
                          fill=color, outline=border, width=2, tags=self.tag)
        if self.eraser and self.enabled:
            c.create_polygon(x+10, y+25, x+23, y+12, x+33, y+22, x+23, y+32, x+17, y+32,
                             fill='#ffffff', outline=SUM_TEXT, width=2, tags=self.tag)
            c.create_line(x+17, y+18, x+27, y+28, fill=SUM_TEXT, width=2, tags=self.tag)
        else:
            text = self.paint['text'] if self.kind == 'cell' else self.label
            if not self.enabled and not is_action:
                text = '×'
            fg = self.paint['fg']
            if is_action:
                fg = '#a99c93' if not self.enabled else ('#ffffff' if self.active else SUM_TEXT)
            if is_action and draw_action_icon(c, self.label, x+self.width/2, y+self.height/2,
                                              fg, tags=self.tag):
                return
            c.create_text(x+self.width/2, y+self.height/2, text=text, fill=fg,
                          font=('Helvetica', 12, 'bold') if is_action else self.paint['font'],
                          tags=self.tag)


class GlassPlayView(tk.Canvas):
    def __init__(self, owner):
        self.owner = owner
        self.background_visible = True
        self.background_asset = choose_background()
        width = max(520, owner.C*46+100)
        height = 480+owner.R*46
        container = tk.Frame(owner, bg=BG)
        container.pack(fill='both', expand=True)
        super().__init__(container, width=width, height=height, bg=BG, bd=0,
                         highlightthickness=0, yscrollincrement=20)
        self.pack(fill='both', expand=True)
        self._revision = 0
        self._pending = None
        self._closed = False
        self._results = Queue()
        self._photo = None
        self._last_size = None
        self._word_images = load_word_images(self)
        self._result_state = 'idle'
        self._playing_animation = PlayingStatusAnimation(self, RESULT_ICON_SIZE)
        self._poll_id = self.after(100, self._poll)
        self._layout(width, height)
        self.bind('<Configure>', self._on_resize)
        self.bind('<Destroy>', self._destroyed)
        self.bind('<MouseWheel>', self._scroll)
        self.bind('<Button-4>', lambda event: self.yview_scroll(-1, 'units'))
        self.bind('<Button-5>', lambda event: self.yview_scroll(1, 'units'))

    def _scroll(self, event):
        # Aqua reports small trackpad deltas; Windows reports multiples of 120.
        delta = event.delta
        if delta:
            units = int(delta / 120) if abs(delta) >= 120 else (1 if delta > 0 else -1)
            self.yview_scroll(-units, 'units')
        return 'break'

    def show_result(self, state):
        transitioned = state != self._result_state
        if not transitioned:
            return
        self._playing_animation.stop()
        self._result_state = state
        self._draw_result()
        if transitioned and state == 'correct':
            self.owner.sounds.celebrate()

    def restart_playing_animation(self):
        if self._result_state == 'idle':
            self._playing_animation.stop()
            self._draw_result()

    def _draw_result(self):
        self.home_button.set_active(self._result_state == 'correct')
        self.delete('result-icon')
        label = {'idle': 'ResultPlaying', 'correct': 'ResultCorrect', 'incorrect': 'ResultRetry'}.get(self._result_state)
        if label:
            x, y = self._result_center
            if self._result_state == 'idle':
                item = self.create_image(x, y, anchor='center', tags='result-icon')
                self._playing_animation.show(item)
            else:
                draw_action_icon(self, label, x, y, RESULT_COLOR, size=RESULT_ICON_SIZE,
                                 tags='result-icon')

    def _toggle_sound(self):
        self.owner.sounds.set_muted(not self.owner.sounds.muted)
        self.sound_button.set_state(label='SoundOff' if self.owner.sounds.muted else 'SoundOn')

    def _toggle_background(self):
        self.background_visible = not self.background_visible
        self._layout(*self._last_size)
        self.owner.sounds.play()

    def _on_resize(self, event):
        if (event.width, event.height) == self._last_size:
            return
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(100, lambda: self._layout(event.width, event.height))

    def _layout(self, width, height):
        self._pending = None
        self._last_size = width, height
        self._revision += 1
        revision = self._revision
        self.delete('all')
        owner, center = self.owner, width/2
        panels = []
        menu_top = 11
        group_width = 3*TILE_SIZE + 2*8
        action_x = [16+i*52 for i in range(3)] + [width-16-group_width+i*52 for i in range(3)]
        self.action_centers = [x+TILE_SIZE/2 for x in action_x]
        controls = [
            ('Home', owner._on_home),
            ('SoundOff' if owner.sounds.muted else 'SoundOn', self._toggle_sound),
            ('BackgroundOn' if self.background_visible else 'BackgroundOff', self._toggle_background),
            ('Undo', owner._on_undo), ('Lock', owner._on_lock), ('Reset', owner._on_reset),
        ]
        for i, (label, callback) in enumerate(controls):
            x = action_x[i]
            panels.append((round(x), menu_top, TILE_SIZE, TILE_SIZE))
            button = CanvasTile(self, x, menu_top, label=label, callback=callback, kind='action')
            if i == 0:
                self.home_button = button
            elif i == 1:
                self.sound_button = button
            elif i == 2:
                self.background_button = button
            elif i == 3:
                owner.undo_btn = button
            elif i == 4:
                owner.lock_btn = button

        board_width, board_height = owner.C*46+14, owner.R*46+14
        sum_probe = self.create_text(0, 0, text='88', font=SUM_FONT)
        sum_half_height = (self.bbox(sum_probe)[3]-self.bbox(sum_probe)[1])/2
        self.delete(sum_probe)
        result_top = menu_top + 20
        fixed_height = (result_top + RESULT_ICON_SIZE +
                        sum_half_height + 18 + board_height + 194 + 24)
        section_gap = max(12, min(24, round((height-fixed_height)/2)))
        self._result_center = (center, result_top+RESULT_ICON_SIZE/2)
        for photo, x, anchor in zip(self._word_images,
                                    (center-RESULT_ICON_SIZE/2-10, center+RESULT_ICON_SIZE/2+10),
                                    ('e', 'w')):
            self.create_image(x, self._result_center[1], image=photo, anchor=anchor, tags='branding')
        self._draw_result()

        left = round(center-board_width/2)
        # Include the sums in the grid section's visible bounds.
        top = round(result_top + RESULT_ICON_SIZE + section_gap + sum_half_height + 18)
        panels.append((left, top, board_width, board_height))
        owner.cells = []
        for c in range(owner.C):
            self.create_text(left+7+c*46+23, top-18, text=str(owner.puzzle.col_sums[c]),
                             fill=SUM_TEXT, font=SUM_FONT)
        for r in range(owner.R):
            self.create_text(left-18, top+7+r*46+23, text=str(owner.puzzle.row_sums[r]),
                             fill=SUM_TEXT, font=SUM_FONT)
            row = []
            for c in range(owner.C):
                row.append(CanvasTile(self, left+8+c*46, top+8+r*46,
                                      callback=lambda rr=r, cc=c: owner._on_cell_click(rr, cc)))
            owner.cells.append(row)
        bottom = top+board_height
        tools_top = bottom+section_gap
        panels.append((round(center-178), tools_top, 356, 194))
        self.create_text(center, tools_top+10, text='Number Tool', fill=SUM_TEXT,
                         font=TOOL_LABEL_FONT)
        self.create_text(center, tools_top+124, text='Color Tool', fill=SUM_TEXT,
                         font=TOOL_LABEL_FONT)
        owner.num_tool_btns = {}
        for i, n in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]):
            owner.num_tool_btns[n] = CanvasTile(
                self, center-118+(i%5)*48, tools_top+22+(i//5)*48,
                label='' if n == 0 else str(n), callback=lambda nn=n: owner._set_num_tool(nn),
                kind='tool', eraser=n == 0, enabled=n == 0 or n in owner.allowed_numbers)
        owner.col_tool_btns = {}
        for i, code in enumerate(['B', 'R', 'Y', 'V', 'P', 'G', 'CLEAR']):
            owner.col_tool_btns[code] = CanvasTile(
                self, center-166+i*48, tools_top+138,
                callback=lambda cc=code: owner._set_color_tool(cc), kind='tool',
                color=COLOR_HEX.get(code, CELL_BG_DEFAULT), eraser=code == 'CLEAR',
                enabled=code == 'CLEAR' or code in owner.allowed_colors)
        owner.status_label = CanvasLabel(self, self.create_text(
            center, tools_top+208, text='', fill=SUM_TEXT, font=('Helvetica', 12), width=width-60))
        content_height = max(height, tools_top+232)
        self.configure(scrollregion=(0, 0, width, content_height))
        self.section_bounds = ((menu_top, menu_top+TILE_SIZE),
                               (result_top, result_top+RESULT_ICON_SIZE),
                               (top-18-sum_half_height, bottom),
                               (tools_top, tools_top+194))
        owner._render_all()
        owner._update_status()
        owner._update_undo_button()
        owner._update_lock_ui()
        owner._update_tool_highlights()
        asset = self.background_asset if self.background_visible else None
        results = self._results

        def render():
            try:
                with tempfile.TemporaryDirectory(prefix='clusters-glass-', ignore_cleanup_errors=True) as directory:
                    file = render_background(asset, width, content_height, panels, directory)
                    results.put((revision, file.read_bytes(), None))
            except Exception as error:
                results.put((revision, None, error))
        Thread(target=render, daemon=True).start()

    def _poll(self):
        try:
            while True:
                revision, data, error = self._results.get_nowait()
                if revision != self._revision:
                    continue
                if error:
                    print(f'Clusters background unavailable: {error}')
                    continue
                self._photo = tk.PhotoImage(master=self, data=data, format='PPM')
                self.delete('artwork')
                self.create_image(0, 0, image=self._photo, anchor='nw', tags='artwork')
                self.tag_lower('artwork')
        except Empty:
            pass
        if not self._closed:
            self._poll_id = self.after(100, self._poll)

    def _destroyed(self, event):
        if event.widget is self:
            self._closed = True
            self._playing_animation.stop()
            self.after_cancel(self._poll_id)
            if self._pending:
                self.after_cancel(self._pending)
