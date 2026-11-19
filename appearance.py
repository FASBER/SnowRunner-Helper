"""User-owned appearance profiles and a live, editable SnowRunner theme designer.

No theme changes are applied until the user presses Apply. Custom images and
archives are validated, and the stock theme is never modified.
"""
from __future__ import annotations
import copy
import json
import os
import shutil
import re
import uuid
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFont, ImageColor
from core import USER_DIR, ROOT, save_json

THEME_DIR = USER_DIR / 'themes'
THEME_DIR.mkdir(parents=True, exist_ok=True)
PRESETS = {
    'snow': {'ru':'Снежный конвой','en':'Snow convoy','accent':'#FFC21B','panel':'#151C20','row':'#222B31','fg':'#F1F2F0','muted':'#BAC3C6','border':'#45525A','image':'preset_snow.png'},
    'expedition': {'ru':'Горная экспедиция','en':'Mountain expedition','accent':'#EAAA2C','panel':'#181D22','row':'#293039','fg':'#F8F0E8','muted':'#BAC0C7','border':'#4F545A','image':'preset_expedition.png'},
    'mud': {'ru':'Суровое бездорожье','en':'Rugged offroad','accent':'#FFB22B','panel':'#1C1B19','row':'#302C27','fg':'#F9F0E3','muted':'#BFB6A8','border':'#665647','image':'preset_mud.png'},
    'ice': {'ru':'Ледяная база','en':'Icy outpost','accent':'#F5BA36','panel':'#101C26','row':'#1E303D','fg':'#EFF5F9','muted':'#BCCEDB','border':'#436078','image':'preset_ice.png'},
}
DEFAULT = {
    'preset':'snow', 'accent':'#FFC21B','panel':'#151C20','row':'#222B31',
    'fg':'#F1F2F0','muted':'#BAC3C6','border':'#45525A',
    'background_image':'','header_image':'',
    'ui_scale':100,'text_size':100,'panel_alpha':94,'corner_radius':8,
    'row_height':71,'button_height':41,'sidebar_width':252,'padding':12,
    'textures':True,'mud':False,'tracks':False,'snow':True,
    'animations':True,'animation_speed':100,'hover_glow':True,
    'slide_detail':True,'smooth_select':True,
    'font_cyrillic':'','font_latin':'', 'nav_icons':{},
}
COLOR_FIELDS = ['accent','panel','row','fg','muted','border']
ALLOWED_IMG = {'.png','.jpg','.jpeg','.webp'}

def normalize(value):
    d=copy.deepcopy(DEFAULT)
    if isinstance(value,dict):
        for k,v in value.items():
            if k in d and type(v)==type(d[k]): d[k]=v
    if d['preset'] not in PRESETS:d['preset']='snow'
    for k in COLOR_FIELDS:
        if not re.fullmatch(r'#[0-9A-Fa-f]{6}',d[k]):d[k]=DEFAULT[k]
    for k,a,b in [('ui_scale',75,150),('text_size',75,160),('panel_alpha',35,100),('corner_radius',0,22),('row_height',56,80),('button_height',29,65),('sidebar_width',200,310),('padding',4,28),('animation_speed',30,250)]:
        d[k]=max(a,min(b,d[k]))
    d['nav_icons']={k:v for k,v in d['nav_icons'].items() if k in ('cargo','recipes','calculator','manual','settings') and isinstance(v,str)}
    return d

def preset_config(name):
    d=copy.deepcopy(DEFAULT)
    d.update({k:v for k,v in PRESETS[name].items() if k in COLOR_FIELDS})
    d['preset']=name
    return d

def asset_path(settings, kind):
    path=settings.get('header_image' if kind=='header' else 'background_image')
    if path:
        p=Path(path)
        if p.is_file():return p
    return ROOT/'assets'/'themes'/PRESETS[settings.get('preset','snow')]['image']

def _copy_asset(source,target_dir):
    path=Path(source)
    if not path.is_file() or path.suffix.lower() not in ALLOWED_IMG:raise ValueError('Нужен PNG, JPG или WebP')
    if path.stat().st_size>18_000_000:raise ValueError('Изображение слишком большое (максимум 18 МБ)')
    with Image.open(path) as img:
        img.verify()
    target_dir.mkdir(parents=True,exist_ok=True)
    dest=target_dir/(uuid.uuid4().hex+path.suffix.lower())
    shutil.copy2(path,dest)
    return str(dest)

def _copy_font_asset(source,target_dir,script):
    # Only user-selected fonts are transferred into their own theme locally;
    # the distributed project never bundles third-party font files.
    from font_manager import inspect_font
    path=Path(source)
    inspect_font(path,script)
    target_dir.mkdir(parents=True,exist_ok=True)
    dest=target_dir/(uuid.uuid4().hex+path.suffix.lower())
    shutil.copy2(path,dest)
    return str(dest)

