"""Offline, collapsible release history for the approved Expedition UI."""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path

# Bundled version notes only. Never invent historical release features.
DEFAULT_NOTES = [
  {'version':'0.31.16', 'date':'2026-11-21', 'sections':{
     'Добавлено':['Разворачиваемая локальная история обновлений с кнопками управления',
                  'Имя профиля Steam при наличии локальной записи; ручное имя профиля',
                  'Подробный просмотр техники из игрового сохранения, где формат подтверждён'],
     'Исправлено':['Рамки и сетка панелей интерфейса «Экспедиция»',
                   'Расположение элементов страницы настроек и поисковых фильтров',
                   'Подсветка системных кнопок окна при наведении'],
     'Улучшено':['Плавное управление колесом прокрутки, без потери накопленных движений',
                  'Сортировка грузов по массе и категориям']
  }},
  {'version':'0.31.15', 'date':'2026-11-20', 'sections':{
     'Исправлено':['Чтение CompleteSave.cfg, CompleteSave1.cfg и CompleteSave2.cfg',
                   'Обработка завершающего нулевого байта в сохранении без изменения файла']
  }},
]
BG = '#091C25'; PANEL = '#132C37'; RAISED = '#193744'
FG = '#EEF3F2'; MUTED = '#AEC1C8'; ACCENT = '#FFC21B'; BORDER='#365564'


def load_notes(root=None):
    if root is None:
        try:
            from core import ROOT
            root = ROOT
        except ImportError:
            root = Path(__file__).resolve().parent
    path = Path(root) / 'changelog_v316.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, list) and all(isinstance(item, dict) and
            isinstance(item.get('version'), str) and isinstance(item.get('sections'),dict)
            for item in data):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return DEFAULT_NOTES


