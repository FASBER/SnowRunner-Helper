"""SnowRunner Helper 0.31.16: conservative UI + functionality upgrade.

Installs after v0.31.15 approved canvas/workspace adapters. Does not modify
save files, original cargo catalog, recipes or OTA verification. All additional
asset placeholders are explicit; no generated truck images or fabricated data.
"""
from __future__ import annotations

from pathlib import Path
import math
import sys
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

_BG='#071923'
_CARD='#102A36'
_FIELD='#183744'
_BORDER='#365664'
_FG='#F3F5F1'
_MUTED='#A8BAC4'
_GOLD='#FFC21B'

_SORTS=[
 ('name_asc','Название А–Я','Name A–Z'),
 ('name_desc','Название Я–А','Name Z–A'),
 ('slots_asc','Слоты: меньше','Slots: low to high'),
 ('slots_desc','Слоты: больше','Slots: high to low'),
 ('weight_asc','Вес: меньше','Weight: low to high'),
 ('weight_desc','Вес: больше','Weight: high to low'),
 ('category_asc','По категории А–Я','Category A–Z'),
 ('category_desc','По категории Я–А','Category Z–A'),
]
_INSTALLED=False


def weight_kg(record):
    """Return only attested weights; for an attested range use lower bound."""
    from cargo_weight_v317 import verified_mass_t, MAPRUNNER_PACKED_MASS_KG
    mass=verified_mass_t(record)
    if mass is not None:return mass*1000
    value=MAPRUNNER_PACKED_MASS_KG.get(record.get('id'))
    if isinstance(value,tuple) and value:
        value=value[0]
    if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0:
        return float(value)
    return None


def sort_entries(entries, mode='name_asc', lang='ru'):
    from core import _sort_name, sort_cargo as _current
    if mode in ('name_asc','name_desc','slots_asc','slots_desc'):
        # Keep official core behavior stable for the existing four modes.
        if getattr(_current,'_v316_enhanced',False):
            return _current._old(entries,mode,lang)
        return _current(entries,mode,lang)
    if mode in ('weight_asc','weight_desc'):
        sign=1 if mode=='weight_asc' else -1
        return sorted(entries,key=lambda r:(weight_kg(r) is None,
                        (weight_kg(r) or 0)*sign,_sort_name(r,lang),r['id']))
    if mode in ('category_asc','category_desc'):
        # Stable grouping with alphabetical name within each category.
        def category(entry):
            return str(entry.get('category') or 'Не определено').casefold()
        return sorted(entries,key=lambda r:(category(r),_sort_name(r,lang),r['id']),
                      reverse=mode=='category_desc')
    return _current._old(entries,'name_asc',lang) if getattr(_current,'_v316_enhanced',False) else _current(entries,'name_asc',lang)


def _install_sort():
    import core,game_ui,app
    if getattr(core.sort_cargo,'_v316_enhanced',False):return
    original=core.sort_cargo
    def improved(entries,mode='name_asc',lang='ru'):
        return sort_entries(entries,mode,lang)
    improved._v316_enhanced=True
    improved._old=original
    core.sort_cargo=improved
    game_ui.sort_cargo=improved
    app.sort_cargo=improved
    core.SORT_MODES=tuple(k for k,_,_ in _SORTS)
    game_ui.SORT_MODES=core.SORT_MODES
    app.SORT_MODES=core.SORT_MODES


