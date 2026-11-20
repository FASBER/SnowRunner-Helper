"""Responsive mouse-wheel scrolling for the approved SnowRunner UI.

SnowRunner's Canvas rebuilds the complete screen on every ``scroll`` call.
Windows can deliver many mouse-wheel messages in a single motion, which used
 to queue many expensive redraws. We accumulate only wheel-generated deltas
for a short display frame and redraw once. Direct clicks, scrollbar dragging,
Ctrl+wheel zoom, classic UI and other app callbacks stay synchronous.
"""
from __future__ import annotations

from tkinter import TclError

_FRAME_MS = 12
_MAX_ACCUMULATED_STEPS = 240
_MISSING = object()


def install_scroll_performance(cls):
    """Install once on a GameScreen class after v0.31.12 workspace hooks."""
    if getattr(cls, '_wheel_perf_v313_installed', False):
        return

    previous_wheel = cls.onwheel
    previous_redraw = cls.redraw

    def bind_wheel_if_needed(self):
        # The approved-UI adapter is installed *during* the first redraw.
        # Root.bind() ran earlier, capturing the old bound handler. Rebind once
        # after installation or the accelerated callback will never be called.
        if not getattr(self, 'reference_ui', False):
            return
        if getattr(self, '_wheel_perf_v313_bound', False):
            return
        try:
            self.root.bind('<MouseWheel>', self.onwheel)
            self.root.bind('<Button-4>', self.onwheel)
            self.root.bind('<Button-5>', self.onwheel)
        except (TclError, AttributeError):
            return
        self._wheel_perf_v313_bound = True

    def redraw(self, *args, **kwargs):
        bind_wheel_if_needed(self)
        return previous_redraw(self, *args, **kwargs)

    def onwheel(self, event):
        if not getattr(self, 'reference_ui', False) or getattr(event, 'state', 0) & 0x0004:
            return previous_wheel(self, event)

        wheel_calls = []
        prev_list = self.__dict__.get('scroll', _MISSING)
        prev_load = self.__dict__.get('scroll_load', _MISSING)
        self.scroll = lambda amount: wheel_calls.append(('list', int(amount)))
        self.scroll_load = lambda amount: wheel_calls.append(('load', int(amount)))
        try:
            result = previous_wheel(self, event)
        finally:
            if prev_list is _MISSING:
                self.__dict__.pop('scroll', None)
            else:
                self.scroll = prev_list
            if prev_load is _MISSING:
                self.__dict__.pop('scroll_load', None)
            else:
                self.scroll_load = prev_load

        if not wheel_calls:
            return result

        state = getattr(self, '_wheel_perf_v313_state', None)
        if state is None:
            state = {'page': self.page, 'list': 0, 'load': 0, 'pending': False}
            self._wheel_perf_v313_state = state
        if state['page'] != self.page:
            state.update(page=self.page, list=0, load=0)
        for kind, amount in wheel_calls:
            state[kind] = max(-_MAX_ACCUMULATED_STEPS,
                              min(_MAX_ACCUMULATED_STEPS, state[kind] + amount))

        if not state['pending']:
            state['pending'] = True
            def flush():
                state['pending'] = False
                amounts = (state['list'], state['load'])
                page = state['page']
                state['list'] = state['load'] = 0
                if page != self.page:
                    return
                try:
                    if hasattr(self, 'canvas') and not self.canvas.winfo_exists():
                        return
                    if amounts[0]:
                        self.scroll(amounts[0])
                    if amounts[1]:
                        self.scroll_load(amounts[1])
                except (TclError, AttributeError):
                    # A closing window can invalidate a scheduled callback.
                    return
            try:
                self.root.after(_FRAME_MS, flush)
            except (TclError, AttributeError):
                state['pending'] = False
                state['list'] = state['load'] = 0
        return result

    cls.onwheel = onwheel
    cls.redraw = redraw
    cls._wheel_perf_v313_installed = True


def install_editor_wheel(cls):
    """Scroll AppearanceEditor controls without delayed full UI redraws.

    Tk dispatches wheel messages to the child beneath the pointer; previously
    only the empty settings Canvas had a wheel binding. Bind the editor's
    toplevel (for controls) and its Canvas (for empty areas), and restrict the
    event to the settings column so the preview is never accidentally scrolled.
    """
    if getattr(cls, '_wheel_editor_v313_installed', False):
        return
    original_init = cls.__init__

    def wheel_editor(self, event):
        try:
            canvas = self.content_canvas
            left = canvas.winfo_rootx()
            top = canvas.winfo_rooty()
            x = getattr(event, 'x_root', None)
            y = getattr(event, 'y_root', None)
            if x is None or y is None or not (left <= x < left + canvas.winfo_width() and
                                              top <= y < top + canvas.winfo_height()):
                return None
            button = getattr(event, 'num', None)
            if button not in (4, 5) and not getattr(event, 'delta', 0):
                return None
            up = button == 4 or (button != 5 and getattr(event, 'delta', 0) > 0)
            canvas.yview_scroll(-3 if up else 3, 'units')
            return 'break'
        except (TclError, AttributeError):
            return None

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.content_canvas.bind('<MouseWheel>', self._wheel_editor_v313)
        self.content_canvas.bind('<Button-4>', self._wheel_editor_v313)
        self.content_canvas.bind('<Button-5>', self._wheel_editor_v313)
        self.bind('<MouseWheel>', self._wheel_editor_v313)
        self.bind('<Button-4>', self._wheel_editor_v313)
        self.bind('<Button-5>', self._wheel_editor_v313)

    cls.__init__ = init
    cls._wheel_editor_v313 = wheel_editor
    cls._wheel_editor_v313_installed = True