class AboutChangelog(tk.Toplevel):
    def __init__(self, master, version='', *, lang='ru'):
        super().__init__(master)
        self.ru = lang == 'ru'
        self.title('О программе • SnowRunner Helper' if self.ru else 'About • SnowRunner Helper')
        self.geometry('825x660')
        self.minsize(640,500)
        self.configure(bg=BG)
        self.notes = load_notes()
        self.sections = []
        header = tk.Frame(self,bg='#0C222E',height=148)
        header.pack(fill='x');header.pack_propagate(False)
        tk.Label(header,text='SNOWRUNNER HELPER',fg=FG,bg=header['bg'],
            font=('Segoe UI',21,'bold')).pack(anchor='w',padx=25,pady=(18,1))
        tk.Label(header,text='ЭКСПЕДИЦИОННЫЙ ПОМОЩНИК' if self.ru else 'EXPEDITION ASSISTANT',
            fg=ACCENT,bg=header['bg'],font=('Segoe UI',10,'bold')).pack(anchor='w',padx=26)
        tk.Label(header,text=(f'Разработчик: FASBER     •     Версия: {version}' if self.ru else
            f'Developer: FASBER     •     Version: {version}'),fg=MUTED,bg=header['bg'],
            font=('Segoe UI',11)).pack(anchor='w',padx=26,pady=(15,0))
        intro = 'Грузы, крафт, техника и игровой прогресс. Работает без интернета.' if self.ru else 'Cargo, crafting, vehicles and save progress. Works offline.'
        tk.Label(self,text=intro,fg=FG,bg=BG,font=('Segoe UI',11),anchor='w').pack(fill='x',padx=24,pady=(13,5))
        tk.Label(self,text=('Сохранения игры доступны только для чтения.' if self.ru else
                'Game saves are read-only.'),fg=MUTED,bg=BG,font=('Segoe UI',10),anchor='w').pack(fill='x',padx=24,pady=(0,11))
        tk.Frame(self,bg=BORDER,height=1).pack(fill='x',padx=24)
        heading = tk.Frame(self,bg=BG)
        heading.pack(fill='x',padx=24,pady=(12,7))
        tk.Label(heading,text='ИСТОРИЯ ОБНОВЛЕНИЙ' if self.ru else 'CHANGELOG',
             fg=ACCENT,bg=BG,font=('Segoe UI',14,'bold')).pack(side='left')
        tk.Button(heading,text='Развернуть всё' if self.ru else 'Expand all',
             command=lambda:self.expand_all(True),fg=FG,bg=RAISED,
             activebackground='#2B5464',activeforeground=FG,relief='flat',bd=0,
             padx=12,pady=5,cursor='hand2').pack(side='right',padx=(8,0))
        tk.Button(heading,text='Свернуть всё' if self.ru else 'Collapse all',
             command=lambda:self.expand_all(False),fg=FG,bg=RAISED,
             activebackground='#2B5464',activeforeground=FG,relief='flat',bd=0,
             padx=12,pady=5,cursor='hand2').pack(side='right')
        surround = tk.Frame(self,bg=BG)
        surround.pack(fill='both',expand=True,padx=22,pady=(0,15))
        self.canvas=tk.Canvas(surround,bg=BG,highlightthickness=0,borderwidth=0)
        scrollbar=tk.Scrollbar(surround,command=self.canvas.yview)
        scrollbar.pack(side='right',fill='y')
        self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.inner=tk.Frame(self.canvas,bg=BG)
        self.slot=self.canvas.create_window((0,0),window=self.inner,anchor='nw')
        self.inner.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.slot,width=e.width))
        for index, note in enumerate(self.notes):
            self._add_note(note, initially_open=index==0)
        self._wheel_target=None
        self._wheel_job=None
        self.bind('<MouseWheel>',self._wheel)
        self.bind('<Button-4>',self._wheel)
        self.bind('<Button-5>',self._wheel)
        self.protocol('WM_DELETE_WINDOW',self.destroy)

    def _wheel(self,e):
        """Gentle accumulated scrolling, never create one animation per wheel event."""
        delta=1 if getattr(e,'num',None)==4 else -1 if getattr(e,'num',None)==5 else (1 if getattr(e,'delta',0)>0 else -1)
        first,last=self.canvas.yview()
        visible=max(0.001,last-first)
        current=first if self._wheel_target is None else self._wheel_target
        target=max(0,min(1-visible,current-delta*visible*.21))
        self._wheel_target=target
        if self._wheel_job is None:
            self._wheel_job=self.after(16,self._wheel_step)
        return 'break'

    def _wheel_step(self):
        self._wheel_job=None
        try:
            current=self.canvas.yview()[0]
            first,last=self.canvas.yview()
            dst=max(0,min(1-(last-first),self._wheel_target or 0))
            if abs(dst-current)<.0007:
                self.canvas.yview_moveto(dst)
                self._wheel_target=None
                return
            self.canvas.yview_moveto(current+(dst-current)*.33)
            self._wheel_job=self.after(16,self._wheel_step)
        except tk.TclError:
            self._wheel_job=None

    def _add_note(self,note,initially_open):
        container=tk.Frame(self.inner,bg=PANEL,highlightbackground=BORDER,highlightthickness=1)
        container.pack(fill='x',pady=(0,9))
        bar=tk.Frame(container,bg=PANEL,height=46)
        bar.pack(fill='x');bar.pack_propagate(False)
        text=tk.Label(bar,text=f"v{note['version']}   •   {note.get('date','')}",font=('Segoe UI',12,'bold'),
            fg=FG,bg=PANEL,anchor='w',cursor='hand2')
        text.pack(side='left',padx=15,fill='y')
        arrow=tk.Label(bar,text='▾' if initially_open else '▸',fg=ACCENT,bg=PANEL,
            font=('Segoe UI',16,'bold'),cursor='hand2')
        arrow.pack(side='right',padx=15)
        details=tk.Frame(container,bg=PANEL)
        for group,items in note.get('sections',{}).items():
            if not isinstance(items,list):continue
            tk.Label(details,text=group.upper(),font=('Segoe UI',10,'bold'),bg=PANEL,
                fg=ACCENT,anchor='w').pack(fill='x',padx=17,pady=(10,3))
            for item in items:
                tk.Label(details,text='•  '+str(item),font=('Segoe UI',10),fg=FG,bg=PANEL,
                    anchor='w',justify='left',wraplength=675).pack(fill='x',padx=20,pady=3)
        if initially_open:details.pack(fill='x',pady=(0,14))
        state={'opened':initially_open,'details':details,'arrow':arrow}
        def toggle(event=None):
            self._toggle(state,not state['opened'])
        for w in (bar,text,arrow):w.bind('<Button-1>',toggle)
        self.sections.append(state)

    def _toggle(self,state,show):
        if state['opened']==show:return
        state['opened']=show
        if show:state['details'].pack(fill='x',pady=(0,14))
        else:state['details'].pack_forget()
        state['arrow'].configure(text='▾' if show else '▸')
        self.after_idle(lambda:self.canvas.configure(scrollregion=self.canvas.bbox('all')))

    def expand_all(self,show):
        for state in self.sections:self._toggle(state,show)


def show_about(screen):
    from update_config import CURRENT_VERSION
    window=AboutChangelog(screen.root,CURRENT_VERSION,lang=screen.lang)
    window.transient(screen.root)
    window.lift()
    return window