def _draw_filters(self):
    import approved_reference_v311 as ref
    ru=self.lang=='ru'
    # Keep every filter label readable in a fixed-width two-row grid.
    # The original toolbar occupies the same rectangle; repaint only that
    # region, not the approved title, list, row art or detail card.
    self.rect(203,219,900,305,_BG)
    self.round(207,225,452,257,5,_FIELD,_BORDER)
    cx,cy=224,241
    px,py=self.p(cx,cy)
    rad=max(2,int(7*self.scale))
    self.canvas.create_oval(px-rad,py-rad,px+rad,py+rad,
        outline=self.ui_color(_GOLD),width=max(1,int(2*self.scale)))
    x1,y1=self.p(cx+5,cy+5);x2,y2=self.p(cx+10,cy+10)
    self.canvas.create_line(x1,y1,x2,y2,fill=self.ui_color(_GOLD),width=max(1,int(2*self.scale)))
    self.txt(467,241,'Сортировка' if ru else 'Sort',9,_FG,limit=95)
    self.round(565,225,895,257,5,'#0E2732',_BORDER)
    current=self.app.config.get('sort','name_asc')
    caption=next((r if ru else en for k,r,en in _SORTS if k==current),_SORTS[0][1 if ru else 2])
    self.txt(576,241,caption,12,_FG,limit=284)
    self.txt(879,241,'⌄',16,_FG,anchor='center')
    self.hit(565,225,895,257,lambda:self.toggle('ref_sort'),('btn','sort'))
    # Region, Map and Category: equal 32 px high controls, aligned baselines.
    self.txt(208,283,'Регион:' if ru else 'Region:',11,_FG,limit=71)
    self.round(285,267,451,299,5,'#0E2732',_BORDER)
    region=getattr(self,'_v311_filter_region','')
    self.txt(294,283,ref._location_label(region,self.lang) if region else
             ('Все регионы' if ru else 'All regions'),11,_FG,limit=128)
    self.txt(438,283,'⌄',16,_FG,anchor='center')
    self.hit(285,267,451,299,lambda:ref._show_location_popup(self,'v311_regions'),('btn','regions'))
    self.txt(462,283,'Карта' if ru else 'Map',10,_FG,limit=47)
    self.round(512,267,648,299,5,'#0E2732',_BORDER)
    map_filter=getattr(self,'_v311_filter_map','')
    self.txt(521,283,ref._location_label(map_filter,self.lang) if map_filter else
             ('Все карты' if ru else 'All maps'),11,_FG,limit=114)
    self.txt(636,283,'⌄',16,_FG,anchor='center')
    self.hit(512,267,648,299,lambda:ref._show_location_popup(self,'v311_maps'),('btn','maps'))
    self.txt(658,283,'Категория' if ru else 'Category',9,_FG,limit=88)
    self.round(752,267,895,299,5,'#0E2732',_BORDER)
    name=self._reference_category_name(self.cargo_category) if self.cargo_category else ('Все категории' if ru else 'All categories')
    self.txt(761,283,name,9,_FG,limit=106)
    self.txt(883,283,'⌄',16,_FG,anchor='center')
    self.hit(752,267,895,299,lambda:self.toggle('ref_category'),('btn','category'))


def _popup(self):
    if getattr(self,'reference_ui',False) and self.page=='cargo' and self.popup=='ref_sort':
        ru=self.lang=='ru'
        x,y,w,row=565,257,330,29
        self.round(x,y,x+w,y+row*len(_SORTS)+10,6,'#0E2531','#456978')
        for index,(key,r,en) in enumerate(_SORTS):
            a=y+5+index*row
            sel=self.app.config.get('sort','name_asc')==key
            self.round(x+4,a,x+w-5,a+row-2,4,'#6C521A' if sel else '#183A47')
            self.txt(x+13,a+row/2,r if ru else en,11,_FG,limit=w-28)
            self.hit(x+4,a,x+w-5,a+row,lambda k=key:self.choose_sort(k),('popup',key))
        return
    return self._v316_previous_popup()


def _draw_cargo(self):
    original=self._v316_previous_cargo
    original()
    if not getattr(self,'reference_ui',False) or getattr(self,'_approved_extra',None):return
    self.hitboxes=[h for h in self.hitboxes if not (isinstance(h[-1],tuple) and
        h[-1] in {('btn','sort'),('btn','maps'),('btn','regions'),('btn','category')})]
    _draw_filters(self)


def _choose_sort(self,value):
    if value not in {x[0] for x in _SORTS}:
        return
    # The old Application validates only four legacy modes during startup.
    # Keep a separate durable expedition sort choice to survive that validation.
    self.app.config['expedition_sort_mode']=value
    return self._v316_previous_choose_sort(value)


