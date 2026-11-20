"""SnowRunner v0.31.13: coordinate-safe workspace and approved-UI preview.

No changes to save files, cargo numbers, recipe imports or OTA behavior.
The original canvas buttons and item callbacks remain in use.
"""
from __future__ import annotations

from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor

_INSTALLED = False
# Original (v0.31.11) new-UI pages were placed at y=129..735, covering the
# approved profile strip (y=110..166). Fit the *whole* page into y=176..717.
_TOP_SOURCE, _BOTTOM_SOURCE = 129.0, 735.0
_TOP_TARGET, _BOTTOM_TARGET = 177.0, 718.0
_FACTOR = (_BOTTOM_TARGET-_TOP_TARGET)/(_BOTTOM_SOURCE-_TOP_SOURCE)
_LEFT_SOURCE,_RIGHT_SOURCE = 262.0,1305.0
_LEFT_TARGET,_RIGHT_TARGET = 197.0,1295.0
_X_FACTOR = (_RIGHT_TARGET-_LEFT_TARGET)/(_RIGHT_SOURCE-_LEFT_SOURCE)

def fitted_x(x):
    return _LEFT_TARGET+(float(x)-_LEFT_SOURCE)*_X_FACTOR

def source_x(x):
    return _LEFT_SOURCE+(float(x)-_LEFT_TARGET)/_X_FACTOR



def fitted_y(y):
    return _TOP_TARGET + (float(y)-_TOP_SOURCE)*_FACTOR


def source_y(y):
    return _TOP_SOURCE + (float(y)-_TOP_TARGET)/_FACTOR


def _fitted_page(original):
    def draw(self, *args, **kwargs):
        if not getattr(self,'reference_ui',False) or self.page=='cargo':
            return original(self,*args,**kwargs)
        # Render is a temporary local transform, never a mutation of real app
        # configuration, recipe coordinates, or registered click callbacks.
        oldp=self.p; oldhit=self.hit
        previous_p=self.__dict__.get('p',None)
        previous_hit=self.__dict__.get('hit',None)
        self.p=lambda x,y: oldp(fitted_x(x),fitted_y(y))
        self.hit=lambda a,b,c,d,fn,tag=None:oldhit(fitted_x(a),fitted_y(b),fitted_x(c),fitted_y(d),fn,tag)
        try:
            return original(self,*args,**kwargs)
        finally:
            if previous_p is None:self.__dict__.pop('p',None)
            else:self.p=previous_p
            if previous_hit is None:self.__dict__.pop('hit',None)
            else:self.hit=previous_hit
    draw.__name__=getattr(original,'__name__','fitted_page')
    return draw


def _place_search_widgets(self):
    """The old redraw places live Tk entries at untransformed coordinates."""
    if not getattr(self,'reference_ui',False):return
    if self.page in ('recipes','manual'):
        baseline=188.0
        left=327.0
        main=self.search_entry
        secondary=self.search_placeholder
        baseline_placeholder=190.0
    elif self.page=='calculator':
        baseline=194.0
        left=285.0
        main=self.calc_search_entry
        secondary=self.calc_search_placeholder
        baseline_placeholder=196.0
    else:return
    try:
        if main.winfo_manager()=='place':
            main.place_configure(x=round(self.p(fitted_x(left),0)[0]),y=round(fitted_y(baseline)*self.sy+self.oy))
        if secondary.winfo_manager()=='place':
            secondary.place_configure(x=round(self.p(fitted_x(left+9),0)[0]),y=round(fitted_y(baseline_placeholder)*self.sy+self.oy))
    except (AttributeError,KeyError):pass


def _scrollbar_click(original):
    def click(self,x,y1,y2,total,visible):
        if not getattr(self,'reference_ui',False) or self.page=='cargo':
            return original(self,x,y1,y2,total,visible)
        previous=self.__dict__.get('local',None)
        oldlocal=self.local
        def reverse(xp,yp):
            result=oldlocal(xp,yp)
            return (source_x(result[0]),source_y(result[1])) if result else result
        self.local=reverse
        try:return original(self,x,y1,y2,total,visible)
        finally:
            if previous is None:self.__dict__.pop('local',None)
            else:self.local=previous
    return click


def _wheel(original):
    def scroll(self,event):
        if not getattr(self,'reference_ui',False) or self.page=='cargo':
            return original(self,event)
        oldlocal=self.local
        previous=self.__dict__.get('local',None)
        def reverse(px,py):
            location=oldlocal(px,py)
            return (source_x(location[0]),source_y(location[1])) if location else location
        self.local=reverse
        try:return original(self,event)
        finally:
            if previous is None:self.__dict__.pop('local',None)
            else:self.local=previous
    return scroll


