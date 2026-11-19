"""Manual stop-order planner, per-profile route storage, no fake map distances."""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from core import BUILTIN_RECIPES, REGIONS, calculate_load, display_region


def open_route_planner(app):
    ru = app.config.get('lang') == 'ru'
    win = tk.Toplevel(app.root)
    win.title('Планировщик маршрутов SnowRunner' if ru else 'SnowRunner route planner')
    win.geometry('1060x730')
    win.minsize(830, 620)
    win.configure(bg=app.c('panel'))
    tk.Label(win, text=('Маршруты и рейсы' if ru else 'Routes and cargo runs'),
             bg=app.c('panel'), fg=app.c('accent'), font=(app.ui_font_family(), 19, 'bold')).pack(anchor='w', padx=20, pady=(14, 4))
    tk.Label(win, text=('Ручной порядок остановок. Геометрия дорог, расстояние и время в пути не рассчитываются.' if ru
                 else 'Manual stop order. No road geometry, travel times or distances are calculated.'),
             bg=app.c('panel'), fg=app.c('muted'), font=(app.ui_font_family(), 10)).pack(anchor='w', padx=20)
    main = tk.Frame(win, bg=app.c('panel'))
    main.pack(fill='both', expand=True, padx=20, pady=12)
    left = tk.Frame(main, bg=app.c('panel'))
    right = tk.Frame(main, bg=app.c('panel'))
    left.pack(side='left', fill='both', expand=True, padx=(0, 12))
    right.pack(side='left', fill='both', expand=True)
    tk.Label(left, text=('Сохранённые маршруты' if ru else 'Saved routes'),
             bg=app.c('panel'), fg=app.c('fg')).pack(anchor='w')
    saved = tk.Listbox(left, height=10, exportselection=False, bg=app.c('input'), fg=app.c('fg'),
                       selectbackground=app.c('selection'), font=(app.ui_font_family(), 10))
    saved.pack(fill='both', expand=True, pady=(6, 10))
    tk.Label(right, text=('Остановки (сверху вниз)' if ru else 'Stops (top to bottom)'),
             bg=app.c('panel'), fg=app.c('fg')).pack(anchor='w')
    stops_box = tk.Listbox(right, height=10, exportselection=False, bg=app.c('input'), fg=app.c('fg'),
                           selectbackground=app.c('selection'), font=(app.ui_font_family(), 10))
    stops_box.pack(fill='both', expand=True, pady=(6, 10))
    stop_ids = set(REGIONS)
    stop_ids.update(str(r.get('map')) for r in BUILTIN_RECIPES if r.get('map'))
    try:
        snap = app.profiles.read(app.active_profile_key).get('game_snapshot') or {}
        stop_ids.update((snap.get('visited_levels') or {}).get('items') or [])
    except (OSError, ValueError):
        pass
    selected_stop = tk.StringVar()
    stop_choices = sorted(stop_ids)
    custom = ttk.Combobox(right, values=stop_choices, textvariable=selected_stop)
    custom.pack(fill='x', pady=(0, 8))
    stops = []
    saved_load = []
    selected_route = None
    routes = []
    details = tk.Label(win, bg=app.c('panel'), fg=app.c('muted'), justify='left',
                       font=(app.ui_font_family(), 10), text='')
    details.pack(fill='x', padx=20, pady=(4, 8))
    notes = tk.Entry(win, bg=app.c('input'), fg=app.c('fg'), insertbackground=app.c('fg'),
                     font=(app.ui_font_family(), 10))
    notes.pack(fill='x', padx=20, ipady=6, pady=(0, 12))

    def update_stops():
        stops_box.delete(0, tk.END)
        for i, stop in enumerate(stops):
            visited = stop in ((snap.get('visited_levels') or {}).get('items') or [])
            shown = display_region(stop, app.config['lang'])
            label = shown if shown != ('Карта не определена' if ru else 'Unknown map') else stop
            stops_box.insert(tk.END, f'{i+1}. {label}' + (' ✓' if visited else ''))
        try:
            slots = calculate_load(saved_load) if saved_load else 0
        except ValueError:
            slots = '?'
        details.config(text=(f'Профиль: {app.active_profile_key} • остановок: {len(stops)} • слотов сохранённого груза: {slots}'
                             if ru else f'Profile: {app.active_profile_key} • stops: {len(stops)} • stored cargo slots: {slots}'))

    def reload_routes():
        nonlocal routes
        routes = app.profiles.list_routes(app.active_profile_key)
        saved.delete(0, tk.END)
        for item in routes:
            saved.insert(tk.END, f'{item["name"]} ({len(item["stops"])} остановок)' if ru
                         else f'{item["name"]} ({len(item["stops"])} stops)')
        update_stops()

    def on_route_select(_=None):
        nonlocal stops, saved_load, selected_route
        idx = saved.curselection()
        if not idx:
            return
        selected_route = routes[idx[0]]
        stops = list(selected_route['stops'])
        saved_load = [tuple(x) for x in selected_route['load']]
        notes.delete(0, tk.END)
        notes.insert(0, selected_route['notes'])
        update_stops()

    def add_stop():
        value = selected_stop.get().strip()
        if not value or len(value) > 120 or any(ord(c) < 32 for c in value):
            messagebox.showerror(win.title(), 'Некорректное название остановки.' if ru else 'Invalid stop name.', parent=win)
            return
        if len(stops) < 40:
            stops.append(value)
            update_stops()

    def remove_stop():
        selection = stops_box.curselection()
        if selection:
            stops.pop(selection[0])
            update_stops()

    def move_stop(offset):
        selection = stops_box.curselection()
        if not selection:
            return
        i = selection[0]
        j = i + offset
        if 0 <= j < len(stops):
            stops[i], stops[j] = stops[j], stops[i]
            update_stops()
            stops_box.selection_set(j)

    def new_route():
        nonlocal selected_route, stops, saved_load
        selected_route = None
        stops = []
        saved_load = list(app.load)
        notes.delete(0, tk.END)
        saved.selection_clear(0, tk.END)
        update_stops()

    def store_route(overwrite=False):
        nonlocal selected_route, saved_load
        route_id = selected_route['id'] if overwrite and selected_route else None
        name = selected_route['name'] if route_id else simpledialog.askstring(
            win.title(), 'Название маршрута:' if ru else 'Route name:', parent=win)
        if name is None:
            return
        try:
            # The route captures the current cargo manifest at save time.
            stored = app.profiles.save_route(app.active_profile_key, name, stops, list(app.load),
                     route_id=route_id, notes=notes.get())
            selected_route = stored
            saved_load = [tuple(x) for x in stored['load']]
            reload_routes()
        except (OSError, ValueError) as exc:
            messagebox.showerror(win.title(), str(exc), parent=win)

    def delete_route():
        nonlocal selected_route, stops, saved_load
        if selected_route and messagebox.askyesno(win.title(),
                 'Удалить выбранный маршрут?' if ru else 'Delete the selected route?', parent=win):
            app.profiles.delete_route(app.active_profile_key, selected_route['id'])
            selected_route = None
            stops, saved_load = [], []
            reload_routes()

    def apply_load():
        if not selected_route:
            return
        if not messagebox.askyesno(win.title(),
            'Загрузить грузы этого маршрута в калькулятор? Текущий план останется в истории.' if ru
            else 'Restore this route cargo to calculator? Current load is saved in history.', parent=win):
            return
        try:
            app._save_profile_draft(force=True)
            app.profiles.save_draft(app.active_profile_key, saved_load)
            app.load = list(saved_load)
            app._draft_saved_load = list(saved_load)
            app.render()
        except (OSError, ValueError) as exc:
            messagebox.showerror(win.title(), str(exc), parent=win)

    buttons_left = tk.Frame(left, bg=app.c('panel'))
    buttons_left.pack(fill='x')
    for title, cmd in [(('Новый' if ru else 'New'), new_route),
                       (('Сохранить' if ru else 'Save as'), lambda: store_route(False)),
                       (('Обновить' if ru else 'Update'), lambda: store_route(True)),
                       (('Удалить' if ru else 'Delete'), delete_route)]:
        app.btn(buttons_left, title, cmd).pack(side='left', padx=(0, 5))
    buttons_right = tk.Frame(right, bg=app.c('panel'))
    buttons_right.pack(fill='x')
    for title, cmd in [(('Добавить' if ru else 'Add'), add_stop),
                       (('Убрать' if ru else 'Remove'), remove_stop),
                       ('↑', lambda: move_stop(-1)), ('↓', lambda: move_stop(1))]:
        app.btn(buttons_right, title, cmd).pack(side='left', padx=(0, 5))
    bottom = tk.Frame(win, bg=app.c('panel'))
    bottom.pack(fill='x', padx=20, pady=(0, 15))
    app.btn(bottom, 'Грузы в калькулятор' if ru else 'Restore cargo to calculator', apply_load).pack(side='left')
    tk.Label(bottom, text=('Нет автоматической прокладки дороги.' if ru else 'No automatic road routing.'),
             bg=app.c('panel'), fg=app.c('muted'), font=(app.ui_font_family(), 9)).pack(side='left', padx=10)
    saved.bind('<<ListboxSelect>>', on_route_select)
    new_route()
    reload_routes()
    win.lift()
    return win
