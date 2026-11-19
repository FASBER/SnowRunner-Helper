"""Tkinter update controls for both Expedition and Classic UI skins.

Network and disk operations run in a worker thread. Tk is touched only on the
main thread by polling a queue with root.after; all dialogs are opt-in.
"""
from __future__ import annotations
import queue
import threading
import tkinter as tk
from tkinter import messagebox

from core import USER_DIR, SETTINGS_FILE, save_json
from update_checker import check_for_update
from update_downloader import download_installer, UpdateDownloadCancelled
from update_launcher import launch_installer
from update_config import (CURRENT_VERSION, RELEASE_MANIFEST_URL,
                           PUBLIC_KEY_ED25519_BASE64, UPDATE_CHANNEL)

BG, PANEL, FIELD, FG, MUTED, YELLOW = '#0B1922', '#132832', '#1C3440', '#F2F1EB', '#A8BEC7', '#F1BB39'

class UpdaterUI:
    def __init__(self, app):
        self.app = app
        self.busy = False
        self.closed = False
        self.events = queue.Queue()
        self.dialog = None
        self._progress = None
        self._progress_text = None
        self._release = None
        self._downloaded_file = None
        self._poll_running = False
        self._cancel_download = None

    @property
    def ru(self):
        return self.app.config.get('lang','ru') == 'ru'

    def configured(self):
        return bool(RELEASE_MANIFEST_URL and PUBLIC_KEY_ED25519_BASE64)

    def start_auto(self):
        if self.app.config.get('ota_auto_check', True) and self.configured():
            self.check(manual=False)

    def open_settings(self):
        self._window('Обновления' if self.ru else 'Updates')
        self._heading('ОБНОВЛЕНИЯ ПРИЛОЖЕНИЯ' if self.ru else 'APPLICATION UPDATES')
        self._label(('Установлена версия ' if self.ru else 'Installed version ') + CURRENT_VERSION)
        self._label(('Канал: стабильный · обновления требуют подтверждения' if self.ru else
                     'Channel: stable · updates require your approval'), muted=True)
        if self.configured():
            self._label('Сервер релизов подключён' if self.ru else 'Release server configured', muted=True)
        else:
            self._label('Сервер OTA и ключ подписи ещё не настроены.' if self.ru else
                        'OTA server and public signing key are not configured.', muted=True)
        auto = tk.BooleanVar(value=bool(self.app.config.get('ota_auto_check',True)))
        def toggle():
            self.app.config['ota_auto_check'] = bool(auto.get())
            save_json(SETTINGS_FILE,self.app.config)
        tk.Checkbutton(self._content,text='Проверять при запуске' if self.ru else 'Check on startup',
                       bg=PANEL,fg=FG,activebackground=PANEL,activeforeground=FG,
                       selectcolor=FIELD,variable=auto,command=toggle).pack(anchor='w',pady=(15,15))
        self._buttons([('Проверить сейчас' if self.ru else 'Check now',lambda:self.check(manual=True),True),
                       ('Закрыть' if self.ru else 'Close',self.close_dialog,False)])

    def _window(self, title):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.destroy()
        top = tk.Toplevel(self.app.root)
        top.title('SnowRunner Helper — ' + title)
        top.configure(bg=BG)
        top.geometry('630x360')
        top.resizable(False,False)
        top.transient(self.app.root)
        top.protocol('WM_DELETE_WINDOW',self.close_dialog)
        outer=tk.Frame(top,bg=BG,padx=18,pady=18);outer.pack(fill='both',expand=True)
        tk.Frame(outer,bg=YELLOW,height=4).pack(fill='x')
        self._content=tk.Frame(outer,bg=PANEL,padx=20,pady=20)
        self._content.pack(fill='both',expand=True,pady=(9,0))
        self.dialog=top
        top.lift()
        return top

    def _heading(self, text):
        tk.Label(self._content,text=text,bg=PANEL,fg=YELLOW,
                 font=('Segoe UI',16,'bold'),anchor='w').pack(fill='x',pady=(0,12))

    def _label(self,text,muted=False):
        widget=tk.Label(self._content,text=text,bg=PANEL,fg=MUTED if muted else FG,
                        font=('Segoe UI',10),justify='left',wraplength=540,anchor='w')
        widget.pack(fill='x',pady=(2,5))
        return widget

    def _buttons(self, items):
        line=tk.Frame(self._content,bg=PANEL)
        line.pack(side='bottom',fill='x',pady=(12,0))
        buttons=[]
        for title,command,primary in items:
            btn=tk.Button(line,text=title,command=command,bg=YELLOW if primary else FIELD,
                          fg='#12202A' if primary else FG,activebackground='#DAA829',
                          activeforeground=FG,relief='flat',padx=13,pady=8,
                          font=('Segoe UI',10,'bold' if primary else 'normal'))
            btn.pack(side='left',padx=(0,9))
            buttons.append(btn)
        return buttons

    def close_dialog(self):
        if self._cancel_download is not None and self.busy:
            self._cancel_download.set()
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog=None

    def _start_worker(self, job, on_success, on_error=None):
        if self.busy:return False
        self.busy=True
        self._on_success=on_success
        self._on_error=on_error
        def background():
            try: self.events.put(('success',job()))
            except Exception as exc: self.events.put(('error',exc))
        threading.Thread(target=background,daemon=True,name='SnowRunner-OTA').start()
        if not self._poll_running:
            self._poll_running=True
            self.app.root.after(100,self._poll)
        return True

    def _poll(self):
        if self.closed:return
        while True:
            try: kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='progress':
                if self._progress is not None and self._progress.winfo_exists():
                    self._progress['value']=round(100*value[0]/max(value[1],1))
                    self._progress_text.configure(text=f'{self._progress["value"]}%')
            else:
                self.busy=False
                try:
                    if kind=='success':self._on_success(value)
                    elif self._on_error:self._on_error(value)
                    else:
                        messagebox.showerror('SnowRunner OTA',str(value),parent=self.app.root)
                except tk.TclError:return
        if self.busy:
            self.app.root.after(100,self._poll)
        else:self._poll_running=False

    def check(self,manual=True):
        if not self.configured():
            if manual:
                messagebox.showinfo('SnowRunner OTA',
                    ('OTA пока не настроено: требуется HTTPS-сервер релизов и публичный ключ подписи.'
                     if self.ru else 'OTA is not configured: HTTPS release endpoint and public key required.'),
                    parent=self.dialog or self.app.root)
            return
        if manual and self.dialog is not None and self.dialog.winfo_exists():
            self._label('Проверяю обновления…' if self.ru else 'Checking for updates…',muted=True)
        def job():
            return check_for_update(RELEASE_MANIFEST_URL,PUBLIC_KEY_ED25519_BASE64,
                                    CURRENT_VERSION,UPDATE_CHANNEL)
        def found(release):
            if release is None:
                if manual: messagebox.showinfo('SnowRunner OTA',
                    'Уже установлена последняя версия.' if self.ru else 'You are up to date.',
                    parent=self.dialog or self.app.root)
            elif manual or release.version != self.app.config.get('ota_skip_version'):
                self.show_release(release)
        def error(exc):
            if manual:messagebox.showerror('SnowRunner OTA',str(exc),parent=self.dialog or self.app.root)
        self._start_worker(job,found,error)

    def show_release(self,release):
        self._release=release
        self._window('Доступно обновление' if self.ru else 'Update available')
        self._heading('НОВАЯ ВЕРСИЯ ' + release.version if self.ru else 'NEW VERSION ' + release.version)
        self._label(('Установлена: ' if self.ru else 'Installed: ') + CURRENT_VERSION)
        self._label(release.notes or ('Исправления и улучшения.' if self.ru else 'Fixes and improvements.'),muted=True)
        self._buttons([
            ('Скачать и установить' if self.ru else 'Download and install',self.download,True),
            ('Позже' if self.ru else 'Later',self.close_dialog,False),
            ('Пропустить версию' if self.ru else 'Skip version',self.skip_version,False)])

    def skip_version(self):
        self.app.config['ota_skip_version']=self._release.version
        save_json(SETTINGS_FILE,self.app.config)
        self.close_dialog()

    def download(self):
        release=self._release
        self._window('Скачивание' if self.ru else 'Download')
        self._heading('ЗАГРУЗКА ' + release.version if self.ru else 'DOWNLOADING ' + release.version)
        self._label('Проверка SHA-256 обязательна перед запуском установщика.' if self.ru else
                    'SHA-256 validation is required before launching the installer.',muted=True)
        from tkinter import ttk
        self._progress=ttk.Progressbar(self._content,orient='horizontal',length=530,maximum=100,mode='determinate')
        self._progress.pack(fill='x',pady=(10,4))
        self._progress_text=self._label('0%')
        self._cancel_download = threading.Event()
        self._buttons([('Отменить скачивание' if self.ru else 'Cancel download',self.close_dialog,False)])
        def job():
            return download_installer(release,USER_DIR/'updates',
                    progress=lambda done,total:self.events.put(('progress',(done,total))),
                    cancelled=self._cancel_download.is_set)
        def done(path):
            self._cancel_download=None
            self._downloaded_file=path
            self._show_install_prompt()
        def error(exc):
            self._cancel_download=None
            if isinstance(exc,UpdateDownloadCancelled):return
            messagebox.showerror('SnowRunner OTA',str(exc),parent=self.dialog or self.app.root)
            self.show_release(release)
        self._start_worker(job,done,error)

    def _show_install_prompt(self):
        self._window('Установка' if self.ru else 'Installation')
        self._heading('СКАЧАНО И ПРОВЕРЕНО' if self.ru else 'DOWNLOADED AND VERIFIED')
        self._label('Контрольная сумма совпадает с подписанным релизом.' if self.ru else
                    'Installer hash matches the signed release.')
        self._label('Сохранить черновики, закрыть помощник и запустить установщик?' if self.ru else
                    'Save drafts, close the assistant and launch the installer?',muted=True)
        self._buttons([('Установить' if self.ru else 'Install',self._install,True),
                       ('Позже' if self.ru else 'Later',self.close_dialog,False)])

    def _install(self):
        try:
            self.app._save_profile_draft(force=True)
        except (OSError,ValueError) as exc:
            messagebox.showerror('SnowRunner OTA',
                ('Не удалось сохранить черновик. Установка отменена:\n' if self.ru else
                 'Draft could not be saved. Installation canceled:\n') + str(exc),parent=self.dialog)
            return
        try:
            launch_installer(self._downloaded_file,self._release,user_folder=USER_DIR/'updates')
        except (OSError,ValueError,RuntimeError) as exc:
            messagebox.showerror('SnowRunner OTA',str(exc),parent=self.dialog)
            return
        self.closed=True
        self.app.root.destroy()