def install_workspace_fix(cls):
    """Keep original classic code untouched; approved new UI only."""
    global _INSTALLED
    if _INSTALLED:return
    for name in ('draw_recipes','draw_calculator','draw_settings','draw_manual','draw_popup'):
        original=getattr(cls,name,None)
        if original is not None:
            setattr(cls,name,_fitted_page(original))
    if hasattr(cls,'scrollbar_click'):
        cls.scrollbar_click=_scrollbar_click(cls.scrollbar_click)
    if hasattr(cls,'onwheel'):
        cls.onwheel=_wheel(cls.onwheel)
    original=cls.redraw
    def repaint(self,*args,**kwargs):
        result=original(self,*args,**kwargs)
        _place_search_widgets(self)
        return result
    cls.redraw=repaint
    # v0.31.13: merge consecutive wheel ticks into a single Canvas redraw.
    from scroll_performance_v313 import install_scroll_performance
    install_scroll_performance(cls)
    _INSTALLED=True


def _font(editor,size,bold=False):
    scale=editor.draft.get('text_size',100)/100
    scale*=editor.draft.get('ui_scale',100)/100
    return editor._preview_font(max(9,round(size*scale)),bold)


def _color(entry,default):
    val=entry if isinstance(entry,str) else default
    try:return ImageColor.getrgb(val)
    except ValueError:return ImageColor.getrgb(default)