def _redraw(self):
    if not getattr(self,'_v316_sort_restored',False):
        restore_sort_preference(self.app)
        self._v316_sort_restored=True
    output=self._v316_previous_redraw()
    if not getattr(self,'reference_ui',False):return output
    _schedule_release_notes(self)
    if self.page=='cargo' and not getattr(self,'_approved_extra',None):
        x,y=self.p(251,228)
        self.search_entry.place(x=int(x),y=int(y),width=max(20,int(189*self.sx)),
                                height=max(19,int(27*self.sy)))
        self.search_entry.configure(bg=_FIELD,fg=_FG,
            insertbackground=_GOLD,insertwidth=1,insertontime=600,
            insertofftime=600)
        if not self.search.get() and self.root.focus_get()!=self.search_entry:
            x,y=self.p(260,230)
            self.search_placeholder.configure(bg=_FIELD,anchor='w',text='Поиск грузов…' if self.lang=='ru' else 'Search cargo…')
            self.search_placeholder.place(x=int(x),y=int(y),
                width=max(30,int(179*self.sx)),height=max(19,int(26*self.sy)))
            self.search_placeholder.lift()
    return output


def _schedule_release_notes(self):
    # The notification is displayed once for each actual installed version.
    # Toplevel creation is deferred until the original Application constructor
    # has also created its updater and overlay components.
    if getattr(self,'_v316_release_notes_scheduled',False):return
    self._v316_release_notes_scheduled=True
    def check():
        try:
            from update_config import CURRENT_VERSION
            from core import SETTINGS_FILE, save_json
            config=self.app.config
            if config.get('last_release_notes_version')==CURRENT_VERSION:return
            from changelog_ui_v316 import load_notes
            if not any(note.get('version')==CURRENT_VERSION for note in load_notes()):return
            # Record the version only once the window has been constructed.
            self.about_dialog()
            config['last_release_notes_version']=CURRENT_VERSION
            try:save_json(SETTINGS_FILE,config)
            except (OSError,TypeError,ValueError):pass
        except (AttributeError,RuntimeError,ImportError,TypeError):return
    self.root.after(2200,check)


def _draw_nav(self):
    if not getattr(self,'reference_ui',False):return self._v316_previous_nav()
    import approved_reference_v311 as ref
    ru=self.lang=='ru'
    items=[('home','Главная','Home',185),('cargo','Грузы','Cargo',242),
           ('recipes','Крафт','Craft',299),('garage','Гараж','Garage',356),
           ('calculator','Калькулятор','Calculator',413),('settings','Настройки','Settings',659)]
    current=getattr(self,'_approved_extra',None) or self.page
    for key,r,en,y in items:
        selected=key==current
        self.round(9,y,176,y+46,7,'#214353' if selected else '#102733',
                   _GOLD if selected else '#35515D',2 if selected else 1)
        ref._nav_icon(self,key,38,y+23,selected)
        self.txt(64,y+23,r if ru else en,11 if key=='calculator' else 12,_FG,selected,limit=111)
        self.hit(9,y,176,y+46,lambda target=key:ref._action(self,target),('nav',key))
    # No previous white decorative line over the navigation.


