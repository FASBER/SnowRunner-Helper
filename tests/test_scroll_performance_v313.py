"""Regression coverage for low-latency mouse-wheel handling in v0.31.13."""
import unittest
from types import SimpleNamespace
from pathlib import Path

from scroll_performance_v313 import install_scroll_performance, _FRAME_MS


class MockRoot:
    def __init__(self):
        self.callbacks = []
        self.bindings = {}
    def after(self, delay, fn):
        self.callbacks.append((delay,fn))
        return len(self.callbacks)
    def bind(self, event, fn):
        self.bindings[event] = fn
    def fire(self):
        pending = self.callbacks[:]
        self.callbacks.clear()
        for _,cb in pending:cb()


def screen(reference_ui=True):
    class Screen:
        def __init__(self):
            self.reference_ui=reference_ui
            self.page='cargo'
            self.root=MockRoot()
            self.canvas=SimpleNamespace(winfo_exists=lambda: True)
            self.scroll_history=[]
            self.load_history=[]
            self.zoom_history=[]
            self.draws=0
        def onwheel(self,event):
            if getattr(event,'state',0)&4:
                self.zoom_history.append(event.delta)
                return 'break'
            if getattr(event,'part','list')=='load':
                self.scroll_load(-2 if event.delta>0 else 2)
            else:
                self.scroll(-2 if event.delta>0 else 2)
            return 'break'
        def scroll(self,amount):
            self.scroll_history.append(amount)
            self.redraw()
        def scroll_load(self,amount):
            self.load_history.append(amount)
            self.redraw()
        def redraw(self):
            self.draws+=1

    install_scroll_performance(Screen)
    return Screen()

class ScrollPerformanceTests(unittest.TestCase):
    def test_burst_of_40_ticks_renders_once_instead_of_40_times(self):
        app=screen()
        app.redraw()  # installs real root bindings after lazy UI adapter
        for i in range(40):
            result=app.onwheel(SimpleNamespace(delta=-120,state=0))
            self.assertEqual(result,'break')
        self.assertEqual(app.scroll_history,[])
        self.assertEqual(len(app.root.callbacks),1)
        self.assertEqual(app.root.callbacks[0][0],_FRAME_MS)
        app.root.fire()
        self.assertEqual(app.scroll_history,[80])
        self.assertEqual(app.draws,2)  # initial + a single batched frame

    def test_direct_scrollbar_click_is_immediate(self):
        app=screen()
        app.scroll(7)
        self.assertEqual(app.scroll_history,[7])
        self.assertEqual(app.draws,1)
        self.assertEqual(app.root.callbacks,[])

    def test_load_panel_uses_the_correct_scroller(self):
        app=screen()
        for _ in range(6):
            app.onwheel(SimpleNamespace(delta=-120,state=0,part='load'))
        app.root.fire()
        self.assertEqual(app.load_history,[12])
        self.assertEqual(app.scroll_history,[])

    def test_ctrl_wheel_zoom_is_immediate(self):
        app=screen()
        self.assertEqual(app.onwheel(SimpleNamespace(delta=120,state=4)), 'break')
        self.assertEqual(app.zoom_history,[120])
        self.assertEqual(app.root.callbacks,[])

    def test_classic_ui_stays_unmodified(self):
        app=screen(reference_ui=False)
        for _ in range(3):app.onwheel(SimpleNamespace(delta=-120,state=0))
        self.assertEqual(app.scroll_history,[2,2,2])
        self.assertEqual(app.draws,3)
        self.assertFalse(app.root.bindings)

    def test_switching_tab_discards_stale_wheel_events(self):
        app=screen()
        app.onwheel(SimpleNamespace(delta=-120,state=0))
        app.page='settings'
        app.root.fire()
        self.assertEqual(app.scroll_history,[])

    def test_opposite_wheel_directions_cancel_without_redraw(self):
        app=screen()
        app.onwheel(SimpleNamespace(delta=-120,state=0))
        app.onwheel(SimpleNamespace(delta=120,state=0))
        app.root.fire()
        self.assertEqual(app.scroll_history,[])
        self.assertEqual(app.draws,0)

    def test_rebinds_three_native_wheel_events_only_once(self):
        app=screen()
        app.redraw()
        app.redraw()
        self.assertEqual(set(app.root.bindings),{'<MouseWheel>','<Button-4>','<Button-5>'})
        self.assertEqual(len(app.root.bindings),3)
        self.assertIs(app.root.bindings['<MouseWheel>'].__self__,app)

    def test_multiple_frame_windows_process_independently(self):
        app=screen()
        for _ in range(4):app.onwheel(SimpleNamespace(delta=-120,state=0))
        app.root.fire()
        for _ in range(3):app.onwheel(SimpleNamespace(delta=120,state=0))
        app.root.fire()
        self.assertEqual(app.scroll_history,[8,-6])
        self.assertEqual(app.draws,2)

    def test_mixed_regions_do_not_lose_any_wheel_steps(self):
        app=screen()
        app.onwheel(SimpleNamespace(delta=-120,state=0,part='list'))
        app.onwheel(SimpleNamespace(delta=120,state=0,part='load'))
        app.root.fire()
        self.assertEqual(app.scroll_history,[2])
        self.assertEqual(app.load_history,[-2])

    def test_source_is_wired_after_existing_workspace_transform(self):
        code=(Path(__file__).resolve().parents[1]/'ui_repair_v312.py').read_text(encoding='utf8')
        self.assertIn('install_scroll_performance(cls)',code)
        self.assertLess(code.index('cls.onwheel=_wheel(cls.onwheel)'),code.index('install_scroll_performance(cls)'))


