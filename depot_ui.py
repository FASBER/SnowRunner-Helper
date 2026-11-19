"""Manual cargo-ID matching and read-only warehouse estimate.

No stock depletion, game-file writes or automatic cargo-ID guesses.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, ttk
from core import CARGO, display_cargo
from warehouse_planning import preview_warehouse


def open_depot_preview(app):
    ru = app.config.get('lang') == 'ru'
    if app.active_profile_key == 'local':
        messagebox.showinfo('SnowRunner', 'Выбери игровое сохранение.' if ru else 'Select a game save.', parent=app.root)
        return None
    snap = app.profiles.read(app.active_profile_key).get('game_snapshot') or {}
    depots = snap.get('cargo_depots', {}).get('candidates', [])
    if not depots:
        messagebox.showinfo('SnowRunner', ('В сохранении не найдены предварительные данные складов.' if ru
                   else 'No candidate warehouse data found in this save.'), parent=app.root)
        return None
    win = tk.Toplevel(app.root)
    win.title('Склады — предварительные данные' if ru else 'Warehouses — estimates')
    win.geometry('940x740')
    win.minsize(750, 580)
    win.configure(bg=app.c('panel'))
    tk.Label(win, text=('Склады: предварительный расчёт' if ru else 'Warehouse estimates'),
             bg=app.c('panel'), fg=app.c('accent'), font=(app.ui_font_family(), 18, 'bold')).pack(anchor='w', padx=20, pady=(14, 5))
    tk.Label(win, text=('ВАЖНО: формат складов не подтверждён реальным сохранением. Расчёт не списывает грузы.' if ru
                   else 'IMPORTANT: warehouse schema unverified. No cargo is deducted.'),
             bg=app.c('panel'), fg=app.c('fg'), font=(app.ui_font_family(), 10), wraplength=880).pack(anchor='w', padx=20)
    available = sorted({str(d.get('warehouse_id', '')) for d in depots if d.get('warehouse_id')})
    depot_name = tk.StringVar(value=available[0])
    depot_cb = ttk.Combobox(win, state='readonly', values=available, textvariable=depot_name)
    depot_cb.pack(fill='x', padx=20, pady=(12, 5))
    tk.Label(win, text=('Выбери внутренний ID груза, затем вручную сопоставь его каталогу:' if ru
                       else 'Select a game cargo ID, then match it to a catalog cargo:'),
             bg=app.c('panel'), fg=app.c('muted'), font=(app.ui_font_family(), 10)).pack(anchor='w', padx=20)
    sources = tk.Listbox(win, height=7, exportselection=False, bg=app.c('input'), fg=app.c('fg'),
                         selectbackground=app.c('selection'), relief='flat', font=(app.ui_font_family(), 10))
    sources.pack(fill='x', padx=20, pady=(5, 8))
    choices = sorted(CARGO.keys(), key=lambda c: display_cargo(c, 'ru').casefold())
    labels = [f'{display_cargo(cid, app.config["lang"])} — {cid}' for cid in choices]
    cargo_label = tk.StringVar()
    cargo_cb = ttk.Combobox(win, state='readonly', values=labels, textvariable=cargo_label)
    cargo_cb.pack(fill='x', padx=20)
    actions = tk.Frame(win, bg=app.c('panel'))
    actions.pack(fill='x', padx=20, pady=8)
    report = tk.Text(win, wrap='word', bg=app.c('input'), fg=app.c('fg'),
                     insertbackground=app.c('fg'), relief='flat', padx=12, pady=10,
                     font=(app.ui_font_family(), 10))
    report.pack(fill='both', expand=True, padx=20, pady=(0, 16))
    source_ids = []

    def mapped():
        return app.profiles.cargo_mappings(app.active_profile_key)

    def update_report():
        try:
            data = preview_warehouse(snap, depot_name.get(), mapped(), list(app.load))
            lines = [('Склад: ' if ru else 'Warehouse: ') + depot_name.get(),
                     ('Только приблизительный расчёт; значения не подтверждены и не списываются.' if ru
                      else 'Estimate only: counts are unverified and never deducted.'), '']
            if not data['rows']:
                lines.append('В калькуляторе пока нет грузов.' if ru else 'No cargo in current load.')
            for row in data['rows']:
                name = display_cargo(row['cargo_id'], app.config['lang'])
                amount = row['observed']
                avail = ('неизвестно' if ru else 'unknown') if amount is None else (
                    ('без ограничения (?)' if ru else 'possibly unlimited') if amount == -1 else str(amount))
                need = '?' if row['shortage'] is None else str(row['shortage'])
                lines.append(f'{name}: {row["required"]} нужно / {avail} на складе / дефицит {need}' if ru
                             else f'{name}: need {row["required"]} / observed {avail} / short {need}')
            lines.extend(['', ('Не сопоставленные ID: ' if ru else 'Unmatched IDs: ') +
                          str(len(data['unmapped_raw_ids']))])
            if data['ambiguous_cargo_ids']:
                lines.append('Несколько ID связаны с одним грузом; количество неизвестно: ' +
                             ', '.join(data['ambiguous_cargo_ids']) if ru else
                             'Multiple game IDs map to the same cargo; counts unknown: ' +
                             ', '.join(data['ambiguous_cargo_ids']))
        except ValueError as exc:
            lines = [str(exc)]
        report.config(state='normal')
        report.delete('1.0', tk.END)
        report.insert('1.0', '\n'.join(lines))
        report.config(state='disabled')

    def update_source(*_):
        nonlocal source_ids
        sources.delete(0, tk.END)
        source_ids = []
        for depot in depots:
            if depot.get('warehouse_id') != depot_name.get():
                continue
            for raw, value in sorted(depot.get('cargo', {}).items()):
                source_ids.append(raw)
                dest = mapped().get(raw)
                sources.insert(tk.END, f'{raw}: {value}  →  {display_cargo(dest, app.config["lang"]) if dest else "?"}')
        update_report()

    def chosen_id():
        idx = sources.curselection()
        return source_ids[idx[0]] if idx else None

    def pick_source(_=None):
        raw = chosen_id()
        if raw:
            dest = mapped().get(raw)
            cargo_label.set(labels[choices.index(dest)] if dest in choices else '')

    def assign():
        raw = chosen_id()
        if raw is None or cargo_label.get() not in labels:
            return
        app.profiles.map_game_cargo(app.active_profile_key, raw, choices[labels.index(cargo_label.get())])
        update_source()

    def unassign():
        raw = chosen_id()
        if raw:
            app.profiles.map_game_cargo(app.active_profile_key, raw, None)
            update_source()

    app.btn(actions, 'Сопоставить ID' if ru else 'Match ID', assign).pack(side='left', padx=(0, 8))
    app.btn(actions, 'Убрать связь' if ru else 'Remove match', unassign).pack(side='left', padx=(0, 8))
    app.btn(actions, 'Пересчитать' if ru else 'Recalculate', update_report).pack(side='left')
    depot_cb.bind('<<ComboboxSelected>>', update_source)
    sources.bind('<<ListboxSelect>>', pick_source)
    update_source()
    win.lift()
    return win