def _draw_toolbar(self):
    if not getattr(self,'reference_ui',False):return self._v316_previous_toolbar()
    from player_identity_v316 import display_profile,edit_profile_name
    import approved_reference_v311 as ref
    ru=self.lang=='ru'
    values=ref._stats(self)
    # One shared baseline and equal divider lengths. Bounded labels avoid clipping.
    self.txt(210,137,'Игрок:' if ru else 'Player:',12,_MUTED)
    self.txt(273,137,display_profile(self.app),12,_FG,True,limit=195)
    self.hit(210,117,468,158,lambda:edit_profile_name(self.app),('btn','profile_alias'))
    for x in (475,646,878):self.line(x,119,x,159,'#365563')
    self.txt(499,137,'★',23,_GOLD,True,anchor='center')
    self.txt(520,124,'Опыт' if ru else 'XP',10,_MUTED)
    self.txt(520,147,ref._number(values['exp']),17,_FG,True)
    self.txt(677,137,'▣',20,_GOLD,True,anchor='center')
    self.txt(702,124,'Баланс' if ru else 'Balance',10,_MUTED)
    money=ref._number(values['money'])
    self.txt(702,147,(money+' ₵') if values['money'] is not None else '—',17,_FG,True,limit=171)
    self.txt(895,137,'Выполнено:' if ru else 'Completed:',11,_MUTED)
    self.txt(1002,137,ref._number(values['objectives']),16,_FG,True,limit=99)
    self.round(1109,117,1283,154,6,'#193A47','#50707A')
    self.txt(1196,136,'⟳  ОБНОВИТЬ' if ru else '⟳  REFRESH',12,_FG,True,anchor='center')
    self.hit(1109,117,1283,154,self.app.refresh_game_data,('btn','refresh_game'))
    # Native-looking hover colors in title strip; no geometry changes on hover.
    controls=[('min',1199,1224,lambda:self.minimize_window(),'—','#28516D','#64C7FF'),
              ('max',1230,1270,lambda:self.toggle_maximize(),'□','#235643','#A9F2CD'),
              ('close',1272,1318,self.app.close_app,'×','#A3363B','#FFFFFF')]
    for key,x1,x2,action,glyph,bg,fg in controls:
        if self.hover==('btn',key):
            self.rect(x1,0,x2,25,bg)
            self.txt((x1+x2)/2,12,glyph,18,fg,True,anchor='center')
        self.hit(x1,0,x2,25,action,('btn',key))


def _settings_slider(self,label,key,y):
    """Single baseline without overlap between number and +/- controls."""
    value=self.app.config.get(key,100)
    self.txt(762,y,label,13,_FG,True,limit=229)
    self.txt(1058,y,str(value)+'%',13,_GOLD,True,anchor='e',limit=67)
    self.button(1074,y-16,1123,y+16,'−',lambda k=key:self.app.adjust(k,-10),small=True)
    self.button(1130,y-16,1179,y+16,'+',lambda k=key:self.app.adjust(k,10),small=True)
    self.button(1186,y-16,1268,y+16,'100%',lambda k=key:self.change(k,100),small=True)
    track=506
    self.round(762,y+24,762+track,y+28,2,'#405965')
    span=65 if key=='ui_scale' else 75
    fill=max(0,min(1,(value-75)/span))
    if fill:self.round(762,y+24,762+track*fill,y+28,2,_GOLD)