def save_theme(name,settings):
    title=name.strip()[:80]
    if not title:raise ValueError('Введите название темы')
    identifier=uuid.uuid4().hex[:12]
    folder=THEME_DIR/identifier
    folder.mkdir(parents=True)
    content=normalize(settings)
    for k in ('background_image','header_image'):
        if content.get(k):content[k]=Path(_copy_asset(content[k],folder)).name
    for script in ('cyrillic','latin'):
        key='font_'+script
        if content.get(key):content[key]=Path(_copy_font_asset(content[key],folder,script)).name
    for k,v in list(content['nav_icons'].items()):
        if v:content['nav_icons'][k]=Path(_copy_asset(v,folder)).name
    data={'format':1,'name':title,'settings':content}
    save_json(folder/'theme.json',data)
    return folder

def list_themes():
    found=[]
    for p in sorted(THEME_DIR.glob('*/theme.json')):
        try:
            d=json.loads(p.read_text(encoding='utf8'))
            if isinstance(d,dict) and isinstance(d.get('settings'),dict): found.append((d.get('name',p.parent.name),p.parent))
        except Exception:pass
    return found

def open_theme(folder):
    folder=Path(folder).resolve()
    if folder.parent!=THEME_DIR.resolve():raise ValueError('Неверная папка темы')
    d=json.loads((folder/'theme.json').read_text(encoding='utf8'))
    s=normalize(d['settings'])
    for k in ('background_image','header_image'):
        if s[k]:
            p=(folder/s[k]).resolve()
            s[k]=str(p) if p.parent==folder and p.exists() else ''
    for script in ('cyrillic','latin'):
        key='font_'+script
        if s.get(key):
            path=(folder/s[key]).resolve()
            s[key]=str(path) if path.parent==folder and path.is_file() else ''
    s['nav_icons']={k:str((folder/v).resolve()) for k,v in s['nav_icons'].items() if v and (folder/v).resolve().parent==folder and (folder/v).is_file()}
    return s

def export_theme(settings,target,name='SnowRunner Theme'):
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        d=normalize(settings)
        for k in ('background_image','header_image'):
            if d.get(k):
                p=Path(d[k]); z.write(p,'images/'+k+p.suffix.lower());d[k]='images/'+k+p.suffix.lower()
        for script in ('cyrillic','latin'):
            key='font_'+script
            if d.get(key):
                from font_manager import inspect_font
                src=Path(d[key]);inspect_font(src,script)
                filename=f'fonts/{script}'+src.suffix.lower()
                z.write(src,filename);d[key]=filename
        for k,p in list(d['nav_icons'].items()):
            if Path(p).is_file():
                z.write(p,f'icons/{k}'+Path(p).suffix.lower());d['nav_icons'][k]=f'icons/{k}'+Path(p).suffix.lower()
            else:d['nav_icons'].pop(k,None)
        z.writestr('theme.json',json.dumps({'format':1,'name':name,'settings':d},ensure_ascii=False,indent=2))

def import_theme(path):
    folder=THEME_DIR/uuid.uuid4().hex[:12]
    with zipfile.ZipFile(path) as z:
        members=z.infolist()
        if len(members)>24 or sum(x.file_size for x in members)>100_000_000:raise ValueError('Слишком большой архив темы')
        names={x.filename for x in members}
        if 'theme.json' not in names:raise ValueError('В архиве нет theme.json')
        raw=json.loads(z.read('theme.json').decode('utf-8'))
        if raw.get('format')!=1 or not isinstance(raw.get('settings'),dict):raise ValueError('Неподдерживаемый формат темы')
        s=normalize(raw['settings'])
        folder.mkdir(parents=True,exist_ok=True)
        for key in ('background_image','header_image'):
            filename=s.get(key)
            if filename:
                if filename not in names or Path(filename).suffix.lower() not in ALLOWED_IMG:raise ValueError('В архиве не хватает изображения: '+filename)
                dest=folder/Path(filename).name
                dest.write_bytes(z.read(filename));s[key]=dest.name
                with Image.open(dest) as im:im.verify()
        for script in ('cyrillic','latin'):
            key='font_'+script
            name=s.get(key)
            if name:
                if name not in names or Path(name).suffix.lower() not in ('.ttf','.otf'):
                    raise ValueError('Шрифт отсутствует в архиве: '+str(name))
                dest=folder/(script+Path(name).suffix.lower())
                dest.write_bytes(z.read(name))
                from font_manager import inspect_font
                inspect_font(dest,script)
                s[key]=dest.name
        for key,v in list(s['nav_icons'].items()):
            if v:
                if v not in names or Path(v).suffix.lower() not in ALLOWED_IMG:raise ValueError('Ошибка значка '+key)
                dest=folder/(key+Path(v).suffix.lower())
                dest.write_bytes(z.read(v));s['nav_icons'][key]=dest.name
                with Image.open(dest) as im:im.verify()
        save_json(folder/'theme.json',{'format':1,'name':str(raw.get('name','Импортированная тема'))[:80],'settings':s})
    return folder

