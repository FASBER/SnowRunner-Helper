"""Visible, explicit SnowRunner save-slot selector with a separate Save action.

This is installed on Application without altering game-save files, calculator
manifests, OTA handling or the underlying _switch_profile safety confirmation.
A selection in the list is only a candidate until Save is clicked.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


def label_for_slot(item, ru=True):
    if item is None:
        return 'Мой локальный профиль (без сохранения игры)' if ru else 'Local profile (no game save)'
    hint = str(item.get('platform_hint') or 'SnowRunner')
    slot = item.get('slot', '?')
    name = Path(str(item.get('path', ''))).name
    return (f'{hint} — слот {slot} — {name}' if ru else
            f'{hint} — slot {slot} — {name}')


def game_connection_dialog(self):
    """Choose a slot first, click Save to persist it, then read its snapshot.

    The diagnostic report is packed *after* the action rows. Previously it
    expanded ahead of them and pushed the profile controls off the window.
    """
    from core import SETTINGS_FILE, save_json
    from game_bridge import status_summary

    ru = self.config.get('lang', 'ru') == 'ru'
    theme = lambda k: self.c(k)
    font = self.ui_font_family()
    win = tk.Toplevel(self.root)
    win.title('Подключение SnowRunner и профили' if ru else 'SnowRunner connection and profiles')
    win.geometry('960x665')
    win.minsize(770, 565)
    win.configure(bg=theme('panel'))

    def line(text, *, color='fg', size=10, weight='normal', pady=0):
        widget = tk.Label(win, text=text, bg=theme('panel'), fg=theme(color),
                          font=(font, size, weight), anchor='w', justify='left')
        widget.pack(fill='x', padx=24, pady=pady)
        return widget

    line('ПОДКЛЮЧЕНИЕ И ИГРОВЫЕ ПРОФИЛИ' if ru else 'GAME CONNECTION AND PROFILES',
         color='accent', size=18, weight='bold', pady=(17, 4))
    line('Игровые файлы — только чтение. Сначала выбери слот, затем нажми «Сохранить профиль».' if ru
         else 'Game saves are read-only. Choose a slot, then click Save profile.',
         color='muted', pady=(0, 7))
    status = line('', color='accent', weight='bold', pady=(0, 3))
    line('ВЫБЕРИ ИГРОВОЙ ПРОФИЛЬ:' if ru else 'SELECT A GAME PROFILE:', weight='bold', pady=(0, 3))

    slots_list = tk.Listbox(win, height=4, selectmode='browse', exportselection=False,
                            bg=theme('input'), fg=theme('fg'), selectbackground=theme('selection'),
                            selectforeground=theme('fg'), activestyle='none',
                            font=(font, 11), borderwidth=0, highlightthickness=1,
                            highlightbackground=theme('stroke'))
    slots_list.pack(fill='x', padx=24, pady=(0, 5))
    pending = line('', color='accent', weight='bold', pady=(0, 5))

    slots = []  # list[(profile_key, discovered slot | None)]
    def get_chosen():
        selected = slots_list.curselection()
        if not selected or selected[0] >= len(slots):
            return None
        return slots[selected[0]]

    def update_pending(event=None):
        selected = get_chosen()
        if selected is None:
            pending.configure(text='Выбери строку выше.' if ru else 'Select a row above.')
            return
        key, info = selected
        text = label_for_slot(info, ru)
        is_saved = key == self.active_profile_key
        pending.configure(text=(('Уже сохранён: ' if ru else 'Already saved: ') if is_saved else
                                ('Будет сохранён: ' if ru else 'Pending save: ')) + text)

    slots_list.bind('<<ListboxSelect>>', update_pending)

    # Place buttons BEFORE the expandable diagnostic panel. They must always be visible.
    row_primary = tk.Frame(win, bg=theme('panel'))
    row_primary.pack(fill='x', padx=24, pady=(0, 7))

    row_folders = tk.Frame(win, bg=theme('panel'))
    row_folders.pack(fill='x', padx=24, pady=(0, 5))
    row_tools = tk.Frame(win, bg=theme('panel'))
    row_tools.pack(fill='x', padx=24, pady=(0, 5))
    diagnostics_title = line('Найденные игровые файлы и сведения о профиле:' if ru
                             else 'Discovered game files and profile details:',
                             color='muted', pady=(3, 3))
    log_frame = tk.Frame(win, bg=theme('panel'))
    log_frame.pack(fill='both', expand=True, padx=24, pady=(0, 9))
    diagnostics = tk.Text(log_frame, wrap='word', bg=theme('input'), fg=theme('fg'),
                          font=(font, 10), insertbackground=theme('fg'), borderwidth=0,
                          padx=12, pady=10, state='disabled')
    log_scroll = tk.Scrollbar(log_frame, command=diagnostics.yview)
    diagnostics.configure(yscrollcommand=log_scroll.set)
    log_scroll.pack(side='right', fill='y')
    diagnostics.pack(side='left', fill='both', expand=True)

    def write_diagnostics(body):
        diagnostics.configure(state='normal')
        diagnostics.delete('1.0', 'end')
        diagnostics.insert('1.0', body)
        diagnostics.configure(state='disabled')

    def update_summary(*, preserve_pending=True):
        previous = get_chosen()
        previous_key = previous[0] if preserve_pending and previous else self.active_profile_key
        try:
            archives, found_slots = self._local_game_paths()
        except (OSError, ValueError) as exc:
            archives, found_slots = [], []
            scan_error = str(exc)
        else:
            scan_error = None
        slots[:] = [('local', None)] + [(item['profile_key'], item) for item in found_slots
                                         if item.get('profile_key') and item.get('path')]
        slots_list.delete(0, 'end')
        for key, info in slots:
            marker = '● ' if key == self.active_profile_key else '   '
            slots_list.insert('end', marker + label_for_slot(info, ru))
        keys = [entry[0] for entry in slots]
        selected_key = previous_key if previous_key in keys else (self.active_profile_key if self.active_profile_key in keys else 'local')
        chosen_index = keys.index(selected_key)
        slots_list.selection_set(chosen_index)
        slots_list.activate(chosen_index)
        slots_list.see(chosen_index)
        current_name = label_for_slot(next((info for key, info in slots if key == self.active_profile_key), None), ru)
        if self.active_profile_key not in keys:
            current_name = ('Ранее выбранное сохранение не найдено' if ru else 'Previously selected save not found')
        status.configure(text=('Текущий профиль: ' if ru else 'Current profile: ') + current_name)
        update_pending()
        if scan_error:
            message = (('Ошибка поиска: ' if ru else 'Scan error: ') + scan_error)
        else:
            message = status_summary(archives, found_slots, self.config.get('lang', 'ru'))
        if self.active_profile_key != 'local':
            try:
                data = self.profiles.read(self.active_profile_key)
                snapshot = data.get('game_snapshot')
                if snapshot:
                    message += '\n\n' + self._snapshot_description(snapshot)
                    message += '\n' + ('Обновлено: ' if ru else 'Updated: ') + str(data.get('last_synced_utc') or '?')
                else:
                    message += '\n\n' + ('Данные ещё не прочитаны.' if ru else 'Save not read yet.')
            except (OSError, ValueError) as exc:
                message += '\n\n' + str(exc)
        if getattr(self, '_last_profile_sync_issue', ''):
            message += '\n\n' + ('Последняя ошибка: ' if ru else 'Last issue: ') + self._last_profile_sync_issue
        write_diagnostics(message)

    def save_profile():
        chosen = get_chosen()
        if chosen is None:
            messagebox.showwarning('SnowRunner', 'Выбери профиль из списка.' if ru else
                                   'Select a profile from the list.', parent=win)
            return False
        key, slot = chosen
        if key != self.active_profile_key:
            # _switch_profile prompts before discarding/replacing a load draft,
            # saves previous app draft, and persists selected_game_profile.
            if not self._switch_profile(key, slot.get('path') if slot else None):
                return False
        else:
            # Explicit save also persists an already selected profile.
            self.config['selected_game_profile'] = key
            try:
                save_json(SETTINGS_FILE, self.config)
            except (OSError, ValueError) as exc:
                messagebox.showerror('SnowRunner', str(exc), parent=win)
                return False
        if key != 'local':
            try:
                self._sync_active_profile()
            except (OSError, ValueError, RuntimeError) as exc:
                self._last_profile_sync_issue = str(exc)
                update_summary(preserve_pending=False)
                messagebox.showwarning('SnowRunner',
                                       ('Профиль сохранён, но прочитать игровой прогресс пока не удалось:\n' if ru
                                        else 'Profile saved, but game progress could not be read:\n') + str(exc),
                                       parent=win)
                return True
        update_summary(preserve_pending=False)
        messagebox.showinfo('SnowRunner',
                            'Профиль сохранён. Он останется выбранным после перезапуска.' if ru else
                            'Profile saved. It will stay selected after restart.', parent=win)
        return True

    def choose_folder(setting, title):
        folder = filedialog.askdirectory(parent=win, title=title,
                                         initialdir=self.config.get(setting) or str(Path.home()))
        if folder:
            self.config[setting] = folder
            try:
                save_json(SETTINGS_FILE, self.config)
            except (OSError, ValueError) as exc:
                messagebox.showerror('SnowRunner', str(exc), parent=win)
                return
            update_summary()

    def sync_now():
        if self.active_profile_key == 'local':
            messagebox.showinfo('SnowRunner', 'Сначала сохрани игровой профиль.' if ru else
                                'Save a game profile first.', parent=win)
            return
        self.refresh_active_profile()
        update_summary()

    self.btn(row_primary, 'СОХРАНИТЬ ВЫБРАННЫЙ ПРОФИЛЬ' if ru else 'SAVE SELECTED PROFILE',
             save_profile, primary=True).pack(side='left', padx=(0, 10))
    self.btn(row_primary, 'Обновить список' if ru else 'Rescan',
             update_summary).pack(side='left', padx=(0, 8))
    self.btn(row_primary, 'Закрыть' if ru else 'Close', win.destroy).pack(side='right')

    self.btn(row_folders, 'Папка игры' if ru else 'Game folder', lambda: choose_folder(
        'game_install_dir', 'Папка SnowRunner' if ru else 'SnowRunner installation')).pack(side='left', padx=(0, 7))
    self.btn(row_folders, 'Папка сохранений' if ru else 'Save folder', lambda: choose_folder(
        'game_save_dir', 'Папка сохранений' if ru else 'Save folder')).pack(side='left', padx=(0, 7))
    self.btn(row_folders, 'Считать прогресс' if ru else 'Read progress', sync_now).pack(side='left', padx=(0, 7))
    self.btn(row_folders, 'Детали прогресса' if ru else 'Progress details',
             self.view_saved_progress).pack(side='left')

    self.btn(row_tools, 'Импорт рецептов' if ru else 'Import recipes',
             self.refresh_from_installed_game).pack(side='left', padx=(0, 7))
    self.btn(row_tools, 'Черновики' if ru else 'Drafts', self.drafts_dialog).pack(side='left', padx=(0, 7))
    self.btn(row_tools, 'Склады' if ru else 'Depots', self.warehouse_preview_dialog).pack(side='left', padx=(0, 7))
    self.btn(row_tools, 'Маршруты' if ru else 'Routes', self.route_planner_dialog).pack(side='left', padx=(0, 7))
    self.btn(row_tools, 'Схема сохранения' if ru else 'Save schema',
             self.save_structure_dialog).pack(side='left')

    update_summary(preserve_pending=False)
    win.lift()
    return win


def install_profile_selector():
    """Patch the actual Application class in script and module launch modes.

    Called from the existing theme setup after the Application class is defined;
    safe to call on every repaint because installation is idempotent.
    """
    installed = 0
    seen = set()
    for name in ('__main__', 'app'):
        module = sys.modules.get(name)
        cls = getattr(module, 'Application', None) if module is not None else None
        if cls is None or id(cls) in seen:
            continue
        seen.add(id(cls))
        if not getattr(cls, '_profile_selector_v314_installed', False):
            cls.game_connection_dialog = game_connection_dialog
            cls._profile_selector_v314_installed = True
            installed += 1
    return installed