def _draw_settings(self):
    if not getattr(self,'reference_ui',False):return self._v316_previous_settings()
    ru=self.lang=='ru'
    self.round(202,179,1290,713,7,'#0A202B','#355665')
    self.txt(224,206,'НАСТРОЙКИ' if ru else 'SETTINGS',26,_FG,True)
    self.line(224,223,1265,223,_BORDER)
    # Two balanced independent columns. Everything fits inside y=713.
    self.txt(224,247,'ОФОРМЛЕНИЕ' if ru else 'APPEARANCE',17,_GOLD,True)
    self.round(218,266,730,424,8,'#142E3A','#385863')
    self.txt(239,295,'SnowRunner Game Edition',19,_FG,True)
    from appearance import PRESETS
    preset=PRESETS.get(self.appearance.get('preset','snow'),PRESETS['snow'])
    self.txt(239,325,preset['ru' if ru else 'en'],13,_MUTED)
    self.txt(239,354,'Темы • цвета • фон • шрифты • размеры' if ru else
             'Themes • colors • background • fonts • sizes',11,_MUTED,limit=459)
    self.button(237,373,707,414,'⚙  '+('НАСТРОИТЬ ВНЕШНИЙ ВИД' if ru else 'CUSTOMIZE APPEARANCE'),
                self.app.appearance_editor,selected=True,small=True)
    self.txt(224,457,'СЕРВИСНЫЕ ПАРАМЕТРЫ' if ru else 'TOOLS',15,_GOLD,True)
    self.button(218,473,730,514,('О программе и история обновлений' if ru else
                                 'About and release history'),self.about_dialog,small=True)
    self.button(218,525,730,566,('Редактор пользовательских рецептов' if ru else
                                 'Custom recipe editor'),lambda:self.app.recipe_editor(),small=True)
    self.button(218,577,730,618,('Цветовая тема' if ru else 'Color theme')+'  ↻',
                self.cycle_theme,small=True)
    self.button(218,629,730,674,('Подключить игровые файлы SnowRunner' if ru else
                                 'Connect SnowRunner game files'),self.app.game_connection_dialog,small=True)
    self.txt(762,247,'ПАРАМЕТРЫ' if ru else 'PREFERENCES',17,_GOLD,True)
    self.txt(762,285,'Язык интерфейса' if ru else 'Language',12,_MUTED)
    self.button(762,301,1004,343,'Русский',lambda:self.change('lang','ru'),selected=ru,small=True)
    self.button(1014,301,1269,343,'English',lambda:self.change('lang','en'),selected=not ru,small=True)
    _settings_slider(self,'Масштаб интерфейса' if ru else 'Interface zoom','ui_scale',382)
    _settings_slider(self,'Размер текста' if ru else 'Text size','text_size',464)
    self.txt(762,527,'МИНИ-ОКНО КРАФТА' if ru else 'CRAFT OVERLAY',14,_GOLD,True)
    overlay=getattr(self.app,'overlay',None)
    if overlay is not None:
        self.button(762,550,1008,593,'Показать мини-окно' if ru else 'Show overlay',overlay.toggle,small=True)
        self.button(1017,550,1269,593,'Клавиша: '+overlay.shortcut if ru else
                    'Shortcut: '+overlay.shortcut,overlay.shortcut_dialog,small=True)
    self.txt(765,609,'Сочетания работают поверх оконной игры' if ru else
             'Shortcuts work in windowed games',11,_MUTED,limit=492)
    self.button(762,638,1269,685,'↓  '+('ПРОВЕРИТЬ ОБНОВЛЕНИЯ' if ru else 'CHECK FOR UPDATES'),
                self.app.updater.open_settings,small=True)