class AppearanceEditor(tk.Toplevel):
    SECTIONS=['Общие','Цвета','Фон','Шрифты','Размеры','Иконки','Анимации','Темы']
    EN=['General','Colors','Background','Fonts','Sizing','Icons','Animations','Themes']
    def __init__(self,app):
        super().__init__(app.root)
        self.app=app;self.ru=app.config['lang']=='ru'
        self.draft=normalize(app.config.get('appearance'))
        self.title('SnowRunner Helper — Настройка внешнего вида' if self.ru else 'SnowRunner Helper — Appearance')
        screenw=self.winfo_screenwidth();screenh=self.winfo_screenheight()
        self.geometry(f'{min(1430,screenw-65)}x{min(850,screenh-65)}')
        self.minsize(min(950,screenw-90),min(590,screenh-90))
        self.configure(bg='#10181D')
        self.selection=0;self.preview_image=None;self.preview_mode='cargo';self.selected_theme_folder=None
        self.preview_popup=None;self.preview_popup_canvas=None;self._preview_images={}
        self._build()
        self.transient(app.root)
        self.protocol('WM_DELETE_WINDOW',self.destroy)
        self.grab_set()
    def tx(self,ru,en):return ru if self.ru else en
    def text(self,parent,caption,size=11,color='#EAF0F3',bold=False,**kw):
        return tk.Label(parent,text=caption,fg=color,bg=parent.cget('bg'),font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)
    def button(self,parent,title,fn,primary=False):
        return tk.Button(parent,text=title,command=fn,bg=self.draft['accent'] if primary else '#27343C',fg='#15191C' if primary else '#EFF4F5',activebackground='#E3AB28',activeforeground='#14171A',font=('Segoe UI',10,'bold'),bd=0,relief='flat',padx=13,pady=8,cursor='hand2')
    def _build(self):
        head=tk.Frame(self,bg='#1A252D',height=68);head.pack(side='top',fill='x');head.pack_propagate(False)
        self.text(head,self.tx('НАСТРОЙКА ВНЕШНЕГО ВИДА','APPEARANCE EDITOR'),20,bold=True).pack(side='left',padx=20,pady=14)
        from tkinter import ttk
        options={k:PRESETS[k]['ru' if self.ru else 'en'] for k in PRESETS}
        combo=ttk.Combobox(head,values=list(options.values()),state='readonly',width=22)
        combo.set(self.tx('Быстрые настройки','Quick settings'))
        combo.pack(side='right',padx=18,pady=16)
        combo.bind('<<ComboboxSelected>>',lambda e:self.pick_preset(next(k for k,v in options.items() if v==combo.get())))
        bottom=tk.Frame(self,bg='#141D22');bottom.pack(side='bottom',fill='x',padx=0,pady=0)
        for title,fn in [(self.tx('Сбросить','Reset'),self.reset),(self.tx('Сохранить как тему','Save as theme'),self.save_custom),(self.tx('Экспорт ZIP','Export ZIP'),self.export),(self.tx('Импорт ZIP','Import ZIP'),self.import_zip),(self.tx('Отмена','Cancel'),self.destroy)]:
            self.button(bottom,title,fn).pack(side='left',padx=5,pady=12)
        self.button(bottom,self.tx('ПРИМЕНИТЬ ИЗМЕНЕНИЯ','APPLY CHANGES'),self.apply,True).pack(side='right',padx=14,pady=12)
        body=tk.Frame(self,bg='#131B20');body.pack(fill='both',expand=True,padx=13,pady=12)
        sidebar=tk.Frame(body,bg='#1B262C',width=158);sidebar.pack(side='left',fill='y',padx=(0,12));sidebar.pack_propagate(False)
        self.nav=[]
        for i,caption in enumerate(self.SECTIONS if self.ru else self.EN):
            b=self.button(sidebar,caption,lambda j=i:self.section(j));b.pack(fill='x',padx=7,pady=4)
            self.nav.append(b)
        self.content_shell=tk.Frame(body,bg='#1A252B',width=388);self.content_shell.pack(side='left',fill='y',padx=(0,12));self.content_shell.pack_propagate(False)
        self.content_canvas=tk.Canvas(self.content_shell,bg='#1A252B',highlightthickness=0)
        self.content_scroll=tk.Scrollbar(self.content_shell,command=self.content_canvas.yview)
        self.content_canvas.configure(yscrollcommand=self.content_scroll.set)
        self.content_scroll.pack(side='right',fill='y')
        self.content_canvas.pack(side='left',fill='both',expand=True)
        self.content=tk.Frame(self.content_canvas,bg='#1A252B')
        self.content_window=self.content_canvas.create_window((9,7),window=self.content,anchor='nw')
        self.content.bind('<Configure>',lambda _:self.content_canvas.configure(scrollregion=self.content_canvas.bbox('all')))
        self.content_canvas.bind('<Configure>',lambda e:self.content_canvas.itemconfigure(self.content_window,width=max(260,e.width-24)))
        self.content_canvas.bind('<MouseWheel>',lambda e:self.content_canvas.yview_scroll(-1 if e.delta>0 else 1,'units'))
        self.preview_shell=tk.Frame(body,bg='#18242B');self.preview_shell.pack(side='left',fill='both',expand=True)
        paneltitle=tk.Frame(self.preview_shell,bg=self.preview_shell.cget('bg'));paneltitle.pack(fill='x',padx=17,pady=(16,8))
        self.text(paneltitle,self.tx('ПРЕДПРОСМОТР ПРИЛОЖЕНИЯ','LIVE PREVIEW'),14,bold=True).pack(side='left')
        from tkinter import ttk
        self.preview_mode_var=tk.StringVar(value=self.tx('Главное окно','Main window'))
        choices=[self.tx('Главное окно','Main window'),self.tx('Крафт','Crafting'),self.tx('Настройки','Settings')]
        cb=ttk.Combobox(paneltitle,textvariable=self.preview_mode_var,values=choices,width=18,state='readonly')
        cb.pack(side='right',padx=2)
        cb.bind('<<ComboboxSelected>>',lambda e:self.change_preview_mode(choices.index(cb.get())))
        self.button(self.preview_shell,self.tx('⛶  Открыть предпросмотр в отдельном окне','⛶  Open large live preview'),
                    self.open_preview_window).pack(anchor='e',padx=14,pady=(0,7))
        self.text(self.preview_shell,self.tx('Все изменения видны до сохранения. Отмена вернёт прежнюю тему.',
                    'All changes are shown before saving. Cancel keeps the old theme.'),
                    10,color='#AEB9C1').pack(anchor='w',padx=18,pady=(0,5))
        self.preview=tk.Canvas(self.preview_shell,bg='#0C141A',highlightthickness=0);self.preview.pack(fill='both',expand=True,padx=14,pady=(0,14))
        self.preview.bind('<Configure>',lambda _:self.draw_preview())
        self.section(0)
    def section(self,index):
        self.selection=index
        for i,b in enumerate(self.nav): b.configure(bg=self.draft['accent'] if i==index else '#27343C',fg='#13191D' if i==index else '#F1F4F5')
        for x in self.content.winfo_children():x.destroy()
        self.content_canvas.yview_moveto(0)
        p=self.content
        titles=self.SECTIONS if self.ru else self.EN
        self.text(p,titles[index],18,bold=True).pack(anchor='w',pady=(5,15))
        [self.general,self.colors,self.background,self.fonts,self.sizes,self.icons,self.animations,self.themes][index](p)
        self.draw_preview()
    def caption(self,p,txt):self.text(p,txt,10,color='#CBD3D8').pack(anchor='w',pady=(10,3))
    def dropdown(self,p,values,current,onchange):
        from tkinter import ttk
        var=tk.StringVar(value=current)
        widget=ttk.Combobox(p,textvariable=var,values=values,state='readonly',width=29)
        widget.pack(anchor='w',fill='x',pady=5)
        widget.bind('<<ComboboxSelected>>',lambda _:onchange(var.get()))
    def slider(self,p,key,caption,lo,hi):
        self.caption(p,f'{caption}: {self.draft[key]}'+(' %' if key in ('ui_scale','text_size','panel_alpha','animation_speed') else ''))
        val=tk.IntVar(value=self.draft[key])
        w=tk.Scale(p,from_=lo,to=hi,variable=val,orient='horizontal',bg='#1A252B',fg='#F8F8F8',troughcolor='#34434C',activebackground=self.draft['accent'],highlightthickness=0,showvalue=True,resolution=1,length=285)
        w.pack(fill='x',padx=2)
        w.configure(command=lambda v,k=key:self.set(k,int(float(v))))
    def check(self,p,key,title):
        v=tk.BooleanVar(value=self.draft[key]);tk.Checkbutton(p,text=title,variable=v,command=lambda k=key,val=v:self.set(k,val.get()),bg=p.cget('bg'),fg='#EAEFF1',selectcolor='#354046',activebackground=p.cget('bg'),activeforeground='#F7F7F7',anchor='w').pack(anchor='w',pady=6)
    def set(self,k,v):
        self.draft[k]=v;self.draw_preview()
    def general(self,p):
        self.caption(p,self.tx('Базовый стиль','Base style'))
        values=[PRESETS[x]['ru' if self.ru else 'en'] for x in PRESETS]
        current=PRESETS[self.draft['preset']]['ru' if self.ru else 'en']
        self.dropdown(p,values,current,lambda name:self.pick_preset(next(k for k,v in PRESETS.items() if v['ru' if self.ru else 'en']==name)))
        self.slider(p,'ui_scale',self.tx('Масштаб интерфейса','Interface scale'),75,150)
        self.slider(p,'panel_alpha',self.tx('Непрозрачность панелей','Panel opacity'),35,100)
        self.slider(p,'corner_radius',self.tx('Скругление углов','Corner radius'),0,22)
        for key,title in [('textures',self.tx('Текстуры и потертости','Weathered textures')),('snow',self.tx('Снежный налёт','Snow overlay'))]:self.check(p,key,title)
    def pick_preset(self,k):
        new=preset_config(k)
        for color in COLOR_FIELDS:self.draft[color]=new[color]
        self.draft['preset']=k
        self.section(self.selection)
    def colors(self,p):
        for key,ru,en in [('accent','Акцентный цвет','Accent'),('panel','Фон панелей','Panel'),('row','Цвет карточек','Rows'),('fg','Основной текст','Text'),('muted','Вторичный текст','Muted'),('border','Рамки','Borders')]:
            line=tk.Frame(p,bg=p.cget('bg'));line.pack(fill='x',pady=5)
            tk.Label(line,text=ru if self.ru else en,bg=p.cget('bg'),fg='#F5F5F5',width=22,anchor='w').pack(side='left')
            tk.Button(line,command=lambda k=key:self.choose_color(k),bg=self.draft[key],width=8,relief='ridge').pack(side='left')
    def choose_color(self,k):
        value=colorchooser.askcolor(color=self.draft[k],parent=self)[1]
        if value:self.set(k,value);self.section(self.selection)
    def image_picker(self,p,key,name):
        self.caption(p,name)
        line=tk.Frame(p,bg=p.cget('bg'));line.pack(fill='x')
        self.text(line,Path(self.draft[key]).name if self.draft[key] else self.tx('Стандартное изображение','Default image'),9,color='#CDD3D6').pack(anchor='w')
        self.button(line,self.tx('Выбрать файл…','Browse…'),lambda:self.pick_image(key)).pack(side='left',padx=(0,8),pady=7)
        self.button(line,self.tx('Сброс','Reset'),lambda:self.set_image(key,'')).pack(side='left',pady=7)
    def set_image(self,key,v):self.set(key,v);self.section(self.selection)
    def pick_image(self,key):
        name=filedialog.askopenfilename(parent=self,filetypes=[('Images','*.png *.jpg *.jpeg *.webp')])
        if name:
            try:
                if Path(name).stat().st_size>18_000_000:raise ValueError('Максимум 18 МБ')
                with Image.open(name) as i:i.verify()
                self.set_image(key,name)
            except Exception as exc:messagebox.showerror('Image',str(exc),parent=self)
    def background(self,p):
        self.image_picker(p,'background_image',self.tx('Фон приложения','Application background'))
        self.image_picker(p,'header_image',self.tx('Шапка и грузовик','Header / truck image'))
        self.slider(p,'panel_alpha',self.tx('Непрозрачность панелей','Panel opacity'),35,100)
        self.check(p,'snow',self.tx('Снежный эффект','Snow effect'))
        self.check(p,'textures',self.tx('Текстуры и потертости','Grunge textures'))
    def fonts(self,p):
        self.caption(p,self.tx('Кириллица','Cyrillic'))
        self.text(p,self.app.font_manager.label('cyrillic'),10).pack(anchor='w')
        self.button(p,self.tx('Загрузить TTF / OTF','Import TTF / OTF'),lambda:self.change_font('cyrillic')).pack(anchor='w',pady=5)
        self.button(p,self.tx('Вернуть стандартный','Restore default'),lambda:self.clear_font('cyrillic')).pack(anchor='w',pady=3)
        self.caption(p,self.tx('Латиница','Latin'))
        self.text(p,self.app.font_manager.label('latin'),10).pack(anchor='w')
        self.button(p,self.tx('Загрузить TTF / OTF','Import TTF / OTF'),lambda:self.change_font('latin')).pack(anchor='w',pady=5)
        self.button(p,self.tx('Вернуть стандартный','Restore default'),lambda:self.clear_font('latin')).pack(anchor='w',pady=3)
        self.slider(p,'text_size',self.tx('Размер текста','Text size'),75,160)
        self.text(p,'АБВГДЕЁЖ • SnowRunner ABC',13).pack(anchor='w',pady=16)
    def clear_font(self,script):
        self.draft['font_'+script]=''
        self.section(self.selection)

    def change_font(self,script):
        name=filedialog.askopenfilename(parent=self,filetypes=[('Fonts','*.ttf *.otf')]);
        if not name:return
        try:
            from font_manager import inspect_font
            inspect_font(name,script)
            self.draft['font_'+script]=name
            self.section(self.selection)
        except Exception as exc:messagebox.showerror('Font',str(exc),parent=self)
    def sizes(self,p):
        for key,title,a,b in [('ui_scale',self.tx('Масштаб','Zoom'),75,150),('text_size',self.tx('Размер текста','Text size'),75,160),('row_height',self.tx('Высота строк','Row height'),56,80),('button_height',self.tx('Высота кнопок','Button height'),29,65),('sidebar_width',self.tx('Ширина меню','Sidebar width'),200,310),('padding',self.tx('Отступы','Padding'),4,28)]:self.slider(p,key,title,a,b)
    def icons(self,p):
        self.text(p,self.tx('Заменяй значки меню собственными изображениями. Значки грузов меняются в карточке груза.','Choose your menu icon images. Cargo icons are changed in each cargo card.'),10,wraplength=322,justify='left').pack(anchor='w',pady=7)
        for key,ru,en in [('cargo','Грузы','Cargo'),('recipes','Крафт','Crafting'),('calculator','Калькулятор','Calculator'),('manual','Справочник','Guide'),('settings','Настройки','Settings')]:
            line=tk.Frame(p,bg=p.cget('bg'));line.pack(fill='x',pady=4)
            self.text(line,ru if self.ru else en,10).pack(side='left')
            self.button(line,'PNG',lambda k=key:self.pick_icon(k)).pack(side='right')
        self.button(p,self.tx('Вернуть стандартные значки','Restore default icons'),lambda:self.set('nav_icons',{})).pack(anchor='w',pady=10)
    def pick_icon(self,key):
        name=filedialog.askopenfilename(parent=self,filetypes=[('Images','*.png *.jpg *.webp')]);
        if name:
            d=dict(self.draft['nav_icons']);d[key]=name;self.set('nav_icons',d)
    def animations(self,p):
        for key,ru,en in [('animations','Включить анимации','Enable animations'),('hover_glow','Мягкое свечение','Soft hover glow'),('slide_detail','Выдвижение карточки','Slide-in details'),('smooth_select','Плавное выделение','Smooth selection')]:self.check(p,key,ru if self.ru else en)
        self.slider(p,'animation_speed',self.tx('Скорость эффектов','Animation speed'),30,250)
    def themes(self,p):
        self.caption(p,self.tx('Встроенные игровые темы','Built-in game themes'))
        for code,value in PRESETS.items():
            self.button(p,value['ru' if self.ru else 'en'],lambda k=code:self.pick_preset(k)).pack(fill='x',pady=3)
        self.caption(p,self.tx('Мои темы','My themes'))
        for name,path in list_themes()[:7]:
            self.button(p,name,lambda path=path:self.load_saved(path)).pack(fill='x',pady=2)
        if self.selected_theme_folder:
            self.button(p,self.tx('Обновить выбранную тему','Update selected theme'),self.update_saved).pack(fill='x',pady=3)
            self.button(p,self.tx('Удалить выбранную тему','Delete selected theme'),self.delete_saved).pack(fill='x',pady=3)
        self.button(p,self.tx('Сохранить как новую…','Save as new…'),self.save_custom).pack(fill='x',pady=(14,4))
    def load_saved(self,path):
        try:self.draft=open_theme(path);self.selected_theme_folder=path;self.section(self.selection)
        except Exception as exc:messagebox.showerror('Theme',str(exc),parent=self)
    def update_saved(self):
        folder=self.selected_theme_folder
        if not folder:return
        try:
            title=json.loads((folder/'theme.json').read_text(encoding='utf8')).get('name','Моя тема')
            new_folder=save_theme(title,self.draft)
            shutil.rmtree(folder)
            self.selected_theme_folder=new_folder
            self.section(self.selection)
        except Exception as exc:messagebox.showerror('Theme',str(exc),parent=self)
    def delete_saved(self):
        folder=self.selected_theme_folder
        if folder and messagebox.askyesno('Theme',self.tx('Удалить эту пользовательскую тему?','Delete this custom theme?'),parent=self):
            try:shutil.rmtree(folder);self.selected_theme_folder=None;self.section(self.selection)
            except Exception as exc:messagebox.showerror('Theme',str(exc),parent=self)
    def reset(self):self.draft=preset_config('snow');self.section(self.selection)
    def save_custom(self):
        from tkinter import simpledialog
        name=simpledialog.askstring('Theme',self.tx('Название новой темы:','New theme name:'),parent=self)
        if not name:return
        try:
            save_theme(name,self.draft)
            messagebox.showinfo('Theme',self.tx('Тема сохранена.','Theme saved.'),parent=self)
            self.section(self.selection)
        except Exception as exc:messagebox.showerror('Theme',str(exc),parent=self)
    def export(self):
        fn=filedialog.asksaveasfilename(parent=self,defaultextension='.zip',filetypes=[('ZIP','*.zip')]);
        if fn:
            try:export_theme(self.draft,fn);messagebox.showinfo('Theme',self.tx('Тема экспортирована.','Theme exported.'),parent=self)
            except Exception as exc:messagebox.showerror('Theme',str(exc),parent=self)
    def import_zip(self):
        fn=filedialog.askopenfilename(parent=self,filetypes=[('ZIP','*.zip')]);
        if fn:
            try:self.draft=open_theme(import_theme(fn));self.section(self.selection)
            except Exception as exc:messagebox.showerror('Theme',str(exc),parent=self)
    def apply(self):
        self.app.apply_appearance(self.draft)
        self.destroy()
    def change_preview_mode(self,index):
        self.preview_mode=['cargo','recipes','settings'][index]
        self.draw_preview()

    def open_preview_window(self):
        """A non-destructive enlarged preview: no settings change until Apply."""
        if self.preview_popup is not None and self.preview_popup.winfo_exists():
            self.preview_popup.lift()
            self.draw_preview()
            return
        self.preview_popup=tk.Toplevel(self)
        self.preview_popup.title(self.tx('Предпросмотр — НЕ СОХРАНЕНО','Live preview — NOT SAVED'))
        screenw,screenh=self.winfo_screenwidth(),self.winfo_screenheight()
        self.preview_popup.geometry(f'{min(1120,screenw-90)}x{min(740,screenh-110)}')
        self.preview_popup.configure(bg='#111A20')
        self.preview_popup.transient(self)
        top=tk.Frame(self.preview_popup,bg='#16242B');top.pack(fill='x')
        self.text(top,self.tx('ПРЕДПРОСМОТР • ЕЩЁ НЕ СОХРАНЕНО','LIVE PREVIEW • NOT SAVED'),12,bold=True,color='#FFC21B').pack(side='left',padx=14,pady=10)
        self.button(top,self.tx('Закрыть предпросмотр','Close preview'),self.close_preview_window).pack(side='right',padx=12,pady=6)
        self.preview_popup_canvas=tk.Canvas(self.preview_popup,bg='#0C141A',highlightthickness=0)
        self.preview_popup_canvas.pack(fill='both',expand=True,padx=15,pady=(14,15))
        self.preview_popup_canvas.bind('<Configure>',lambda e:self.draw_preview())
        self.preview_popup.protocol('WM_DELETE_WINDOW',self.close_preview_window)
        # Keep both windows usable while editing. The original editor owns
        # a grab by default; release it for a secondary preview surface.
        try:self.grab_release()
        except tk.TclError:pass
        self.draw_preview()

    def close_preview_window(self):
        if self.preview_popup and self.preview_popup.winfo_exists():
            self.preview_popup.destroy()
        self.preview_popup=None;self.preview_popup_canvas=None
        try:
            if self.winfo_exists():self.grab_set()
        except tk.TclError:pass

    def _preview_font(self,size,bold=False,latin=False):
        key='font_latin' if latin else 'font_cyrillic'
        candidate=self.draft.get(key)
        paths=[candidate] if candidate else []
        paths+=['C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
        for path in paths:
            if path and Path(path).is_file():
                try:return ImageFont.truetype(str(path),int(size))
                except (OSError,ValueError):pass
        return ImageFont.load_default()

    def _render_preview_image(self):
        """Render a draft design without mutating the running app configuration."""
        d=normalize(self.draft)
        width,height=960,580
        try:
            path=asset_path(d,'background')
            base=ImageOps.fit(Image.open(path).convert('RGB'),(width,height),Image.Resampling.LANCZOS)
        except Exception:
            base=Image.new('RGB',(width,height),'#10202A')
        if d.get('header_image') and Path(d['header_image']).is_file():
            try:
                header=ImageOps.fit(Image.open(d['header_image']).convert('RGB'),(width,145),Image.Resampling.LANCZOS)
                base.paste(header,(0,0))
            except OSError:pass
        a=Image.new('RGBA',(width,height),(0,0,0,0))
        draw=ImageDraw.Draw(a)
        accent=d['accent'];panel=d['panel'];row=d['row'];fg=d['fg'];muted=d['muted'];border=d['border']
        opacity=int(d['panel_alpha']/100*255)
        inset=d['padding'];radius=d['corner_radius']
        nav=int(d['sidebar_width']*.72)
        z=d['ui_scale']/100
        textz=d['text_size']/100
        def box(xy,color,alpha=255,r=7,stroke=None):
            fill=ImageColor.getrgb(color)+(int(alpha),)
            rr=max(0,min(r,25))
            draw.rounded_rectangle(xy,radius=rr,fill=fill,outline=stroke,width=2 if stroke else 1)
        def label(x,y,t,size=14,color=None,bold=False,latin=False):
            font=self._preview_font(max(8,int(size*textz*z)),bold,latin)
            draw.text((x,y),t,font=font,fill=(color or fg),stroke_width=0)
        # Screenshot-inspired header and dark panels, but all draft colors are live.
        box((0,0,width,82),'#091218',130,0)
        label(16,16,'SNOWRUNNER',24,'#FFFFFF',True,True)
        label(17,48,'HELPER  /  GAME EDITION',14,accent,True,True)
        # The same full-width matte as the main app prevents a thin band of
        # snow scenery appearing between the sidebar and the preview content.
        box((10,98,width-13,560),panel,opacity,9)
        box((10,98,nav-2,560),'#111B20',opacity,9)
        box((nav+12,98,width-13,560),panel,opacity,10)
        entries=['Грузы','Крафт','Калькулятор','Справочник','Настройки'] if self.ru else ['Cargo','Craft','Calculator','Guide','Settings']
        for i,navname in enumerate(entries):
            y=493 if i==4 else 135+i*75
            box((19,y,nav-12,y+53),accent if i==0 else '#202C32',250 if i==0 else 220,6)
            ico_key=['cargo','recipes','calculator','manual','settings'][i]
            custom=d['nav_icons'].get(ico_key)
            iconpath=Path(custom) if custom and Path(custom).is_file() else ROOT/'assets'/'ui'/'nav'/f'{ico_key}.png'
            if iconpath.is_file():
                try:
                    icon=Image.open(iconpath).convert('RGBA');icon.thumbnail((34,34),Image.Resampling.LANCZOS)
                    a.alpha_composite(icon,(25,y+9))
                except OSError:pass
            label(66,y+16,navname,14,'#151A1C' if i==0 else fg,True)
        label(nav+29,110,{'cargo':'КАТАЛОГ ГРУЗОВ','recipes':'РЕЦЕПТЫ КРАФТА','settings':'НАСТРОЙКИ'}[self.preview_mode] if self.ru else {'cargo':'CARGO LIST','recipes':'CRAFTING','settings':'SETTINGS'}[self.preview_mode],21,fg,True)
        x0=nav+26; panel_right=width-22
        left_right=min(625,round(nav+(width-nav)*.58))
        box((x0,159,left_right,201),row,230,6,border)
        label(x0+12,170,'⌕  Поиск груза...' if self.ru else '⌕  Search cargo...',14,muted)
        options={'cargo':['Металлические балки','Деревянные доски','Бетонные плиты','Бочки с топливом'],
                 'recipes':['Металлические балки','Бетонные блоки','Рельсовая секция','Бытовка'],
                 'settings':['Оформление','Цвета','Шрифты','Анимации']}[self.preview_mode]
        if not self.ru:
            options={'cargo':['Metal beams','Wooden planks','Concrete slabs','Fuel barrels'],
                 'recipes':['Metal beams','Concrete blocks','Rail section','Cabin'],
                 'settings':['Appearance','Colors','Fonts','Animations']}[self.preview_mode]
        rowh=max(48,min(75,d['row_height']*.82))
        for i,nm in enumerate(options):
            y=int(218+i*(rowh+8))
            box((x0,y,left_right,y+rowh),('#594B22' if i==0 else row),240,7,accent if i==0 else border)
            label(x0+12,y+16,nm,13,fg,i==0)
            label(left_right-45,y+16,str([2,1,2,1][i]),12,accent,True)
        xdetail=left_right+13
        box((xdetail,159,panel_right,531),row,225,8,border)
        box((xdetail+9,173,panel_right-9,217),accent,240,5)
        label(xdetail+17,183,options[0][:29],15,'#141819',True)
        # Dynamic preview of icon color, text scaling and layout dimensions.
        cargoimage=ROOT/'assets'/'cargo'/'metal_beams.png'
        if cargoimage.exists():
            try:
                icon=Image.open(cargoimage).convert('RGBA');icon.thumbnail((160,100),Image.Resampling.LANCZOS)
                a.alpha_composite(icon,(xdetail+max(12,(panel_right-xdetail-icon.width)//2),230))
            except OSError:pass
        label(xdetail+17,353,'Размер: 2 слота' if self.ru else 'Size: 2 slots',13,fg)
        label(xdetail+17,391,'Тип: строительный' if self.ru else 'Type: construction',13,muted)
        label(xdetail+17,442,'Используется в крафте' if self.ru else 'Used in crafting',13,accent,True)
        box((xdetail+12,477,panel_right-12,521),panel,240,6)
        label(xdetail+19,485,'Бытовка  ›' if self.ru else 'Cabin  ›',12,fg)
        label(20,height-13,'ПРЕДПРОСМОТР • НЕ СОХРАНЕНО' if self.ru else 'PREVIEW • NOT SAVED',11,accent,True)
        composed=Image.alpha_composite(base.convert('RGBA'),a)
        return composed.convert('RGB')

    def draw_preview(self):
        targets=[]
        if hasattr(self,'preview') and self.preview.winfo_exists():targets.append(self.preview)
        if self.preview_popup_canvas and self.preview_popup_canvas.winfo_exists():targets.append(self.preview_popup_canvas)
        if not targets:return
        picture=self._render_preview_image()
        for canvas in targets:
            w,h=canvas.winfo_width(),canvas.winfo_height()
            if w<100 or h<100:continue
            rendered=ImageOps.contain(picture,(w,h),Image.Resampling.LANCZOS)
            img=ImageTk.PhotoImage(rendered,master=canvas)
            self._preview_images[canvas]=img
            canvas.delete('all')
            canvas.create_image(w//2,h//2,image=img,anchor='center')
            canvas.create_rectangle(1,1,w-2,h-2,outline=self.draft['accent'],width=1)
