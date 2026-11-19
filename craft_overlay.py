"""Compact, optional crafting reference window with a configurable Windows global hotkey.

Does not modify game files or inject into the game.  RegisterHotKey works while
another *windowed or borderless* application has focus; exclusive full-screen
applications can hide ordinary topmost windows.
"""
from __future__ import annotations

import ctypes
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from ctypes import wintypes

from core import (BUILTIN_RECIPES, display_cargo, display_recipe_location,
                  text_value, save_json, SETTINGS_FILE)

DEFAULT_HOTKEY = 'Ctrl+Shift+F9'
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x0008, 0x4000
WM_HOTKEY, WM_QUIT, WM_USER, PM_NOREMOVE = 0x0312, 0x0012, 0x0400, 0x0000


def parse_hotkey(text: str) -> tuple[int, int]:
    """Validate user shortcuts. Require a modifier to avoid capturing game controls."""
    tokens = [s.strip().upper() for s in str(text).replace('CONTROL', 'CTRL').split('+') if s.strip()]
    mods = 0
    key = None
    for token in tokens:
        if token == 'CTRL': mods |= MOD_CONTROL
        elif token == 'SHIFT': mods |= MOD_SHIFT
        elif token == 'ALT': mods |= MOD_ALT
        elif token == 'WIN': mods |= MOD_WIN
        elif token.startswith('F') and token[1:].isdigit() and 1 <= int(token[1:]) <= 12:
            if key is not None: raise ValueError('Only one main key is allowed')
            key = 0x70 + int(token[1:]) - 1
        elif len(token) == 1 and token in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
            if key is not None: raise ValueError('Only one main key is allowed')
            key = ord(token)
        else:
            raise ValueError('Unsupported key: ' + token)
    if not mods or key is None:
        raise ValueError('Choose a modifier (Ctrl / Alt / Shift / Win) and a key')
    if len(tokens) != sum(bool(mods & bit) for bit in (MOD_ALT,MOD_CONTROL,MOD_SHIFT,MOD_WIN)) + 1:
        raise ValueError('Invalid shortcut')
    return mods | MOD_NOREPEAT, key


def event_hotkey(event) -> str | None:
    """Convert a Tk keyboard event captured in the shortcut editor."""
    keysym = event.keysym.upper()
    if keysym in ('CONTROL_L','CONTROL_R','SHIFT_L','SHIFT_R','ALT_L','ALT_R','SUPER_L','SUPER_R'):
        return None
    mods = []
    if event.state & 0x0004: mods.append('Ctrl')
    if event.state & 0x0001: mods.append('Shift')
    # Alt state varies across Tk builds; Windows sets Mod1 = 0x0008.
    if event.state & 0x0008: mods.append('Alt')
    if not mods: return None
    if keysym.startswith('F') and keysym[1:].isdigit(): key = keysym
    elif len(keysym)==1 and keysym.isascii() and keysym.isalnum(): key = keysym
    else: return None
    result = '+'.join(mods + [key])
    try: parse_hotkey(result)
    except ValueError: return None
    return result


class WindowsHotkey:
    """Own the Windows hotkey/message queue in a dedicated thread.

    The Tk thread consumes events from a Queue; no Tk methods run in this thread.
    """
    def __init__(self, shortcut: str, events: queue.Queue):
        self.shortcut = shortcut
        self.events = events
        self._thread_id = None
        self._ready = threading.Event()
        self._thread = None
        self.registered = False
        self.failure = None

    def start(self):
        if os.name != 'nt': return
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name='SnowRunnerOverlayHotkey')
        self._thread.start()
        if not self._ready.wait(timeout=3):
            raise RuntimeError('Не удалось запустить обработчик горячей клавиши')
        if not self.registered:
            raise RuntimeError(self.failure or 'Сочетание клавиш недоступно')

    def close(self):
        if os.name != 'nt': return
        tid = self._thread_id
        if tid:
            ctypes.windll.user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
        self._thread_id = None
        if self._thread and self._thread.is_alive() and threading.current_thread()!=self._thread:
            self._thread.join(timeout=1)

    def _run(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, WM_USER, WM_USER, PM_NOREMOVE)
        try: mods, key = parse_hotkey(self.shortcut)
        except ValueError as exc:
            self.failure=str(exc)
            self.events.put(('error', self.failure))
            self._ready.set()
            return
        ok = user32.RegisterHotKey(None, 0xCA65, mods, key)
        self.registered=bool(ok)
        if not ok:
            self.failure='Горячая клавиша занята другим приложением. Выбери другую.'
            self.events.put(('error',self.failure))
        self._ready.set()
        if not ok:return
        self.events.put(('ready', self.shortcut))
        try:
            while True:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0: break
                if msg.message == WM_HOTKEY and msg.wParam == 0xCA65:
                    self.events.put(('toggle', None))
        finally:
            user32.UnregisterHotKey(None, 0xCA65)