def _draw_extra(self,page):
    if page!='garage':
        import approved_reference_v311 as ref
        return ref._v316_original_extra(self,page)
    from core import ROOT, USER_DIR
    from player_identity_v316 import display_profile
    from vehicle_catalog_v316 import (fleet_from_source,summary_owned,read_cached_catalog,
                                    evidence_image_path)
    ru=self.lang=='ru'
    self.round(202,179,1290,713,7,'#0A202B','#365461')
    self.txt(223,207,'ГАРАЖ' if ru else 'GARAGE',27,_FG,True)
    self.line(223,224,1267,224,_BORDER)
    tab=getattr(self,'_v316_garage_tab','mine')
    for name,x,title in [('mine',222,'МОЯ ТЕХНИКА' if ru else 'MY FLEET'),
                          ('catalog',475,'КАТАЛОГ ТЕХНИКИ' if ru else 'VEHICLE CATALOG')]:
        selected=name==tab
        self.round(x,244,x+235,281,6,'#5C4618' if selected else '#183744',
                   _GOLD if selected else _BORDER,2 if selected else 1)
        self.txt(x+117,263,title,12,_FG,True,anchor='center')
        self.hit(x,244,x+235,281,lambda n=name:_select_garage_tab(self,n),('btn','garage_'+name))
    self.txt(1265,263,display_profile(self.app),11,_MUTED,anchor='e',limit=325)
    if tab=='mine':
        source=None;snapshot={}
        if self.app.active_profile_key!='local':
            try:
                info=self.app.profiles.read(self.app.active_profile_key)
                source=info.get('source_path')
                snapshot=info.get('game_snapshot') or {}
            except (OSError,ValueError,TypeError,AttributeError):pass
        fleet=[]
        if source:
            try:
                stat=Path(source).stat()
                key=(str(source),stat.st_mtime_ns,stat.st_size)
                if getattr(self,'_v316_fleet_key',None)!=key:
                    self._v316_fleet=fleet_from_source(source)
                    self._v316_fleet_key=key
                fleet=self._v316_fleet
            except (OSError,ValueError,TypeError,KeyError):fleet=[]
        if not fleet:
            fleet=[{'id':row['id'],'where':'На хранении', 'source':'retained_trucks'}
                   for row in summary_owned(snapshot) for _ in range(min(100,row['count']))]
        self.txt(230,308,('Подтверждено машин: ' if ru else 'Verified trucks: ')+str(len(fleet)),13,_MUTED)
        if not fleet:
            self.txt(238,386,'Подключи сохранение, чтобы увидеть свою технику.' if ru else
                     'Connect a game save to see your vehicles.',15,_FG)
            self.button(233,430,623,475,'ПОДКЛЮЧИТЬ СОХРАНЕНИЕ' if ru else 'CONNECT SAVE',
                        self.app.game_connection_dialog,small=True)
        else:
            offset=max(0,min(getattr(self,'_v316_garage_offset',0),max(0,len(fleet)-7)))
            self._v316_garage_offset=offset
            for i,truck in enumerate(fleet[offset:offset+7]):
                _vehicle_row(self,truck['id'],truck['where'],i,ROOT,USER_DIR,'truck')
            _garage_scrollbar(self,len(fleet),offset)
            self.txt(231,684,'Показаны только подтверждённые записи сохранения.' if ru else
                'Only verified save entries are shown.',10,_MUTED)
    else:
        catalog=read_cached_catalog(USER_DIR)
        self.txt(230,311,('Моделей в локальном каталоге: ' if ru else 'Local catalog entries: ')+str(len(catalog)),13,_MUTED)
        if not catalog:
            self.txt(233,373,'Для полного каталога выбери initial.pak установленной игры.' if ru else
                     'Select your game initial.pak to build the offline catalog.',14,_FG,limit=940)
            self.txt(233,404,'Изображения не подменяются выдуманными моделями.' if ru else
                     'Missing vehicle artwork is never replaced by invented images.',11,_MUTED)
            self.button(232,447,665,495,'ИМПОРТИРОВАТЬ ИЗ ИГРЫ' if ru else 'IMPORT FROM GAME',
                        lambda:_import_vehicle_catalog(self),small=True)
        else:
            offset=max(0,min(getattr(self,'_v316_garage_offset',0),max(0,len(catalog)-7)))
            self._v316_garage_offset=offset
            for i,vehicle in enumerate(catalog[offset:offset+7]):
                kind=vehicle['category']
                sub={'truck':'Грузовик','trailer':'Прицеп','semitrailer':'Полуприцеп','addon':'Модуль'}.get(kind,kind)
                _vehicle_row(self,vehicle['id'],sub,i,ROOT,USER_DIR,kind)
            _garage_scrollbar(self,len(catalog),offset)
        self.button(914,659,1258,696,'ОБНОВИТЬ КАТАЛОГ' if ru else 'REFRESH CATALOG',
                    lambda:_import_vehicle_catalog(self),small=True)


def _vehicle_row(self,vehicle_id,where,index,root,user_dir,kind):
    from vehicle_catalog_v316 import evidence_image_path
    y=333+index*47
    self.round(221,y,1268,y+44,5,'#102D38' if index%2 else '#153440','#355663')
    image_path=evidence_image_path(vehicle_id,kind,root,user_dir)
    if image_path is not None:
        try:
            cache=getattr(self,'_v316_vehicle_images',None)
            if cache is None:cache=self._v316_vehicle_images={}
            key=(str(image_path),round(73*self.sx),round(40*self.sy))
            if key not in cache:
                with Image.open(image_path) as f:
                    im=f.convert('RGBA'); im.thumbnail((max(1,key[1]),max(1,key[2])),Image.Resampling.LANCZOS)
                cache[key]=ImageTk.PhotoImage(im,master=self.root)
            self.refs.append(cache[key])
            self.canvas.create_image(*self.p(258,y+22),image=cache[key],anchor='center')
        except (OSError,ValueError):pass
    else:self.txt(246,y+22,'—',19,_MUTED,anchor='center')
    self.txt(300,y+22,vehicle_id.replace('_',' '),13,_FG,True,limit=426)
    self.txt(812,y+22,where,11,_MUTED,limit=407)