def _paint_preview(editor):
    """Draw the *approved six-tab layout*, not the retired four-tab mockup.

    Decorative scenery is the approved reference background, while captions,
    menus, data tiles and selected items are newly drawn from draft/current data.
    """
    from core import ROOT, CARGO, display_cargo, BUILTIN_RECIPES
    from cargo_weight_v317 import cargo_weight_label
    from appearance import normalize
    from approved_reference_v311 import _stats, _FEATURED

    d=normalize(editor.draft)
    W,H=1319,747
    path=ROOT/'assets/ui/approved_reference_v311.png'
    if path.is_file():
        with Image.open(path) as im:base=im.convert('RGB').copy()
    else:base=Image.new('RGB',(W,H),'#071821')
    if d.get('background_image') and Path(d['background_image']).is_file():
        try:
            with Image.open(d['background_image']) as source:
                backdrop=ImageOps.fit(source.convert('RGB'),(W,H),Image.Resampling.LANCZOS)
            # Respect custom background while keeping readable approved panels.
            base=Image.blend(base,backdrop,0.28)
        except (OSError,ValueError):pass
    if d.get('header_image') and Path(d['header_image']).is_file():
        try:
            with Image.open(d['header_image']) as source:
                header=ImageOps.fit(source.convert('RGB'),(W,84),Image.Resampling.LANCZOS)
            base.paste(header,(0,25))
        except (OSError,ValueError):pass
    canvas=base.convert('RGBA')
    pen=ImageDraw.Draw(canvas,'RGBA')
    fg=_color(d.get('fg'),'#F4F4F4')
    muted=_color(d.get('muted'),'#BAC3C6')
    accent=_color(d.get('accent'),'#FFC21B')
    surface=_color(d.get('panel'),'#151C20')
    card=_color(d.get('row'),'#222B31')
    border=_color(d.get('border'),'#45525A')
    alpha=int(d.get('panel_alpha',94)/100*255)
    radius=max(0,min(22,d.get('corner_radius',8)))
    def rounded(rect,fill=None,stroke=None,width=1,r=None):
        pen.rounded_rectangle(tuple(round(v) for v in rect),radius=radius if r is None else r,
            fill=tuple(fill)+(alpha,) if fill is not None and len(fill)==3 else fill,
            outline=tuple(stroke)+(230,) if stroke is not None and len(stroke)==3 else stroke,width=width)
    def label(x,y,s,sz=14,fill=fg,bold=False,max_width=None):
        s=str(s)
        f=_font(editor,sz,bold)
        if max_width:
            while len(s)>2 and pen.textbbox((0,0),s,font=f)[2]>max_width:s=s[:-2]+'…'
        pen.text((round(x),round(y)),s,font=f,fill=tuple(fill)+(255,))
    def icon_img(page,x,y,size=34):
        custom=d.get('nav_icons',{}).get(page,'')
        path2=Path(custom) if custom and Path(custom).is_file() else ROOT/'assets/ui/approved_nav'/f'{page}.png'
        if not path2.is_file():return
        try:
            with Image.open(path2) as img:icon=img.convert('RGBA').copy()
            icon.thumbnail((size,size),Image.Resampling.LANCZOS)
            canvas.alpha_composite(icon,(round(x),round(y)))
        except (OSError,ValueError):pass
    is_ru=editor.ru
    # The top 109px are the *actual* approved art, rather than a redesigned
    # title bar. Profile strip is always from current application's save state.
    pen.rectangle((190,110,W,166),fill=(5,24,32,245))
    try:stats=_stats(type('Context',(),{'app':editor.app})())
    except Exception:stats={'profile':'Локальный профиль','exp':None,'money':None,'objectives':None}
    def fmt(v):return f'{v:,.0f}'.replace(',',' ') if isinstance(v,(int,float)) and not isinstance(v,bool) else '—'
    label(211,130,'Игрок:' if is_ru else 'Player:',11,muted)
    label(263,128,stats.get('profile') or '—',15,fg,True,215)
    pen.line((465,118,465,159),fill=border,width=1)
    label(487,122,'★',27,accent)
    label(525,115,'Опыт' if is_ru else 'XP',11,muted)
    label(525,137,fmt(stats.get('exp')),15,fg,True)
    pen.line((637,118,637,159),fill=border,width=1)
    label(655,121,'▣',23,accent)
    label(690,115,'Баланс' if is_ru else 'Balance',11,muted)
    label(690,137,fmt(stats.get('money')),15,fg,True)
    pen.line((875,118,875,159),fill=border,width=1)
    label(890,127,'Выполнено заданий:' if is_ru else 'Completed tasks:',11,muted)
    label(1055,127,fmt(stats.get('objectives')),13,fg,True)
    rounded((1105,118,1283,154),_color(d['row'],'#222B31'),border,r=6)
    label(1133,129,'⟳  ОБНОВИТЬ' if is_ru else '⟳  REFRESH',12,fg,True)
    menu=[('home','Главная','Home'),('cargo','Грузы','Cargo'),('recipes','Крафт','Craft'),
          ('garage','Гараж','Garage'),('calculator','Калькулятор','Calculator'),('settings','Настройки','Settings')]
    page=editor.preview_mode if editor.preview_mode in ('cargo','recipes','settings') else 'cargo'
    for idx,(key,ru,en) in enumerate(menu):
        y=184+idx*57 if idx<5 else 660
        active=key==page
        rounded((8,y,179,y+46),card if not active else (85,68,24),accent if active else border,2 if active else 1,r=8)
        icon_img(key,22,y+4,36)
        label(70,y+12,ru if is_ru else en,15,fg,active,104)
    rounded((197,177,908,711),surface,border)
    rounded((913,177,1294,711),surface,border)
    from core import CARGO_DB
    if page=='cargo':
        label(210,188,'ГРУЗЫ' if is_ru else 'CARGO',27,fg,True)
        pen.line((211,216,890,216),fill=border,width=2)
        rounded((211,227,450,257),card,border,r=4)
        label(223,229,'⌕',21,accent,True)
        label(263,234,'Поиск...' if is_ru else 'Search...',12,muted)
        label(465,234,'Сортировка:' if is_ru else 'Sort:',12,fg)
        rounded((542,227,673,256),card,border,r=4); label(551,233,'Слоты ↑' if is_ru else 'Slots ↑',12,fg)
        label(706,234,'Карта:' if is_ru else 'Map:',12,fg);rounded((755,227,895,257),card,border,r=4)
        label(762,235,'Все карты' if is_ru else 'All maps',11,fg)
        label(463,270,'Регион:' if is_ru else 'Region:',12,fg);rounded((515,268,658,299),card,border,r=4)
        label(525,273,'Все регионы' if is_ru else 'All regions',11,fg)
        label(696,270,'Категория:' if is_ru else 'Category:',12,fg);rounded((766,268,895,299),card,border,r=4)
        label(774,273,'Все' if is_ru else 'All',11,fg)
        names=[cid for cid in _FEATURED if cid in CARGO]
        if not names:names=[c['id'] for c in CARGO_DB[:8]]
        for idx,cid in enumerate(names[:8]):
            item=CARGO[cid]; y=309+idx*45
            selected=idx==0
            rounded((201,y,891,y+44),(86,69,27) if selected else card,accent if selected else border,2 if selected else 1,r=5)
            try:
                from icon_manager import cargo_icon_path
                ip=cargo_icon_path(cid)
                if ip and Path(ip).is_file():
                    with Image.open(ip) as icon:ii=icon.convert('RGBA');ii.thumbnail((65,42),Image.Resampling.LANCZOS)
                    canvas.alpha_composite(ii,(226,y+round((44-ii.height)/2)))
            except (ImportError,ValueError,OSError):pass
            label(302,y+12,display_cargo(cid,'ru' if is_ru else 'en'),14,fg,selected,245)
            rounded((547,y+10,648,y+35),card,border,r=5)
            label(556,y+14,str(item.get('category','—'))[:12],11,muted)
            label(681,y+14,cargo_weight_label(item,'ru' if is_ru else 'en'),11,fg)
            slots=item.get('slots');label(806,y+14,'× '+str(slots) if slots is not None else '—',12,fg)
        cid=names[0] if names else None
        if cid:
            item=CARGO[cid]
            label(949,191,display_cargo(cid,'ru' if is_ru else 'en'),21,fg,True,329)
            label(1048,238,str(item.get('category','—')),12,muted)
            label(1030,278,cargo_weight_label(item,'ru' if is_ru else 'en'),14,fg)
            label(1200,278,('× '+str(item.get('slots','—'))+' слота') if is_ru else ('× '+str(item.get('slots','—'))+' slots'),12,fg)
        pen.line((930,310,1280,310),fill=border)
        label(946,320,'Используется в:' if is_ru else 'Used in:',18,accent,True)
        label(954,365,'Данные из игрового каталога' if is_ru else 'From the game catalog',12,muted)
        pen.line((930,434,1280,434),fill=border)
        label(945,443,'Связанные задания:' if is_ru else 'Related tasks:',17,accent,True)
        label(955,489,'Нет подтверждённых данных' if is_ru else 'No verified data',13,muted)
        pen.line((930,538,1280,538),fill=border)
        label(945,551,'Расположение:' if is_ru else 'Location:',18,accent,True)
        label(953,594,'Нет данных' if is_ru else 'No data',12,muted)
    else:
        title={'recipes':('КРАФТ','CRAFT'),'settings':('НАСТРОЙКИ','SETTINGS')}[page]
        label(215,189,title[0 if is_ru else 1],27,fg,True)
        label(220,239,('Подбор рецептов' if page=='recipes' else 'Настройка внешнего вида') if is_ru else ('Recipes' if page=='recipes' else 'Appearance settings'),19,accent,True)
        for i in range(5):
            y=289+i*70
            rounded((221,y,715,y+52),card,border,r=6)
            label(242,y+13,(('Рецепт ' if is_ru else 'Recipe ')+str(i+1)) if page=='recipes' else ('Параметр '+str(i+1) if is_ru else 'Setting '+str(i+1)),13,fg)
        rounded((740,252,1282,682),card,border,r=8)
        label(765,273,'РЕЦЕПТ' if page=='recipes' and is_ru else 'RECIPE' if page=='recipes' else 'ПАРАМЕТРЫ' if is_ru else 'SETTINGS',20,fg,True)
        label(765,351,'Выберите строку слева' if is_ru else 'Select an item',14,muted)
    return canvas.convert('RGB')