class CraftOverlay:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.window = None
        self.search_var = tk.StringVar(master=self.root)
        self.rows = []
        self.shortcut = str(app.config.get('overlay_hotkey') or DEFAULT_HOTKEY)
        try: parse_hotkey(self.shortcut)
        except ValueError: self.shortcut = DEFAULT_HOTKEY
        self.events = queue.Queue()
        self.listener = None
        self.error = ''
        self._poll_id = None
        try:self.set_hotkey(self.shortcut, persist=False)
        except RuntimeError as exc:
            # A conflicting global shortcut must not prevent the whole app
            # from launching. It can be reassigned from Settings.
            self.error=str(exc)
        self._poll()
        self.root.bind('<Destroy>', self._on_root_destroy, add='+')

    def _on_root_destroy(self, event):
        if event.widget == self.root:
            self.shutdown()

    def shutdown(self):
        if self._poll_id is not None:
            try: self.root.after_cancel(self._poll_id)
            except tk.TclError: pass
            self._poll_id = None
        if self.listener:
            self.listener.close()
            self.listener = None

    def _poll(self):
        try:
            while True:
                msg, value = self.events.get_nowait()
                if msg == 'toggle': self.toggle()
                elif msg == 'error': self.error = value
                elif msg == 'ready': self.error = ''
        except queue.Empty: pass
        try:
            if self.root.winfo_exists(): self._poll_id = self.root.after(90, self._poll)
        except tk.TclError: return

    def set_hotkey(self, shortcut, persist=True):
        parse_hotkey(shortcut)
        previous=self.shortcut
        if self.listener:self.listener.close()
        new_listener=WindowsHotkey(shortcut,self.events)
        try:new_listener.start()
        except RuntimeError:
            # Reject collisions without leaving the former working key lost.
            if previous != shortcut:
                restored=WindowsHotkey(previous,self.events)
                try:restored.start();self.listener=restored
                except RuntimeError:self.listener=None
            raise
        self.shortcut=shortcut
        self.listener=new_listener
        if persist:
            self.app.config['overlay_hotkey']=shortcut
            save_json(SETTINGS_FILE,self.app.config)

    def is_visible(self):
        return self.window is not None and self.window.winfo_exists() and self.window.state() != 'withdrawn'

    def toggle(self):
        if self.is_visible():
            self.window.withdraw()
            return
        if not self.window or not self.window.winfo_exists(): self._create()
        self.refresh()
        self.window.deiconify()
        self.window.attributes('-topmost', True)
        self.window.lift()
        try: self.search_entry.focus_set()
        except tk.TclError: pass

    def _create(self):
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.title('SnowRunner — Craft Overlay')
        self.window.configure(bg='#11191D')
        self.window.geometry(self.app.config.get('overlay_geometry','440x535+80+100'))
        self.window.minsize(340,400)
        self.window.attributes('-topmost', True)
        self.window.protocol('WM_DELETE_WINDOW',self.window.withdraw)
        outer = tk.Frame(self.window,bg='#11191D',padx=12,pady=10)
        outer.pack(fill='both',expand=True)
        header = tk.Frame(outer,bg='#11191D')
        header.pack(fill='x')
        title = tk.Label(header,text='⚒  КРАФТ / CRAFT',bg='#11191D',fg='#FFC21B',font=('Segoe UI',15,'bold'))
        title.pack(side='left')
        tk.Button(header,text='✕',command=self.window.withdraw,relief='flat',bd=0,
                  bg='#273137',fg='white',activebackground='#8C3434',cursor='hand2',padx=9).pack(side='right')
        tk.Label(outer,text='Рецепты из игровых файлов и мои рецепты' if self.app.config['lang']=='ru' else 'Game crafting recipes and my recipes',
                 bg='#11191D',fg='#B9C3C7',font=('Segoe UI',9)).pack(anchor='w',pady=(5,9))
        self.search_entry = tk.Entry(outer,textvariable=self.search_var,fg='white',bg='#273137',
                                     insertbackground='#FFC21B',relief='flat',font=('Segoe UI',11))
        self.search_entry.pack(fill='x',ipady=7,pady=(0,8))
        self.search_var.trace_add('write',lambda *_:self.refresh())
        list_frame=tk.Frame(outer,bg='#11191D')
        list_frame.pack(fill='both',expand=True)
        self.listbox=tk.Listbox(list_frame, bg='#222B31',fg='#EAEFF2',selectbackground='#71581C',
                                selectforeground='#FFF4D6',bd=0,highlightthickness=0,
                                activestyle='none',font=('Segoe UI',10),exportselection=False)
        sc=tk.Scrollbar(list_frame,command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sc.set)
        sc.pack(side='right',fill='y')
        self.listbox.pack(side='left',fill='both',expand=True)
        self.listbox.bind('<<ListboxSelect>>',lambda e:self.select())
        self.details=tk.Text(outer,height=9,wrap='word',bg='#1D272D',fg='#F4F4F2',
                             relief='flat',font=('Segoe UI',10),padx=10,pady=9,bd=0)
        self.details.pack(fill='x',pady=(9,0))
        self.details.configure(state='disabled')
        self.window.bind('<Escape>',lambda e:self.window.withdraw())
        self.window.bind('<Configure>',self._remember_window_geometry)

    def _remember_window_geometry(self, event):
        if event.widget is self.window and self.window.state()!='withdrawn':
            geometry=self.window.geometry()
            if geometry != self.app.config.get('overlay_geometry'):
                self.app.config['overlay_geometry'] = geometry
                # Deliberately defer filesystem write until close or explicit settings change.

    def refresh(self):
        if not self.window or not self.window.winfo_exists(): return
        term = self.search_var.get().strip().casefold()
        lang = self.app.config['lang']
        rows = BUILTIN_RECIPES + self.app.official + self.app.custom
        self.rows = [r for r in rows if term in (text_value(r.get('name'),lang)+' '+
                     display_recipe_location(r,lang)+' '+' '.join(display_cargo(c,lang) for c in r.get('inputs',{}))+' '+
                     ' '.join(display_cargo(c,lang) for c in r.get('outputs',{}))).casefold()]
        self.listbox.delete(0,'end')
        for rec in self.rows:
            name = text_value(rec.get('name'),lang) or ', '.join(display_cargo(c,lang) for c in rec.get('outputs',{}))
            self.listbox.insert('end',name[:65])
        if self.rows:
            self.listbox.selection_set(0)
            self.select()
        else:self._set_details('Рецепты не найдены' if lang=='ru' else 'No matching recipes')

    def select(self):
        selection=self.listbox.curselection()
        if not selection or not self.rows:return
        rec=self.rows[selection[0]]
        lang=self.app.config['lang']
        lines=[text_value(rec.get('name'),lang),display_recipe_location(rec,lang),'']
        lines.append('НУЖНО:' if lang=='ru' else 'INPUT:')
        if not rec.get('inputs'):
            lines.append('  Генератор / Generator' if rec.get('generator') else '  —')
        for cid,qty in rec.get('inputs',{}).items(): lines.append('  • '+display_cargo(cid,lang)+f' ×{qty}')
        if rec.get('energy'):
            lines.append(('  Энергия: ' if lang=='ru' else '  Energy: ')+str(rec['energy']))
        lines.extend(['','ПОЛУЧИТСЯ:' if lang=='ru' else 'OUTPUT:'])
        for cid,qty in rec.get('outputs',{}).items(): lines.append('  • '+display_cargo(cid,lang)+f' ×{qty}')
        self._set_details('\n'.join(lines))

    def _set_details(self,text):
        self.details.configure(state='normal')
        self.details.delete('1.0','end')
        self.details.insert('1.0',text)
        self.details.configure(state='disabled')

    def shortcut_dialog(self):
        dialog=tk.Toplevel(self.root)
        dialog.title('Горячая клавиша мини-крафта')
        dialog.geometry('480x210')
        dialog.configure(bg='#171E22')
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(dialog,text='Нажми сочетание, например Ctrl+Shift+F9',bg='#171E22',fg='#E9EDF1',font=('Segoe UI',12)).pack(pady=(22,8))
        text=tk.StringVar(value=self.shortcut)
        field=tk.Entry(dialog,textvariable=text,justify='center',font=('Segoe UI',15),bg='#273137',fg='white',insertbackground='white')
        field.pack(fill='x',padx=35,ipady=5)
        def capture(e):
            choice=event_hotkey(e)
            if choice:
                text.set(choice)
                return 'break'
            # Allow manually typing shortcuts such as Win+F10.
            return None
        field.bind('<KeyPress>',capture)
        tk.Label(dialog,text='В игре используй оконный или безрамочный режим.',bg='#171E22',fg='#B9C3C7').pack(pady=7)
        def save():
            try:self.set_hotkey(text.get())
            except (ValueError,RuntimeError) as exc:
                messagebox.showerror('Shortcut',str(exc),parent=dialog)
                return
            save_json(SETTINGS_FILE,self.app.config)
            dialog.destroy()
            if self.app.game:self.app.game.redraw()
            if self.error:
                messagebox.showwarning('Hotkey', self.error, parent=self.root)
        tk.Button(dialog,text='Сохранить / Save',command=save,bg='#FFC21B',fg='#11191D',relief='flat').pack(pady=4)
        field.focus_set()