def _garage_scrollbar(self,total,offset):
    if total<=7:return
    self.round(1275,332,1283,660,3,'#183944')
    length=max(30,328*7/total)
    yp=333+(328-length)*offset/max(1,total-7)
    self.round(1275,yp,1283,yp+length,3,_GOLD)


def _select_garage_tab(self,key):
    self._v316_garage_tab=key
    self._v316_garage_offset=0
    self.redraw()


def _import_vehicle_catalog(self):
    from vehicle_catalog_v316 import scan_and_cache_catalog
    from core import USER_DIR
    parent=self.root
    path=filedialog.askopenfilename(parent=parent,title='Выберите SnowRunner initial.pak',
          filetypes=[('SnowRunner initial.pak','*.pak'),('All files','*.*')])
    if not path:return
    try:
        records=scan_and_cache_catalog(path,USER_DIR)
    except (OSError,ValueError,RuntimeError,KeyError) as exc:
        messagebox.showerror('SnowRunner Helper',f'Импорт не выполнен:\n{exc}',parent=parent)
        return
    self._v316_garage_offset=0
    self.redraw()
    messagebox.showinfo('SnowRunner Helper',
        f'Прочитано {len(records)} записей из initial.pak. Каталог доступен без интернета.\n'
        'Фотографии не извлечены: их необходимо получить из проверенных источников.',parent=parent)


def _scroll(self,delta):
    if getattr(self,'reference_ui',False) and getattr(self,'_approved_extra',None)=='garage':
        self._v316_garage_offset=max(0,getattr(self,'_v316_garage_offset',0)+int(delta))
        self.redraw();return
    return self._v316_original_scroll(delta)


def _smooth_scroll(self,amount):
    if not getattr(self,'reference_ui',False) or not self.animations_on() or not self.app.config.get('smooth_wheel',True):
        return self._v316_direct_scroll(amount)
    amount=int(amount)
    if not amount:return
    state=getattr(self,'_v316_ease_state',None)
    if state is None:
        state={'page':(self.page,getattr(self,'_approved_extra',None)),'remaining':0,'pending':False}
        self._v316_ease_state=state
    page=(self.page,getattr(self,'_approved_extra',None))
    if page!=state['page']:
        state.update(page=page,remaining=0)
    state['remaining']=max(-240,min(240,state['remaining']+amount))
    if state['pending']:return
    state['pending']=True
    def tick():
        try:
            if not self.canvas.winfo_exists():
                state['pending']=False;return
            if (self.page,getattr(self,'_approved_extra',None))!=state['page']:
                state['remaining']=0;state['pending']=False;return
            remaining=state['remaining']
            if not remaining:
                state['pending']=False;return
            # Two steps per frame if large wheel bursts, one near rest.
            size=min(abs(remaining), 3 if abs(remaining)>8 else 2 if abs(remaining)>3 else 1)
            step=(1 if remaining>0 else -1)*size
            state['remaining']-=step
            self._v316_direct_scroll(step)
            if state['remaining']:
                self.root.after(24,tick)
            else:state['pending']=False
        except (AttributeError,RuntimeError,TypeError):
            state['pending']=False
    try:self.root.after(12,tick)
    except (AttributeError,RuntimeError):state['pending']=False


