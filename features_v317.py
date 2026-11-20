"""Manual one-click SnowRunner game data refresh, without profile switching.

This module is intentionally data-only: it never guesses which save is active,
never rewrites game files, and never clears existing draft/verified recipes.
"""
from __future__ import annotations
import zipfile


def refresh_game_data(app):
    """Re-read ONLY the explicitly selected save and a unique local initial.pak.

    Returns a human-readable status for tests. The application itself is
    redrawn once and reports successes/warnings through a single dialog.
    """
    from pathlib import Path
    from tkinter import messagebox
    from core import CARGO, BUILTIN_RECIPES, IMPORTED_FILE, save_json
    from official_import import import_recipes

    ru = app.config.get('lang','ru') == 'ru'
    selected_profile = app.active_profile_key
    messages=[]
    errors=[]

    try:
        # If a draft cannot be saved, do NOT proceed to actions which redraw
        # the UI: this prevents losing an unsaved calculator load.
        app._save_profile_draft(force=True)
    except (OSError, ValueError) as exc:
        messagebox.showerror('SnowRunner',
            ('Не удалось сохранить текущий черновик: ' if ru else
             'Unable to save the current draft: ') + str(exc), parent=app.root)
        return {'saved':False,'profile':selected_profile,'recipes':0,'errors':[str(exc)]}

    if selected_profile != 'local':
        try:
            snapshot = app._sync_active_profile()
            messages.append('Сохранение выбранного профиля перечитано.' if ru else
                            'Selected profile save re-read.')
        except (OSError, ValueError, RuntimeError) as exc:
            errors.append(('Сохранение: ' if ru else 'Save: ') + str(exc))
    else:
        messages.append('Локальный профиль: игровое сохранение не выбиралось.' if ru else
                        'Local draft: no game save was selected.')

    refreshed = 0
    try:
        archives, _ = app._local_game_paths()
        if len(archives) == 1:
            entries, report = import_recipes(archives[0], CARGO)
            if entries:
                builtin_ids = {r['id'] for r in BUILTIN_RECIPES}
                merged = {r['id']:r for r in app.official}
                merged.update({r['id']:r for r in entries
                               if r.get('id') and r['id'] not in builtin_ids})
                # Do not replace verified recipes when the game has none.
                save_json(IMPORTED_FILE,list(merged.values()))
                app.official = list(merged.values())
                refreshed = len(entries)
                messages.append((f'Подтверждённых рецептов прочитано: {refreshed}.' if ru else
                                 f'Verified game recipes read: {refreshed}.'))
            else:
                messages.append('Подтверждённые рецепты не найдены; предыдущие сохранены.' if ru else
                                'No verified recipes found; previous ones preserved.')
        elif len(archives) > 1:
            errors.append('Найдено несколько игр. Выбери одну папку игры в настройках.' if ru else
                          'Multiple game installs found. Select one game directory.')
        else:
            messages.append('initial.pak не найден; каталог рецептов не изменён.' if ru else
                            'initial.pak not found; recipe catalog unchanged.')
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        errors.append(('Рецепты: ' if ru else 'Recipes: ') + str(exc))

    # Never switch to a different profile, and keep user's calculator draft.
    if app.active_profile_key != selected_profile:
        raise RuntimeError('Unexpected game profile change during manual refresh')
    app._last_profile_sync_issue = '; '.join(errors) if errors else ''
    app.render()
    title = 'Обновление игровых данных' if ru else 'Refresh game data'
    status = '\n'.join(messages + (['']+errors if errors else []))
    messagebox.showwarning(title,status,parent=app.root) if errors else messagebox.showinfo(
        title,status,parent=app.root)
    return {'saved':True,'profile':selected_profile,'recipes':refreshed,'errors':errors}