if __name__=='__main__':unittest.main()

class EditorScrollTests(unittest.TestCase):
    def editor(self):
        from scroll_performance_v313 import install_editor_wheel
        class Editor:
            def __init__(self):
                self.bindings = {}
                self.content_canvas = SimpleNamespace(
                    winfo_rootx=lambda: 100, winfo_rooty=lambda: 100,
                    winfo_width=lambda: 300, winfo_height=lambda: 400,
                    calls=[], binds={})
                self.content_canvas.bind=lambda key,fn:self.content_canvas.binds.__setitem__(key,fn)
                self.content_canvas.yview_scroll=lambda n,units:self.content_canvas.calls.append((n,units))
            def bind(self,event,fn):self.bindings[event]=fn
        install_editor_wheel(Editor)
        return Editor()

    def test_editor_wheel_on_child_controls_scrolls_three_units_immediately(self):
        editor=self.editor()
        handler=editor.bindings['<MouseWheel>']
        self.assertEqual(handler(SimpleNamespace(x_root=130,y_root=180,delta=-120)), 'break')
        self.assertEqual(editor.content_canvas.calls,[(3,'units')])
        self.assertEqual(handler(SimpleNamespace(x_root=130,y_root=180,delta=120)), 'break')
        self.assertEqual(editor.content_canvas.calls[-1],(-3,'units'))

    def test_editor_preview_area_does_not_scroll_setting_list(self):
        editor=self.editor()
        self.assertIsNone(editor.bindings['<MouseWheel>'](
            SimpleNamespace(x_root=650,y_root=220,delta=-120)))
        self.assertEqual(editor.content_canvas.calls,[])

    def test_editor_canvas_mousewheel_does_not_bubble_to_toplevel(self):
        editor=self.editor()
        handler=editor.content_canvas.binds['<MouseWheel>']
        self.assertEqual(handler(SimpleNamespace(x_root=150,y_root=200,delta=-120)), 'break')
        self.assertEqual(editor.content_canvas.calls,[(3,'units')])

    def test_editor_linux_button4_button5_supported(self):
        editor=self.editor()
        for btn in (4,5):
            self.assertEqual(editor.bindings['<Button-'+str(btn)+'>'](
                SimpleNamespace(x_root=125,y_root=140,num=btn,delta=0)), 'break')
        self.assertEqual(editor.content_canvas.calls,[(-3,'units'),(3,'units')])