def install_editor_preview():
    """Replace obsolete preview and register both new six-tab navigation icons."""
    import appearance
    Editor=appearance.AppearanceEditor
    if getattr(Editor,'_ui_repair_v312',False):return
    Editor._render_preview_image=_paint_preview
    def icons(self,p):
        import tkinter as tk
        self.text(p,self.tx('Значки всех шести разделов утверждённого интерфейса.','Icons for all six tabs of the approved interface.'),
                  10,wraplength=322,justify='left').pack(anchor='w',pady=7)
        options=(('home','Главная','Home'),('cargo','Грузы','Cargo'),('recipes','Крафт','Craft'),
                 ('garage','Гараж','Garage'),('calculator','Калькулятор','Calculator'),('settings','Настройки','Settings'))
        for key,ru,en in options:
            line=tk.Frame(p,bg=p.cget('bg'));line.pack(fill='x',pady=4)
            self.text(line,ru if self.ru else en,10).pack(side='left')
            self.button(line,'PNG',lambda k=key:self.pick_icon(k)).pack(side='right')
        self.button(p,self.tx('Вернуть стандартные значки','Restore default icons'),
                    lambda:self.set('nav_icons',{})).pack(anchor='w',pady=10)
    Editor.icons=icons
    original_normalize=appearance.normalize
    def normalize_extended(settings):
        result=original_normalize(settings)
        if isinstance(settings,dict) and isinstance(settings.get('nav_icons'),dict):
            for key in ('home','garage'):
                value=settings['nav_icons'].get(key)
                if isinstance(value,str):result['nav_icons'][key]=value
        return result
    appearance.normalize=normalize_extended
    # These modules imported normalize with `from appearance import normalize`.
    import sys
    for name in ('app','game_ui'):
        module=sys.modules.get(name)
        if module is not None and getattr(module,'normalize',None) is original_normalize:
            module.normalize=normalize_extended
    # Route wheel input over labels/buttons too, without touching the preview.
    from scroll_performance_v313 import install_editor_wheel
    install_editor_wheel(Editor)
    Editor._ui_repair_v312=True
