"""Keyboard capture improvement for the existing Windows RegisterHotKey overlay.

RegisterHotKey already handles Ctrl+Shift+F9 globally in ordinary desktop / borderless
Windows.  This patch avoids dropping one or more modifiers when Windows/Tk reports
incomplete event.state during editor capture; it never steals keys or injects into games.
"""
from __future__ import annotations
import os


def pressed_modifiers(event, get_pressed=None):
    state=int(getattr(event,'state',0) or 0)
    found={'Ctrl':bool(state & 0x0004), 'Shift':bool(state & 0x0001),
           'Alt':bool(state & 0x0008), 'Win':bool(state & 0x0040)}
    if get_pressed is not None:
        keys={'Ctrl':(0xA2,0xA3,0x11),'Shift':(0xA0,0xA1,0x10),
              'Alt':(0xA4,0xA5,0x12),'Win':(0x5B,0x5C)}
        for name,variants in keys.items():
            try:
                if any(get_pressed(k) for k in variants):found[name]=True
            except (OSError,ValueError,TypeError):pass
    return [key for key in ('Ctrl','Shift','Alt','Win') if found[key]]


def capture_combination(event, get_pressed=None):
    import craft_overlay
    sym=str(getattr(event,'keysym','')).upper()
    if sym in ('CONTROL_L','CONTROL_R','SHIFT_L','SHIFT_R','ALT_L','ALT_R',
               'SUPER_L','SUPER_R','WIN_L','WIN_R','META_L','META_R'):
        return None
    if sym.startswith('F') and sym[1:].isdigit() and 1<=int(sym[1:])<=12:
        main=sym
    elif len(sym)==1 and sym in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
        main=sym
    else:return None
    mods=pressed_modifiers(event,get_pressed)
    if not mods:return None
    combination='+'.join(mods+[main])
    try: craft_overlay.parse_hotkey(combination)
    except ValueError:return None
    return combination


def install_hotkey_improvement():
    import craft_overlay
    if getattr(craft_overlay,'_v316_multimod_installed',False):return
    def enhanced(event):
        check=None
        if os.name=='nt':
            from ctypes import windll
            check=lambda k:bool(windll.user32.GetAsyncKeyState(k)&0x8000)
        return capture_combination(event, check)
    craft_overlay.event_hotkey=enhanced
    # The editor resolves the event_hotkey module global when invoked, so no
    # invasive replacement of CraftOverlay or WindowsHotkey is needed.
    craft_overlay._v316_multimod_installed=True