def _wheel_editor(self, event):
    """Animated fractional scrolling in the appearance editor, including children."""
    try:
        canvas=self.content_canvas
        x,y=event.x_root,event.y_root
        if not (canvas.winfo_rootx()<=x<canvas.winfo_rootx()+canvas.winfo_width() and
                canvas.winfo_rooty()<=y<canvas.winfo_rooty()+canvas.winfo_height()):return None
        direction=(1 if getattr(event,'num',None)==4 else -1 if getattr(event,'num',None)==5 else
                   (1 if getattr(event,'delta',0)>0 else -1))
        y0,y1=canvas.yview()
        visible=max(.0001,y1-y0)
        current=getattr(self,'_v316_scroll_target',y0)
        target=max(0,min(1-visible,current-direction*visible*.18))
        self._v316_scroll_target=target
        if getattr(self,'_v316_scroll_job',None):return 'break'
        def step():
            now=canvas.yview()[0]
            dst=self._v316_scroll_target
            gap=dst-now
            if abs(gap)<.0005:
                canvas.yview_moveto(dst);self._v316_scroll_job=None;return
            canvas.yview_moveto(now+gap*.33)
            self._v316_scroll_job=self.after(16,step)
        self._v316_scroll_job=self.after(16,step)
        return 'break'
    except (AttributeError,TypeError):return None


def install_expedition_upgrade(cls):
    global _INSTALLED
    if _INSTALLED:return
    _install_sort()
    import approved_reference_v311 as ref
    from player_identity_v316 import display_profile
    original_stats=ref._stats
    def updated_stats(self):
        data=original_stats(self)
        data['profile']=display_profile(self.app)
        return data
    ref._stats=updated_stats
    if getattr(cls,'_expedition_v316_installed',False):return
    cls._v316_previous_nav=cls.draw_nav
    cls._v316_previous_toolbar=cls.draw_toolbar
    cls._v316_previous_cargo=cls._draw_reference_cargo
    cls._v316_previous_popup=cls._draw_reference_popup
    cls._v316_previous_redraw=cls.redraw
    cls._v316_previous_settings=cls.draw_settings
    cls._v316_previous_choose_sort=cls.choose_sort
    cls._v316_original_scroll=cls.scroll
    cls._v316_direct_scroll=_scroll
    cls._v316_previous_about=cls.about_dialog
    cls.draw_nav=_draw_nav
    cls.draw_toolbar=_draw_toolbar
    cls._draw_reference_cargo=_draw_cargo
    cls._draw_reference_popup=_popup
    cls.draw_settings=_draw_settings
    cls.choose_sort=_choose_sort
    cls.redraw=_redraw
    cls.scroll=_smooth_scroll
    from changelog_ui_v316 import show_about
    cls.about_dialog=lambda self:show_about(self)
    if not hasattr(ref,'_v316_original_extra'):
        ref._v316_original_extra=ref._draw_extra
        ref._draw_extra=_draw_extra
    cls._expedition_v316_installed=True
    _INSTALLED=True
    # Restore modes disabled by legacy Application startup validation.
    # This is stored in a separate key, so older releases remain compatible.
    try:
        from appearance import AppearanceEditor
        if not getattr(AppearanceEditor,'_expedition_editor_scroll_v316',False):
            AppearanceEditor._v316_scroll_editor=_wheel_editor
            old_init=AppearanceEditor.__init__
            def new_init(self,*args,**kw):
                old_init(self,*args,**kw)
                self.content_canvas.bind('<MouseWheel>',self._v316_scroll_editor)
                self.content_canvas.bind('<Button-4>',self._v316_scroll_editor)
                self.content_canvas.bind('<Button-5>',self._v316_scroll_editor)
                self.bind('<MouseWheel>',self._v316_scroll_editor)
                self.bind('<Button-4>',self._v316_scroll_editor)
                self.bind('<Button-5>',self._v316_scroll_editor)
            AppearanceEditor.__init__=new_init
            AppearanceEditor._expedition_editor_scroll_v316=True
    except ImportError:pass


def restore_sort_preference(app):
    mode=app.config.get('expedition_sort_mode')
    if mode in {s[0] for s in _SORTS}:
        app.config['sort']=mode
