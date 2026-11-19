"""Named plans and recoverable load history, isolated per selected game profile.

Uses only app-owned profile JSON; no game data or save files are modified.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from core import calculate_load, display_cargo


def open_draft_manager(app):
    ru = app.config.get('lang', 'ru') == 'ru'
    labels = {
        'title': 'Черновики загрузки' if ru else 'Load drafts',
        'search': 'Поиск по названию' if ru else 'Search names',
        'save': 'Сохранить как…' if ru else 'Save as…',
        'restore': 'Загрузить выбранный' if ru else 'Restore selected',
        'rename': 'Переименовать' if ru else 'Rename',
        'copy': 'Создать копию' if ru else 'Duplicate',
        'delete': 'Удалить' if ru else 'Delete',
        'history': 'История изменений' if ru else 'Recovery history',
        'recover': 'Восстановить запись' if ru else 'Recover entry',
    }
    window = tk.Toplevel(app.root)
    window.title(labels['title'])
    window.geometry('930x660')
    window.minsize(750, 540)
    window.configure(bg=app.c('panel'))
    tk.Label(window, text=labels['title'], bg=app.c('panel'), fg=app.c('accent'),
             font=(app.ui_font_family(), 18, 'bold')).pack(anchor='w', padx=20, pady=(16, 5))
    tk.Label(window,
             text=(f'Профиль: {app.active_profile_key} • только файлы приложения' if ru
                   else f'Profile: {app.active_profile_key} • application files only'),
             bg=app.c('panel'), fg=app.c('muted'), font=(app.ui_font_family(), 10)).pack(anchor='w', padx=20)
    search = tk.StringVar(value='')
    search_entry = tk.Entry(window, textvariable=search, bg=app.c('input'), fg=app.c('fg'),
                            insertbackground=app.c('fg'), relief='flat', font=(app.ui_font_family(), 11))
    search_entry.pack(fill='x', padx=20, pady=(12, 6), ipady=8)
    content = tk.Frame(window, bg=app.c('panel'))
    content.pack(fill='both', expand=True, padx=20)
    left = tk.Frame(content, bg=app.c('panel'))
    right = tk.Frame(content, bg=app.c('panel'))
    left.pack(side='left', fill='both', expand=True, padx=(0, 10))
    right.pack(side='left', fill='both', expand=True)
    tk.Label(left, text=('Именованные планы' if ru else 'Named plans'),
             bg=app.c('panel'), fg=app.c('fg'), font=(app.ui_font_family(), 11, 'bold')).pack(anchor='w', pady=(3, 5))
    drafts = tk.Listbox(left, selectmode='browse', exportselection=False,
                        bg=app.c('input'), fg=app.c('fg'), selectbackground=app.c('selection'),
                        relief='flat', font=(app.ui_font_family(), 10))
    drafts.pack(fill='both', expand=True)
    tk.Label(right, text=labels['history'], bg=app.c('panel'), fg=app.c('fg'),
             font=(app.ui_font_family(), 11, 'bold')).pack(anchor='w', pady=(3, 5))
    history = tk.Listbox(right, selectmode='browse', exportselection=False,
                         bg=app.c('input'), fg=app.c('fg'), selectbackground=app.c('selection'),
                         relief='flat', font=(app.ui_font_family(), 10))
    history.pack(fill='both', expand=True)
    detail = tk.Label(window, text='', bg=app.c('panel'), fg=app.c('muted'),
                      wraplength=855, justify='left', anchor='w', font=(app.ui_font_family(), 10))
    detail.pack(fill='x', padx=20, pady=8)
    items = []
    history_rows = []

    def describe(manifest):
        if not manifest:
            return 'Пустой план' if ru else 'Empty load'
        rows = ', '.join(f'{display_cargo(cargo, app.config["lang"])} ×{amount}' for cargo, amount in manifest[:5])
        if len(manifest) > 5:
            rows += '…'
        try:
            slots = calculate_load(manifest)
            return rows + (f' • слотов: {slots}' if ru else f' • slots: {slots}')
        except ValueError:
            return rows

    def refresh():
        nonlocal items, history_rows
        try:
            items = app.profiles.list_named_drafts(app.active_profile_key, search.get())
            history_rows = app.profiles.list_draft_history(app.active_profile_key)
        except (OSError, ValueError) as exc:
            messagebox.showerror(labels['title'], str(exc), parent=window)
            return
        drafts.delete(0, tk.END)
        for item in items:
            drafts.insert(tk.END, f'{item["name"]}  ({len(item["load"])} поз.)')
        history.delete(0, tk.END)
        for idx, item in enumerate(history_rows):
            history.insert(tk.END, f'{idx + 1}. {item.get("saved_at", "?")[:19]}  ({len(item["load"])} поз.)')
        detail.configure(text=('Текущая загрузка: ' if ru else 'Current load: ') + describe(app.load))

    def chosen():
        indexes = drafts.curselection()
        return items[indexes[0]] if indexes else None

    def operation(fn):
        try:
            app._save_profile_draft(force=True)
            fn()
            refresh()
        except (OSError, ValueError) as exc:
            messagebox.showerror(labels['title'], str(exc), parent=window)

    def add():
        name = simpledialog.askstring(labels['title'], 'Название:' if ru else 'Draft name:', parent=window)
        if name is not None:
            operation(lambda: app.profiles.create_named_draft(app.active_profile_key, name, list(app.load)))

    def restore():
        item = chosen()
        if not item:
            return
        if not messagebox.askyesno(labels['title'],
                ('Заменить текущую загрузку выбранным черновиком? Текущий план останется в истории.' if ru
                 else 'Replace the current load? The previous load remains in recovery history.'), parent=window):
            return
        def apply():
            manifest = app.profiles.restore_named_draft(app.active_profile_key, item['id'])
            app.load = manifest
            app._draft_saved_load = list(manifest)
            app.render()
        operation(apply)

    def rename():
        item = chosen()
        if not item:
            return
        name = simpledialog.askstring(labels['title'], 'Новое название:' if ru else 'New name:',
                                      initialvalue=item['name'], parent=window)
        if name is not None:
            operation(lambda: app.profiles.rename_named_draft(app.active_profile_key, item['id'], name))

    def duplicate():
        item = chosen()
        if not item:
            return
        name = simpledialog.askstring(labels['title'], 'Название копии:' if ru else 'Copy name:',
                                      initialvalue=item['name'] + (' (копия)' if ru else ' (copy)'), parent=window)
        if name is not None:
            operation(lambda: app.profiles.duplicate_named_draft(app.active_profile_key, item['id'], name))

    def delete():
        item = chosen()
        if item and messagebox.askyesno(labels['title'],
                ('Удалить только этот именованный черновик?' if ru else 'Delete this named draft only?'), parent=window):
            operation(lambda: app.profiles.delete_named_draft(app.active_profile_key, item['id']))

    def recover():
        indexes = history.curselection()
        if not indexes:
            return
        if not messagebox.askyesno(labels['title'],
                ('Восстановить выбранную версию? Текущий план останется в истории.' if ru
                 else 'Recover this version? The current load stays in recovery history.'), parent=window):
            return
        index = indexes[0]
        def apply():
            manifest = app.profiles.restore_draft_history(app.active_profile_key, index)
            app.load = manifest
            app._draft_saved_load = list(manifest)
            app.render()
        operation(apply)

    row = tk.Frame(window, bg=app.c('panel'))
    row.pack(fill='x', padx=20, pady=(0, 5))
    for title, func in [(labels['save'], add), (labels['restore'], restore), (labels['rename'], rename),
                        (labels['copy'], duplicate), (labels['delete'], delete)]:
        app.btn(row, title, func).pack(side='left', padx=(0, 6))
    row2 = tk.Frame(window, bg=app.c('panel'))
    row2.pack(fill='x', padx=20, pady=(0, 14))
    app.btn(row2, labels['recover'], recover).pack(side='left')
    tk.Label(row2, text=('Черновики не меняют игровое сохранение.' if ru
                         else 'Draft operations never change game saves.'),
             bg=app.c('panel'), fg=app.c('muted'), font=(app.ui_font_family(), 9)).pack(side='left', padx=12)
    search.trace_add('write', lambda *_: refresh())
    drafts.bind('<<ListboxSelect>>', lambda _: detail.configure(text=describe(chosen()['load'])) if chosen() else None)
    history.bind('<<ListboxSelect>>', lambda _: detail.configure(text=describe(history_rows[history.curselection()[0]]['load'])) if history.curselection() else None)
    refresh()
    window.lift()
    return window
