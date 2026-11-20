"""Screenshot-matched, fully interactive SnowRunner-themed Tk canvas UI.

The supplied concept image is used only as decorative scenery (masthead and
weathered edges); cargo/recipes/sorting/details are real, data-driven widgets.
"""
from __future__ import annotations
import random
import math
import time
import os
import tkinter as tk
from tkinter import messagebox
from font_manager import FontManager
from tkinter import font as tkfont
from pathlib import Path
from PIL import Image, ImageDraw, ImageTk, ImageEnhance, ImageOps, ImageColor
from icon_manager import cargo_icon_path, has_custom_icon
from appearance import normalize, asset_path, PRESETS
from theme_v317 import theme_color, theme_background, THEME_LABELS
from cargo_weight_v317 import cargo_weight_label
import webbrowser
from core import (ROOT, CARGO_DB, CARGO, BUILTIN_RECIPES, SORT_MODES,
                  cargo_slots, display_cargo, display_region, display_recipe_location, display_recipe_notes, text_value,
                  sort_cargo, filter_recipes, calculate_load, save_json, SETTINGS_FILE)

W, H = 1319, 747
BG = '#10171b'
PANEL = '#151c20'
ROW = '#222b31'
ROW_HOVER = '#303940'
FG = '#F1F2F0'
MUTED = '#BDC2C4'
YELLOW = '#FFC21B'
BORDER = '#3A454C'

NAV = ['cargo', 'recipes', 'calculator', 'manual', 'settings']
# Keep frequently used sections together; anchor Settings at the lower edge
# of the continuous left sidebar, instead of a fifth adjacent row.
NAV_Y = {'cargo': 183, 'recipes': 255, 'calculator': 327, 'manual': 399, 'settings': 634}
SYMS = {'cargo':'▣','recipes':'⚒','calculator':'▦','manual':'▤','settings':'⚙'}
CAT_RU = {'construction':'Строительный', 'wood':'Древесина', 'metal':'Металл',
          'industrial':'Промышленный', 'supplies':'Снабжение', 'container':'Контейнер',
          'logs':'Брёвна', 'agriculture':'Сельское хозяйство', 'mission':'Задание', 'special':'Особый'}
CAT_EN = {'construction':'Construction','wood':'Wood','metal':'Metal','industrial':'Industrial',
          'supplies':'Supplies','container':'Container','logs':'Logs',
          'agriculture':'Agriculture','mission':'Mission','special':'Special'}

class GameScreen:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.page = app.page
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, borderwidth=0, cursor='arrow')
        self.canvas.pack(fill='both', expand=True)
        self.search = tk.StringVar()
        self.search.trace_add('write', self.on_search)
        self.search_entry = tk.Entry(self.root, textvariable=self.search, bg='#20272c',
                                     fg='#F3F4F1', insertbackground=YELLOW,
                                     selectbackground='#B4861E', selectforeground='black',
                                     relief='flat', borderwidth=0, highlightthickness=0, font=('Segoe UI', 12))
        self.search_placeholder = tk.Label(self.root, text='Поиск...' if app.config['lang']=='ru' else 'Search...',
                                           font=('Segoe UI',12), bg='#20272c',fg='#899398', cursor='xterm')
        self.search_placeholder.bind('<Button-1>',lambda e:self.search_entry.focus_set())
        self.search_entry.bind('<FocusIn>',lambda e:self.redraw())
        self.search_entry.bind('<FocusOut>',lambda e:self.redraw())
        self.selected_cargo = getattr(app,'last_selected_cargo','metal_beams')
        self.previous_context = None
        self.manual_offset=0
        self.manual_verified_only=True
        self.cargo_verified_only=False  # Full cargo catalog, as in the approved design
        self._window_drag=None
        self._window_resize=None
        self._scrollbar_drag=False
        self._scrollbar_area=None
        self.appearance=normalize(app.config.get('appearance'))
        self.new_ui = app.config.get('ui_design', 'expedition') != 'classic'
        # v24 visual implementation of the image approved by the user.
        self.reference_ui = self.new_ui
        self.cargo_category = ''
        self.cargo_detail_open = False
        self._apply_palette()
        self.selected_recipe = app.selected_recipe
        # Approved transitions: glow on hover, sliding detail, easing outline.
        self.hover_strength = 0.0
        self.selection_y = None
        self.selection_target_y = None
        self.detail_started = 0.0
        self.motion_job = None
        known_ids={cid for rec in BUILTIN_RECIPES+app.official for cid in (list(rec.get('inputs',{}))+list(rec.get('outputs',{})))}
        sorted_at_start=sort_cargo([c for c in CARGO_DB if c['id'] in known_ids],app.config['sort'],app.config['lang'])
        self.offset=max(0,next((i for i,c in enumerate(sorted_at_start) if c['id']=='metal_beams'),0))
        if self.page=='recipes' and self.selected_recipe is not None:
            recipe_rows=filter_recipes(BUILTIN_RECIPES+app.official+app.custom,'','',app.config['lang'])
            self.offset=max(0,next((i for i,r in enumerate(recipe_rows)
                                     if r is self.selected_recipe or r.get('id')==self.selected_recipe.get('id')),0))
        self.popup = None
        self.hover = None
        self.hitboxes = []
        self.refs = []
        self.image_cache = {}
        self.bg_cache = {}
        self.render_token = 0
        self.scale = 1
        self.pan_x = self.pan_y = 0
        self.pan_start = None
        self.ox = self.oy = 0
        self.recipes_region = ''
        self.region_page = 0
        self.qty = 1
        self.calc_offset = 0
        self.load_offset = 0
        self.calc_verified_only = True
        self.calc_search = tk.StringVar(master=self.root)
        self.calc_search.trace_add('write',lambda *_:self._on_calculator_search())
        self.calc_search_entry = tk.Entry(self.root,textvariable=self.calc_search,bg='#20272c',fg='#F3F4F1',
                                          insertbackground=YELLOW,relief='flat',borderwidth=0,
                                          highlightthickness=0,font=('Segoe UI',12))
        self.calc_search_placeholder=tk.Label(self.root,text='Поиск груза...' if app.config['lang']=='ru' else 'Search cargo...',
                                              bg='#20272c',fg='#899398',font=('Segoe UI',11),cursor='xterm')
        self.calc_search_placeholder.bind('<Button-1>',lambda e:self.calc_search_entry.focus_set())
        self.calc_search_entry.bind('<FocusIn>',lambda e:self.redraw())
        self.calc_search_entry.bind('<FocusOut>',lambda e:self.redraw())
        if getattr(self,'new_ui',False):
            for widget in (self.search_entry,self.calc_search_entry):
                widget.configure(bg='#213540',fg=FG,insertbackground=YELLOW)
            for widget in (self.search_placeholder,self.calc_search_placeholder):
                widget.configure(bg='#213540',fg=MUTED)
        if app.config.get('theme','game') != 'game':
            for widget in (self.search_entry,self.calc_search_entry):
                widget.configure(bg=self.ui_color('#213540'),
                                 fg=self.ui_color('#F1F2F0','text'),
                                 insertbackground=self.ui_color('#F1F2F0','text'))
            for widget in (self.search_placeholder,self.calc_search_placeholder):
                widget.configure(bg=self.ui_color('#213540'),
                                 fg=self.ui_color('#BDC2C4','text'))
        self.maximized = False
        self.calculator_cargo = 'metal_beams'
        self._build_background()
        self.canvas.bind('<Configure>', lambda e: self.redraw())
        self._geometry_save_job=None
        self.root.bind('<Configure>',self._remember_geometry)
        self.canvas.bind('<Button-1>', self.onclick)
        self.canvas.bind('<Double-Button-1>', self.on_double_click_header)
        self.canvas.bind('<Motion>', self.onmove)
        self.canvas.bind('<Leave>', lambda e: self.onleave())
        # Bind at toplevel so wheel works even while the search Entry has focus.
        self.root.bind('<MouseWheel>',self.onwheel)
        self.root.bind('<Button-4>',self.onwheel)
        self.root.bind('<Button-5>',self.onwheel)
        self.canvas.bind('<ButtonPress-2>',self.pan_begin)
        self.canvas.bind('<B2-Motion>',self.pan_drag)
        self.canvas.bind('<ButtonRelease-2>',self.pan_end)
        self.root.bind('<Control-plus>',lambda e:self.zoom_by(10))
        self.root.bind('<Control-equal>',lambda e:self.zoom_by(10))
        self.root.bind('<Control-minus>',lambda e:self.zoom_by(-10))
        self.root.bind('<Control-0>',lambda e:self.set_zoom(100))
        self.canvas.bind('<KeyPress>', self.onkey)
        self.root.bind('<Escape>', self.escape)
        self.root.bind('<F11>', lambda event: self.toggle_maximize())
        self.root.bind('<Alt-Left>',lambda e:self.go_back())
        self.canvas.bind('<ButtonPress-1>',self._press_window,add='+')
        self.canvas.bind('<B1-Motion>',self._move_window,add='+')
        self.canvas.bind('<B1-Motion>',self._drag_list,add='+')
        self.canvas.bind('<ButtonRelease-1>',self._release_window,add='+')
        self.root.bind('<Control-f>',lambda e: (self.calc_search_entry if self.page=='calculator' else self.search_entry).focus_set())
        self.root.title('SnowRunner Helper')
        # On Windows use our actual header controls: avoid the OS title bar
        # appearing above a second drawn titlebar.
        if os.name=='nt':
            self.root.overrideredirect(True)
        if not getattr(self.app, '_window_initialized', False):
            geometry=str(self.app.config.get('window_geometry','1319x747'))
            import re
            if not re.fullmatch(r'\d{3,4}x\d{3,4}(?:[+-]\d+[+-]\d+)?',geometry):
                geometry='1319x747'
            self.root.geometry(geometry)
            self.app._window_initialized = True
        self.root.minsize(1040, 640)
        self.redraw()

    def _apply_palette(self):
        global BG,PANEL,ROW,ROW_HOVER,FG,MUTED,YELLOW,BORDER
        d=self.appearance
        BG='#0B131B' if getattr(self,'new_ui',False) else '#10171b'
        alpha=d.get('panel_alpha',94)/100
        def blend(fg,back,f):
            a=ImageColor.getrgb(fg);b=ImageColor.getrgb(back)
            return '#'+''.join(f'{round(u*f+v*(1-f)):02X}' for u,v in zip(a,b))
        PANEL=blend(d['panel'],'#15232E',alpha)
        ROW=blend(d['row'],'#1A2E39',alpha)
        ROW_HOVER=blend(ROW,d['accent'],.22)
        FG=d['fg'];MUTED=d['muted'];YELLOW=d['accent'];BORDER=d['border']
        if getattr(self,'new_ui',False):
            PANEL='#101B24'
            ROW='#1B2B35'
            ROW_HOVER='#28414B'
            MUTED='#9BB0BF'
            BORDER='#344C5B'
        if self.app.config.get('theme','game') != 'game':
            BG=self.app.c('bg'); FG=self.app.c('fg')
            MUTED=self.app.c('muted');YELLOW=self.app.c('accent')

    def _remember_geometry(self,event):
        if event.widget != self.root or self._window_drag or self._window_resize:
            return
        # Debounce user resizing; appearance zoom itself never changes geometry.
        if self._geometry_save_job is not None:
            try:self.root.after_cancel(self._geometry_save_job)
            except tk.TclError:pass
        self._geometry_save_job=self.root.after(700,self._save_geometry)

    def _save_geometry(self):
        self._geometry_save_job=None
        try:
            if not self.root.winfo_exists():return
            if self.maximized:return  # Never overwrite restored size with maximized geometry.
            width,height=self.root.winfo_width(),self.root.winfo_height()
            if width<1040 or height<640:return
            self.app.config['window_geometry']=self.root.geometry()
            save_json(SETTINGS_FILE,self.app.config)
        except tk.TclError:pass

    def _press_window(self,e):
        pos=self.local(e.x,e.y)
        if not pos:return
        x,y=pos
        if self.page=='cargo' and getattr(self,'reference_ui',False) and 1288<x<1309 and 209<y<713:
            self._scrollbar_drag=True;self._scrollbar_area='reference_cargo';return
        if self.page=='calculator' and 1268<x<1292 and 334<y<609:
            self._scrollbar_drag=True;self._scrollbar_area='load'
            return
        if self.page in ('cargo','recipes','manual','calculator') and 735<x<755 and 254<y<695:
            self._scrollbar_drag=True;self._scrollbar_area='catalog'
            return
        # The empty strip of the mountain/header acts as a drag handle.
        if 0<y<133 and 280<x<855 and not self.popup:
            self._window_drag=(e.x_root,e.y_root,self.root.winfo_x(),self.root.winfo_y())
        # Resize near the actual outside window edge; do not intercept controls.
        edge=11
        w=self.root.winfo_width();h=self.root.winfo_height()
        right=e.x>=w-edge;bottom=e.y>=h-edge
        if right or bottom:
            self._window_resize=(e.x_root,e.y_root,w,h,right,bottom)

    def _move_window(self,e):
        if self._window_drag:
            x,y,left,top=self._window_drag
            self.root.geometry(f'+{left+e.x_root-x}+{top+e.y_root-y}')
        elif self._window_resize:
            x,y,w,h,right,bottom=self._window_resize
            nw=max(1040,w+(e.x_root-x)) if right else w
            nh=max(640,h+(e.y_root-y)) if bottom else h
            self.root.geometry(f'{nw}x{nh}')

    def _drag_list(self,e):
        if not self._scrollbar_drag:return
        pos=self.local(e.x,e.y)
        if not pos:return
        if self._scrollbar_area=='reference_cargo':
            total=len(self.visible_cargo())
            self.offset=round(max(0,total-8)*max(0,min(1,(pos[1]-214)/475)))
            self.redraw();return
        if self._scrollbar_area=='load':
            maxoff=max(0,len(self.app.load)-4)
            self.load_offset=round(maxoff*max(0,min(1,(pos[1]-334)/275)))
            self.redraw();return
        if self.page=='cargo':total=len(self.visible_cargo())
        elif self.page=='recipes':total=len(self.visible_recipes())
        elif self.page=='manual':total=len(self.manual_items())
        elif self.page=='calculator':total=len(self.calculator_items())
        else:return
        visible=5 if self.page=='calculator' else self.row_count()
        maxoff=max(0,total-visible)
        start,end=(280,694) if self.page=='calculator' else (255,684)
        offset=round(maxoff*max(0,min(1,(pos[1]-start)/(end-start))))
        if self.page=='manual':self.manual_offset=offset
        elif self.page=='calculator':self.calc_offset=offset
        else:self.offset=offset
        self.selection_y=None
        self.redraw()

    def _release_window(self,e):
        if self._window_drag or self._window_resize:
            self.root.after(200,self._save_geometry)
        self._window_drag=None;self._window_resize=None
        self._scrollbar_drag=False
        self._scrollbar_area=None

    def minimize_window(self):
        if os.name=='nt':
            self.root.overrideredirect(False)
            self.root.iconify()
            def restore(event=None):
                if self.root.state()!='iconic':
                    self.root.overrideredirect(True)
                    self.root.unbind('<Map>')
            self.root.bind('<Map>',restore)
        else:self.root.iconify()

    def _build_expedition_background(self):
        """Purely decorative drawn skin; the real UI and hit boxes stay live."""
        rng=random.Random(72022)
        im=Image.new('RGB',(W,H))
        dr=ImageDraw.Draw(im)
        # Two layered vertical gradients give the interface an expedition-HUD feel.
        for y in range(H):
            f=y/(H-1)
            a=(8,16,23)
            b=(14,24,31)
            dr.line((0,y,W,y),fill=tuple(round(a[c]*(1-f)+b[c]*f) for c in range(3)))
        dr.rectangle((0,0,W,111),fill='#101F2A')
        for y in range(0,111):
            mix=y/111
            dr.line((0,y,W,y),fill=(round(11+7*mix),round(25+10*mix),round(35+13*mix)))
        # Abstract ridge line, deliberately NOT an old game screenshot or truck.
        mountains=[(245,111),(245,89),(304,86),(347,55),(385,75),(429,36),
                   (462,72),(515,45),(564,83),(620,48),(680,69),(729,37),
                   (773,81),(848,46),(912,85),(983,60),(1036,80),(1124,45),
                   (1179,86),(1320,56),(1320,111)]
        dr.polygon(mountains,fill='#1C3642')
        dr.line(mountains[1:-1],fill='#3A5C65',width=2)
        for k in range(19):
            x=rng.randint(260,1290);y=rng.randint(6,105)
            dr.line((x,y,x+rng.randint(5,24),y),fill='#314B53',width=1)
        # Subtle topography curves and grid, outside the text-heavy content.
        for x in range(275,1309,48):
            dr.line((x,132,x,724),fill='#152832',width=1)
        for y in range(133,724,48):
            dr.line((267,y,1310,y),fill='#152832',width=1)
        for k in range(8):
            points=[]
            for x in range(268,1320,8):
                y=142+k*26+12*math.sin(x/125+k*.53)+3*math.sin(x/29+k)
                points.append((x,round(y)))
            dr.line(points,fill='#1B303B',width=1)
        # Continuous sidebar, no tire tracks or clipped image seams.
        dr.rectangle((0,111,250,746),fill='#0C1720')
        dr.rectangle((249,111,251,746),fill='#274453')
        dr.rectangle((0,110,W,112),fill='#3B5965')
        dr.rectangle((0,0,5,746),fill='#213944')
        dr.rectangle((4,111,7,745),fill='#E4AD35')
        # Brand mark: small golden vertical accent and diagonal detail.
        dr.rounded_rectangle((23,29,29,79),radius=3,fill=YELLOW)
        dr.polygon([(247,0),(360,0),(299,110),(247,110)],fill='#162D39')
        dr.line((299,110,356,0),fill='#345766',width=2)
        for i in range(1750):
            x=rng.randint(260,1308);y=rng.randint(130,722)
            dr.point((x,y),fill=('#1D313C' if i%3 else '#1A2E37'))
        # Outer edge for window without double OS titlebar on Windows.
        dr.rectangle((0,0,W-1,H-1),outline='#46626A',width=2)
        self.base_image=im
        self.bg_cache={}

    def _build_background(self):
        if getattr(self,'new_ui',False):
            self._build_reference_background() if getattr(self,'reference_ui',False) else self._build_expedition_background()
            return
        """Build a seamless, page-independent body behind every section.

        Keep snowy scenery above the masthead baseline, but extend the solid
        workspace panel right to the inside window edge at x=1310. Do not leave
        an old truck-image rectangle cutting into the content just below the
        header. Draw the background before all interactive content.
        """
        d=self.appearance
        ref=ROOT/'assets/ui/reference.png'
        original=(Image.open(ref).convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
                  if ref.exists() else Image.new('RGB',(W,H),(12,17,21)))
        if d.get('background_image') and Path(d['background_image']).is_file():
            with Image.open(d['background_image']) as source:
                img=ImageOps.fit(source.convert('RGB'),(W,H),Image.Resampling.LANCZOS)
                img=Image.blend(img,Image.new('RGB',(W,H),'#142028'),.22)
        else:
            img=original.copy()

        # Custom/preset header art comes first.  Otherwise it can repaint the
        # beginning of the body, leaving a second seam at x=478 or y=178.
        try:
            custom=bool(d.get('header_image'))
            with Image.open(asset_path(d,'header')) as source:
                part=ImageOps.fit(source.convert('RGB'),(W,190),Image.Resampling.LANCZOS)
                if custom or d.get('preset')!='snow':
                    img.paste(part.crop((478,0,W,178)),(478,0))
        except (OSError,ValueError):
            pass

        # Replace the full top-right truck artwork with uninterrupted snowy
        # scenery. Previously only the top 92 px were repainted, leaving an
        # awkward clipped truck roof between y=92 and y=123.
        snow=ImageOps.fit(original.crop((385,0,641,123)),(W-862,123),Image.Resampling.LANCZOS)
        fade=Image.new('L',(W-862,123),255)
        fdraw=ImageDraw.Draw(fade)
        for xx in range(46):
            alpha=min(255,round(255*xx/45))
            fdraw.line((xx,0,xx,122),fill=alpha)
        img.paste(snow,(862,0),fade)
        plate=Image.new('RGBA',img.size,(0,0,0,0))
        ImageDraw.Draw(plate).rounded_rectangle((862,5,1315,68),radius=6,fill=(10,18,25,115))
        img=Image.alpha_composite(img.convert('RGBA'),plate).convert('RGB')

        # Cover the whole workspace below the masthead, including the old
        # upper-right truck fragment. This avoids the hard cut at x=1014 and
        # keeps every page's content background continuous to the right edge.
        draw=ImageDraw.Draw(img)
        draw.rectangle((12,123,1310,724),fill=PANEL)

        # Keep the sidebar footer visually continuous below "Settings".
        # Never restore the old tire-track crop or mud splashes from the
        # screenshot artwork, even for profiles with legacy tracks=True.
        # The same PANEL paint extends right down to the bottom inner edge.
        draw=ImageDraw.Draw(img)
        draw.rectangle((12,123,250,724), fill=PANEL)
        # The reference screenshot also has a narrow yellow tire-track strip
        # *inside the left frame*. Replace it for the entire sidebar height.
        # Keep a subtle, consistent window border instead of a new seam.
        draw.rectangle((2,123,12,719), fill=PANEL)
        draw.line((3,123,3,718), fill='#344047', width=1)

        if d.get('textures'):
            # A subtle uniform grain; it must not introduce a footer seam.
            rng=random.Random(2319)
            for _ in range(6500):
                x=rng.randint(15,1309)
                y=rng.randint(126,718)
                base=rng.randint(25,43)
                draw.point((x,y),fill=(base,base+1,base+2))
        if not d.get('snow'):
            img.paste(Image.new('RGB',(510,16),'#19242B'),(790,140))
        self.base_image=img
        self.bg_cache={}

    def t(self, key): return self.app.t(key)
    @property
    def lang(self): return self.app.config['lang']

    def s(self, v): return v * self.scale
    def _xcoord(self,x):
        nav=self.appearance.get('sidebar_width',252)
        return x*nav/252 if x<=252 else nav+(x-252)*(W-nav)/(W-252)
    def _inverse_x(self,x):
        nav=self.appearance.get('sidebar_width',252)
        return x*252/nav if x<=nav else 252+(x-nav)*(W-252)/(W-nav)
    def p(self, x, y): return (self.ox+self._xcoord(x)*self.sx, self.oy+y*self.sy)
    def font(self, size, bold=False, text=''):
        family=self.app.font_manager.family(text,self.lang)
        font_px=max(7,int(size*self.scale*self.app.config.get('text_size',100)/100))
        return (family,font_px,'bold' if bold else 'normal')
    def ui_color(self, color, kind='surface'):
        return theme_color(color,self.app.config.get('theme','game'),kind)

    def txt(self,x,y,text,size=14,color=FG,bold=False,anchor='w',limit=None):
        text=str(text)
        if color=='#F1F2F0':color=self.appearance['fg']
        elif color=='#BDC2C4':color=self.appearance['muted']
        if limit is not None:
            max_px=self.s(limit)
            font_size=max(7,int(size*self.scale*self.app.config.get('text_size',100)/100))
            family=self.app.font_manager.family(text,self.lang)
            f=tkfont.Font(family=family,size=font_size,weight='bold' if bold else 'normal')
            # Prefer fitting the complete cargo name to silently truncating it.
            while f.measure(text)>max_px and font_size>max(8,int(10*self.scale)):
                font_size-=1
                f.configure(size=font_size)
            if f.measure(text)>max_px:
                while len(text)>1 and f.measure(text+'…')>max_px:text=text[:-1]
                text+='…'
            return self.canvas.create_text(*self.p(x,y),text=text,fill=self.ui_color(color,'text'),
                         font=(family,font_size,'bold' if bold else 'normal'),anchor=anchor)
        return self.canvas.create_text(*self.p(x,y),text=text,fill=self.ui_color(color,'text'),font=self.font(size,bold,text),anchor=anchor)
    def rect(self,x1,y1,x2,y2,fill,outline='',width=1):
        return self.canvas.create_rectangle(*self.p(x1,y1),*self.p(x2,y2),fill=self.ui_color(fill),
                                             outline=self.ui_color(outline),width=max(1,self.s(width)))
    def line(self,x1,y1,x2,y2,color=BORDER,width=1):
        if color=='#3A454C':color=self.appearance['border']
        return self.canvas.create_line(*self.p(x1,y1),*self.p(x2,y2),fill=self.ui_color(color),width=max(1,self.s(width)))
    def round(self,x1,y1,x2,y2,r,fill,outline='',width=1):
        x1,y1=self.p(x1,y1); x2,y2=self.p(x2,y2); r=self.s(min(r,self.appearance.get('corner_radius',8)))
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        return self.canvas.create_polygon(pts,smooth=True,splinesteps=10,
                                fill=self.ui_color(fill),outline=self.ui_color(outline),width=max(1,self.s(width)))
    def image(self, name, x,y, width,height,recipe=False):
        folder='recipes' if recipe else 'cargo'
        from app import OVERRIDE_ASSETS
        if recipe:
            path = OVERRIDE_ASSETS / 'recipes' / f'{name}.png'
            if not path.exists():path=ROOT/'assets'/'recipes'/f'{name}.png'
            if not path.exists() and name in CARGO:
                path=cargo_icon_path(name, legacy_folder=OVERRIDE_ASSETS / 'cargo')
        else:
            path=cargo_icon_path(name, legacy_folder=OVERRIDE_ASSETS / 'cargo')
        if not path or not path.exists():return
        px=max(1,int(self.s(width)));py=max(1,int(self.s(height)))
        k=(str(path),px,py)
        if k not in self.image_cache:
            im=Image.open(path).convert('RGBA')
            im.thumbnail((px,py),Image.Resampling.LANCZOS)
            self.image_cache[k]=ImageTk.PhotoImage(im,master=self.root)
        im=self.image_cache[k]
        self.refs.append(im)
        return self.canvas.create_image(*self.p(x,y),image=im,anchor='center')
    def screenshot_detail(self,filename,x,y,width,height):
        path=ROOT/'assets/ui'/filename
        if not path.exists():return
        px=max(1,int(self.s(width)));py=max(1,int(self.s(height)))
        key=(str(path),px,py)
        if key not in self.image_cache:
            img=Image.open(path).convert('RGBA').resize((px,py),Image.Resampling.LANCZOS)
            self.image_cache[key]=ImageTk.PhotoImage(img,master=self.root)
        im=self.image_cache[key]
        self.refs.append(im)
        self.canvas.create_image(*self.p(x,y),image=im,anchor='nw')

    def hit(self,x1,y1,x2,y2,action,tag=None):
        self.hitboxes.append((x1,y1,x2,y2,action,tag))
    def button(self,x1,y1,x2,y2,label,action,selected=False,small=False):
        old_height=y2-y1
        if old_height>30:
            desired=min(old_height+9,max(29,self.appearance.get('button_height',41)))
            mid=(y1+y2)/2
            y1=mid-desired/2;y2=mid+desired/2
        hovering=self.hover==('btn',label)
        highlighted=selected
        active=self.hover_strength if hovering and self.app.config.get('animations',True) else (1.0 if hovering else 0.0)
        bg=self.app.mix(ROW,'#6C5521',active*.75)
        if getattr(self,'new_ui',False):
            bg=self.app.mix('#1C333F',YELLOW,active*.13)
        self.round(x1,y1,x2,y2,7,YELLOW if highlighted else bg,
                   YELLOW if highlighted else self.app.mix(BORDER,'#D2A32B',active*.8))
        self.txt((x1+x2)/2,(y1+y2)/2,label,12 if small else 14,
                 '#121519' if highlighted else FG,bold=highlighted,anchor='center',limit=x2-x1-12)
        self.hit(x1,y1,x2,y2,action,('btn',label))
    def rr_panel(self,x1,y1,x2,y2):
        self.round(x1,y1,x2,y2,17,PANEL,'#303D44')
    def title_band(self,x,y,title,width=420):
        if getattr(self,'new_ui',False):
            width=max(width,1298-x)
            self.round(x,y,x+width,y+46,8,'#213641','#3D5663')
            self.round(x+8,y+8,x+13,y+38,3,YELLOW)
            self.txt(x+28,y+23,title.upper(),17,FG,True,limit=width-55)
            return
        # The detail title bars run to the right inner margin of the panel,
        # rather than stopping abruptly a hundred pixels before its edge.
        width=max(width,1298-x)
        self.round(x,y,x+width,y+46,6,YELLOW)
        self.txt(x+19,y+24,title,20,'#111615',True,limit=width-38)

    def on_search(self,*_):
        self.offset=0
        if self.canvas.winfo_exists():self.redraw()
    def show(self,page):
        if page not in NAV:return
        self.page=page
        self.app.page=page
        self.popup=None
        self.offset=0
        self.search.set('')
        if page=='cargo':
            rows=self.visible_cargo()
            self.offset=next((i for i,c in enumerate(rows) if c['id']==self.selected_cargo),0)
            if rows and not any(c['id']==self.selected_cargo for c in rows):self.selected_cargo=rows[0]['id']
        self.selection_y=None
        self.selection_target_y=None
        self.detail_started=0
        self.redraw()
    def animations_on(self):
        return bool(self.app.config.get('animations',True) and self.appearance.get('animations',True))

    def queue_motion(self):
        if not self.animations_on() or self.motion_job is not None:return
        self.motion_job=self.root.after(16,self.motion_frame)

    def motion_frame(self):
        self.motion_job=None
        try:
            if not self.canvas.winfo_exists() or not self.animations_on():return
        except tk.TclError:return
        keep=False
        target=1.0 if self.hover else 0.0
        diff=target-self.hover_strength
        if abs(diff)>.025:
            self.hover_strength+=diff*min(.8,.29*self.appearance.get('animation_speed',100)/100)
            keep=True
        else:self.hover_strength=target
        if self.selection_y is not None and self.selection_target_y is not None:
            diff=self.selection_target_y-self.selection_y
            if abs(diff)>.55:
                self.selection_y+=diff*min(.9,.23*self.appearance.get('animation_speed',100)/100)
                keep=True
            else:self.selection_y=self.selection_target_y
        if self.detail_started and time.monotonic()-self.detail_started<.24*100/max(30,self.appearance.get('animation_speed',100)):
            keep=True
        self.redraw()
        if keep:self.queue_motion()

    def onleave(self):
        if self.hover is not None:
            self.hover=None
            if self.animations_on():self.queue_motion()
            else:self.redraw()
    def onmove(self,e):
        pos=self.local(e.x,e.y)
        hovered=None
        if pos:
            x,y=pos
            for a,b,c,d,action,tag in reversed(self.hitboxes):
                if a<=x<=c and b<=y<=d:
                    hovered=tag;break
        if hovered!=self.hover:
            self.hover=hovered
            if self.animations_on():
                self.hover_strength=0.0
                self.queue_motion()
            self.redraw()
        self.canvas.configure(cursor='hand2' if hovered else 'arrow')
    def local(self,x,y):
        if not self.scale:return None
        return (self._inverse_x((x-self.ox)/self.sx),(y-self.oy)/self.sy)
    def onclick(self,e):
        pos=self.local(e.x,e.y)
        if not pos:return
        x,y=pos
        # Process the title-bar maximize control before decorative/overlapping
        # canvas hit areas. This button must always change actual OS geometry.
        if (1231 <= x <= 1268 and 0 <= y <= 45) if getattr(self, 'reference_ui', False) else (1218 <= x <= 1256 and 21 <= y <= 60):
            self.toggle_maximize()
            return
        for a,b,c,d,fn,tag in reversed(self.hitboxes):
            if a<=x<=c and b<=y<=d:
                fn()
                return
        if self.popup:self.popup=None;self.redraw()
    def onwheel(self,e):
        # Windows wheel is 120 per notch; X11 uses buttons 4/5.
        delta = (1 if getattr(e,'num',None)==4 else -1 if getattr(e,'num',None)==5 else
                 1 if getattr(e,'delta',0)>0 else -1 if getattr(e,'delta',0)<0 else 0)
        if not delta:return
        if getattr(e,'state',0)&0x0004:  # Ctrl + mouse wheel = interface zoom
            self.zoom_by(5*delta)
            return 'break'
        try:
            x=self.root.winfo_pointerx()-self.canvas.winfo_rootx()
            y=self.root.winfo_pointery()-self.canvas.winfo_rooty()
        except tk.TclError:return
        pos=self.local(x,y)
        if self.page=='calculator' and pos:
            if 265<pos[0]<756 and 229<pos[1]<700:
                self.scroll(-2*delta);return 'break'
            if 793<pos[0]<1304 and 296<pos[1]<621:
                self.scroll_load(-2*delta);return 'break'
        if self.page=='cargo' and getattr(self,'reference_ui',False) and pos and 254<pos[0]<1305 and 208<pos[1]<717:
            self.scroll(-2*delta)
            return 'break'
        if self.page in ('cargo','recipes','manual') and pos and 255<pos[0]<760 and 230<pos[1]<707:
            self.scroll(-2*delta)
            return 'break'
        # At >100% pan vertically when outside the list; mouse-wheel browsing
        # is always prioritized inside the cargo/recipe list.
        # Background is always full-bleed; no pan into empty canvas margins.

    def pan_begin(self,e):
        self.pan_start=(e.x,e.y,self.pan_x,self.pan_y)
    def pan_drag(self,e):
        # Scrolling and zooming never shift the entire desktop-like canvas.
        pass
    def pan_end(self,e):self.pan_start=None
    def set_zoom(self,value):
        self.app.config['ui_scale']=max(75,min(150,int(value)))
        self.appearance['ui_scale']=self.app.config['ui_scale']
        self.app.config['appearance']=self.appearance
        save_json(SETTINGS_FILE,self.app.config)
        self.redraw()
    def zoom_by(self,d):self.set_zoom(self.app.config.get('ui_scale',100)+d)
    def row_count(self):
        if self.page=='cargo' and getattr(self,'reference_ui',False): return 8
        return max(4,min(7,int(435/max(56,self.appearance.get('row_height',71)))))

    def scroll(self,d):
        if self.page=='manual':
            total=len(self.manual_items());self.manual_offset=max(0,min(max(0,total-self.row_count()),self.manual_offset+d))
            self.selection_y=None;self.redraw();return
        if self.page=='calculator':
            total=len(self.calculator_items());self.calc_offset=max(0,min(max(0,total-5),self.calc_offset+d))
            self.redraw();return
        if self.page=='cargo':total=len(self.visible_cargo())
        elif self.page=='recipes':total=len(self.visible_recipes())
        else:return
        self.offset=max(0,min(max(0,total-self.row_count()),self.offset+d))
        # The selection outline must jump with the scrolling content.
        self.selection_y=None
        self.redraw()
    def onkey(self,e):
        if e.keysym=='Down':self.scroll(1)
        elif e.keysym=='Up':self.scroll(-1)
    def escape(self,e=None):
        if getattr(self,'cargo_detail_open',False):self.cargo_detail_open=False;self.redraw();return
        if self.popup:self.popup=None;self.redraw()

    def redraw(self):
        if not self.canvas.winfo_exists():return
        w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height())
        # Fill exactly one actual OS window at *every* zoom level.  Zoom adjusts
        # glyphs / widgets only; it must never shrink the whole rendered app
        # into a black desktop-like frame (the earlier 'window in window' bug).
        zoom=self.app.config.get('ui_scale',100)/100
        self.sx=w/W
        self.sy=h/H
        self.scale=min(self.sx,self.sy)*zoom
        self.ox=self.oy=0
        self.canvas.delete('all')
        self.hitboxes=[];self.refs=[]
        sz=(max(1,int(W*self.sx)),max(1,int(H*self.sy)))
        if sz not in self.bg_cache:
            self.bg_cache[sz]=ImageTk.PhotoImage(theme_background(self.base_image,self.app.config.get('theme','game')).resize(sz,Image.Resampling.LANCZOS),master=self.root)
        self.canvas.create_image(self.ox,self.oy,image=self.bg_cache[sz],anchor='nw')
        self.draw_nav()
        self.draw_toolbar()
        if self.page=='cargo':self.draw_cargo()
        elif self.page=='recipes':self.draw_recipes()
        elif self.page=='calculator':self.draw_calculator()
        elif self.page=='manual':self.draw_manual()
        elif self.page=='settings':self.draw_settings()
        self.draw_popup()
        if self.page in ('cargo','recipes','manual'):
            ref_search=self.page=='cargo' and getattr(self,'reference_ui',False)
            x,y=self.p(337 if ref_search else 327,177 if ref_search else 202)
            self.search_entry.place(x=int(x),y=int(y-(12 if ref_search else 14)*self.sy),
                                    width=int((305 if ref_search else 204)*self.sx),
                                    height=int((26 if ref_search else 28)*self.sy))
            if ref_search:self.search_entry.configure(bg='#1B3745')
            self.search_entry.config(font=self.font(12,text=self.search.get() or ('Поиск' if self.lang=='ru' else 'Search')))
            if not self.search.get() and self.root.focus_get()!=self.search_entry:
                self.search_placeholder.configure(text='Поиск...' if self.lang=='ru' else 'Search...',font=self.font(12,text='Поиск' if self.lang=='ru' else 'Search'))
                self.search_placeholder.place(x=int(x+(0 if ref_search else 9)*self.sx),y=int(y-12*self.sy),
                    width=int((283 if ref_search else 180)*self.sx),height=int(25*self.sy))
                if ref_search:self.search_placeholder.configure(bg='#1B3745',anchor='w')
                self.search_placeholder.lift()
            else:self.search_placeholder.place_forget()
        else:
            self.search_entry.place_forget()
            self.search_placeholder.place_forget()
        if self.page=='calculator':
            x,y=self.p(285,208)
            self.calc_search_entry.place(x=int(x),y=int(y-14*self.sy),
                                         width=max(20,int(438*self.sx)),height=max(20,int(32*self.sy)))
            self.calc_search_entry.configure(font=self.font(12,text=self.calc_search.get()))
            if not self.calc_search.get() and self.root.focus_get()!=self.calc_search_entry:
                self.calc_search_placeholder.configure(text='Поиск груза...' if self.lang=='ru' else 'Search cargo...',font=self.font(12))
                self.calc_search_placeholder.place(x=int(x+9*self.sx),y=int(y-12*self.sy),
                                      width=max(20,int(396*self.sx)),height=max(19,int(27*self.sy)))
                self.calc_search_placeholder.lift()
            else:self.calc_search_placeholder.place_forget()
        else:
            self.calc_search_entry.place_forget()
            self.calc_search_placeholder.place_forget()

    # v24 approved Cargo workspace: reference layout at logical 1319 x 747.
    # The masthead is user-approved art, while all controls, rows and details
    # are real data-driven canvas widgets with working hitboxes.
    REFERENCE_FEATURED=('metal_beams','service_spare_parts_special','consumables',
                        'rail_section','metal_rolls','medium_logs','wooden_planks','bricks')

    def _build_reference_background(self):
        canvas=Image.new('RGB',(W,H),'#07131A')
        painter=ImageDraw.Draw(canvas)
        for y in range(92,H):
            t=(y-92)/max(1,H-92)
            painter.line((0,y,W,y), fill=(round(7+4*t),round(19+6*t),round(26+8*t)))
        painter.rectangle((0,92,237,H),fill='#081821')
        painter.line((237,92,237,H),fill='#34515F',width=2)
        painter.line((0,91,W,91),fill='#365361',width=2)
        painter.rectangle((239,94,1316,745),outline='#244351',width=2)
        art=ROOT/'assets'/'ui'/'v24_approved_header.png'
        if art.is_file():
            with Image.open(art) as source:
                canvas.paste(source.convert('RGB').resize((W,92),Image.Resampling.LANCZOS),(0,0))
        else:
            painter.rectangle((0,0,W,91),fill='#0B2430')
        self.base_image=canvas
        self.bg_cache={}

    def _draw_reference_nav(self):
        # Four workspaces stacked at the top, Settings anchored at the bottom.
        self.line(22,141,214,141,'#33515D')
        ys={'cargo':155,'recipes':226,'calculator':297,'manual':368,'settings':656}
        for page in NAV:
            y=ys[page]
            chosen=self.page==page
            self.round(16,y,220,y+57,8,'#234553' if chosen else '#102731',
                       '#FFC21B' if chosen else '#23424D',2 if chosen else 1)
            self.nav_image(page,51,y+29,32,32,chosen)
            self.txt(86,y+29,self.t(page),16,FG,chosen,limit=121)
            self.hit(16,y,221,y+58,lambda page=page:self.show(page),('nav',page))
        self.line(21,498,214,498,'#31515A')
        self.txt(49,528,'⌁',34,'#85CBB7',True)
        self.txt(84,526,'РЕЖИМ' if self.lang=='ru' else 'MODE',14,'#8DD6BC',True)
        self.txt(84,550,'Только чтение' if self.lang=='ru' else 'Read-only',12,'#95B1BE')
        self.line(21,574,214,574,'#31515A')

    def _draw_reference_frame(self,title):
        self.round(240,93,1317,744,7,'#061922','#24424E')
        self.txt(260,122,title.upper(),30,FG,True,limit=360)
        self.line(260,145,1298,145,'#35505B')
        self.round(254,208,1303,722,8,'#0B2029','#244651')

    def _reference_visible_cargo(self):
        q=self.search.get().strip().casefold()
        category=getattr(self,'cargo_category','')
        entries=[entry for entry in CARGO_DB
                 if (not category or self._reference_category(entry)==category)
                 and q in ' '.join((entry['id'],entry.get('ru',''),entry.get('en',''))).casefold()]
        ordered=sort_cargo(entries,self.app.config['sort'],self.lang)
        # Keep the approved eight cargo illustrations first in the untouched
        # opening state, without replacing any catalog data or search behavior.
        if not q and not category and self.app.config['sort']=='name_asc':
            by_id={entry['id']:entry for entry in ordered}
            first=[by_id[key] for key in self.REFERENCE_FEATURED if key in by_id]
            featured=set(self.REFERENCE_FEATURED)
            return first+[entry for entry in ordered if entry['id'] not in featured]
        return ordered

    def _reference_category(self,item):
        cid=item['id']
        if cid.startswith('service_spare_parts') or cid.endswith('spare_parts'):
            return 'spares'
        if cid=='consumables':return 'materials'
        if cid=='rail_section':return 'metal'
        return item.get('category') or 'special'

    def _reference_category_name(self,category):
        translations={'spares':('Запчасти','Spare parts'),'materials':('Материалы','Supplies'),
                      'metal':('Металл','Metal'),'wood':('Дерево','Wood'),
                      'logs':('Дерево','Wood'),'construction':('Стройматериалы','Construction'),
                      'industrial':('Промышленный','Industrial'), 'supplies':('Снабжение','Supplies'),
                      'container':('Контейнер','Container'),'mission':('Задание','Mission'),
                      'special':('Особый','Special'),'agriculture':('Сельхоз','Agriculture')}
        ru,en=translations.get(category, (category,category))
        return ru if self.lang=='ru' else en

    def _reference_sort_label(self):
        return {'name_asc':('По названию','By name'),
                'name_desc':('Название Я–А','Name Z–A'),
                'slots_asc':('Слоты ↑','Slots ↑'),
                'slots_desc':('Слоты ↓','Slots ↓')}.get(self.app.config['sort'],('По названию','By name'))[self.lang!='ru']

    def _draw_reference_cargo(self):
        self._draw_reference_frame(self.t('cargo'))
        # All three top controls are functional: search, sort, category.
        self.round(259,156,657,195,7,'#1B3745','#365765')
        self.txt(282,176,'⌕',30,YELLOW,True)
        self.txt(690,175,'Сортировка:' if self.lang=='ru' else 'Sort:',13,FG)
        self.round(798,156,990,195,7,'#0D2732','#2A4552')
        self.txt(812,175,self._reference_sort_label(),15,FG,limit=145)
        self.txt(970,175,'⌄',22,FG,anchor='center')
        self.hit(798,156,990,195,lambda:self.toggle('ref_sort'),('btn','sort'))
        self.txt(1020,175,'Категория:' if self.lang=='ru' else 'Category:',13,FG)
        self.round(1116,156,1297,195,7,'#0D2732','#2A4552')
        cat=self._reference_category_name(self.cargo_category) if self.cargo_category else ('Все' if self.lang=='ru' else 'All')
        self.txt(1130,175,cat,15,YELLOW,limit=137)
        self.txt(1277,175,'⌄',22,FG,anchor='center')
        self.hit(1116,156,1297,195,lambda:self.toggle('ref_category'),('btn','category'))
        visible=self.visible_cargo()
        self.offset=min(self.offset,max(0,len(visible)-8))
        rows=visible[self.offset:self.offset+8]
        for i,item in enumerate(rows):
            y=215+i*59
            cid=item['id']
            chosen=cid==self.selected_cargo
            hovered=self.hover==('row',cid)
            surface='#493A18' if chosen else '#102D35' if i%2 else '#0E2933'
            self.round(256,y,1287,y+56,7,surface,YELLOW if chosen else '#28434E',2 if chosen else 1)
            self.image(cid,324,y+28,88,60)
            label=display_cargo(cid,self.lang)
            self.txt(390,y+28,label,18,FG,chosen,limit=375)
            category=self._reference_category_name(self._reference_category(item))
            # Compact pill, as in the approved screenshot. Category is catalog-driven.
            chipw=max(82,min(156,round(21+8.0*len(category))))
            self.round(789,y+15,789+chipw,y+42,14,'#1B3843' if not chosen else '#494530','#385665')
            self.txt(789+chipw/2,y+28,category,12,FG,anchor='center',limit=chipw-12)
            self.line(944,y+11,944,y+46,'#39515A')
            # Never infer weight from cargo slots or undocumented numbers.
            masslabel=cargo_weight_label(item,self.lang)
            self._reference_weight_icon(990,y+28)
            self.txt(1012,y+28,masslabel,11,FG,limit=74)
            self.line(1087,y+11,1087,y+46,'#39515A')
            self._reference_slot_icon(1137,y+28)
            slots=item.get('slots')
            if slots is None:slotlabel='—'
            elif self.lang=='ru':slotlabel=f'× {slots} '+('слот' if slots==1 else 'слота' if slots in (2,3,4) else 'слотов')
            else:slotlabel=f'× {slots} slots'
            self.txt(1162,y+28,slotlabel,16,FG,limit=119)
            self.hit(256,y,1287,y+56,lambda cid=cid:self._reference_select(cid),('row',cid))
        if not rows:
            self.txt(325,298,'Грузы не найдены' if self.lang=='ru' else 'No cargo found',18,MUTED)
        # Bottom track and dynamic vertical scroll thumb.
        self.round(256,707,1287,715,5,'#0A1D25')
        self.round(1290,215,1298,715,5,'#263D47')
        if len(visible)>8:
            h=max(46,500*8/len(visible))
            yp=216+(500-h)*(self.offset/max(1,len(visible)-8))
            self.round(1291,yp,1297,yp+h,3,YELLOW)
        else:self.round(1291,216,1297,382,3,YELLOW)
        if self.cargo_detail_open:
            self._draw_reference_detail()

    def _reference_weight_icon(self,cx,cy):
        # Draw the simple white weight/bag glyph shown in the approved mockup.
        top=[(cx-5,cy-7),(cx-2,cy-13),(cx+3,cy-13),(cx+6,cy-7)]
        body=[(cx-6,cy-5),(cx+7,cy-5),(cx+11,cy+7),(cx+9,cy+12),
              (cx-9,cy+12),(cx-11,cy+7)]
        for shape in (top,body):
            points=[]
            for x,y in shape:points.extend(self.p(x,y))
            self.canvas.create_polygon(points,fill='',outline=FG,width=max(1.2,2*self.scale),joinstyle='round')

    def _reference_slot_icon(self,cx,cy):
        # Three outlines, without the dark square backing from v22.
        for dy in (-7,0,7):
            vertices=[(cx,cy+dy-7),(cx+12,cy+dy-1),
                      (cx,cy+dy+5),(cx-12,cy+dy-1)]
            pts=[]
            for x,y in vertices:pts.extend(self.p(x,y))
            self.canvas.create_polygon(pts,fill='',outline=FG,width=max(1.2,1.7*self.scale))

    def _reference_select(self,cid):
        if cid==self.selected_cargo:
            self.cargo_detail_open=True
        else:
            self.selected_cargo=cid
            self.cargo_detail_open=False
        self.redraw()

    def _draw_reference_detail(self):
        item=CARGO[self.selected_cargo]
        self.round(704,234,1279,675,12,'#102A35','#FFC21B',2)
        self.txt(732,268,display_cargo(self.selected_cargo,self.lang),21,FG,True,limit=470)
        self.txt(1246,260,'×',28,YELLOW,anchor='center')
        self.hit(1220,238,1271,286,lambda:self._reference_close_detail(),('btn','close_detail'))
        self.image(self.selected_cargo,840,396,200,154)
        self.txt(969,359,'Категория:' if self.lang=='ru' else 'Category:',15,MUTED)
        self.txt(969,393,self._reference_category_name(self._reference_category(item)),17,FG)
        self.txt(969,440,'Слотов:' if self.lang=='ru' else 'Slots:',15,MUTED)
        self.txt(969,474,str(item.get('slots')) if item.get('slots') is not None else '—',18,YELLOW,True)
        self.txt(969,502,('Вес: ' if self.lang=='ru' else 'Weight: ')
                 + cargo_weight_label(item,self.lang),13,FG,True,limit=260)
        self.line(739,521,1252,521,'#2F4B57')
        self.txt(742,562,'Нажми ×, чтобы вернуться к списку' if self.lang=='ru'
                 else 'Press × to return to the list',13,MUTED)

    def _reference_close_detail(self):
        self.cargo_detail_open=False
        self.redraw()

    def _reference_choose_category(self,category):
        self.cargo_category=category
        self.popup=None
        self.offset=0
        self.cargo_detail_open=False
        self.redraw()

    def _draw_reference_popup(self):
        if self.popup=='ref_sort':
            x1,y1,x2=798,198,990
            self.round(x1,y1,x2,y1+168,7,'#0C2631','#52717E')
            for i,key in enumerate(('name_asc','name_desc','slots_asc','slots_desc')):
                y=y1+5+i*40
                self.round(x1+4,y,x2-4,y+37,5,'#28424D' if self.app.config['sort']==key else '#102B35')
                self.txt(x1+14,y+19,{'name_asc':'По названию','name_desc':'Название Я–А',
                         'slots_asc':'Слоты ↑','slots_desc':'Слоты ↓'}[key],13,FG,limit=164)
                self.hit(x1+4,y,x2-4,y+37,lambda key=key:self.choose_sort(key),('popup',key))
        elif self.popup=='ref_category':
            keys=['']+sorted({self._reference_category(x) for x in CARGO_DB})
            x1,y1,x2=1093,198,1298
            self.round(x1,y1,x2,y1+len(keys)*33+9,7,'#0C2631','#52717E')
            for i,key in enumerate(keys):
                y=y1+5+i*33
                self.round(x1+4,y,x2-4,y+30,4,'#28424D' if self.cargo_category==key else '#102B35')
                caption=self._reference_category_name(key) if key else 'Все'
                self.txt(x1+13,y+15,caption,12,FG,limit=175)
                self.hit(x1+4,y,x2-4,y+30,lambda key=key:self._reference_choose_category(key),('popup',key))
        elif self.popup=='language':
            self.popup=None
        # Other screens keep existing popup behavior.

    def draw_toolbar(self):
        if getattr(self,'reference_ui',False):
            if self.lang!='ru':
                self.rect(350,0,782,90,'#08202B')
                self.txt(363,28,'EXPEDITION ASSISTANT',21,FG,True,limit=392)
                self.txt(363,60,'PLANNING  •  CRAFT  •  CARGO  •  CALCULATIONS',11,MUTED,limit=398)
            # Brand and truck belong to the approved decorative masthead.
            # All caption controls remain live (the image is not a clickable screenshot).
            self.round(1026,7,1177,43,6,'#1B3945','#4A6B79')
            self.txt(1101,25,'⟳  ОБНОВИТЬ' if self.lang=='ru' else '⟳  REFRESH',11,FG,True,anchor='center')
            self.hit(1026,7,1177,43,self.app.refresh_game_data,('btn','refresh'))
            self.hit(1191,0,1228,45,self.minimize_window,('btn','min'))
            self.hit(1231,0,1268,45,self.toggle_maximize,('btn','max'))
            self.hit(1271,0,1319,45,self.app.close_app,('btn','close'))
            return
        if getattr(self,'new_ui',False):
            # Simple Windows caption controls and localized language switch.
            self.txt(46,38,'SNOWRUNNER',24,FG,True,limit=202)
            self.txt(47,75,'HELPER',12,YELLOW,True,limit=210)
            self.txt(352,37,'ЭКСПЕДИЦИОННЫЙ ЦЕНТР' if self.lang=='ru' else 'EXPEDITION CONTROL',17,FG,True,limit=390)
            self.txt(353,70,'ПЛАНИРОВАНИЕ  •  КРАФТ  •  ГРУЗЫ' if self.lang=='ru' else 'PLANNING  •  CRAFT  •  CARGO',11,MUTED,limit=400)
            self.round(884,25,1021,61,7,'#203440','#3B5562')
            self.txt(899,43,'RU' if self.lang=='ru' else 'EN',13,YELLOW,True)
            self.txt(944,43,'Русский' if self.lang=='ru' else 'English',11,FG,limit=57)
            self.txt(1007,43,'⌄',15,FG)
            self.hit(884,25,1021,61,lambda:self.toggle('language'),('btn','lang'))
            self.button(1027,25,1166,61,'⟳  '+('Обновить' if self.lang=='ru' else 'Refresh'),
                        self.app.refresh_game_data,small=True)
            for x1,x2,symbol,action,tag in [(1174,1214,'−',self.minimize_window,'min'),
                                              (1218,1256,'□',self.toggle_maximize,'max'),
                                              (1260,1305,'×',self.app.close_app,'close')]:
                self.round(x1,21,x2,60,7,'#203440','#38505F')
                self.txt((x1+x2)/2,40,symbol,18,FG,anchor='center')
                self.hit(x1,21,x2,60,action,('btn',tag))
            return
        # Real, compact in-app window controls; native Windows caption is hidden.
        self.round(884,25,1021,61,7,'#222A30')
        if self.lang=='ru':
            self.rect(897,32,921,39,'#F8F8F8');self.rect(897,39,921,46,'#2247BD');self.rect(897,46,921,54,'#D82D38')
        else:
            self.rect(897,33,921,54,'#1F426D');self.txt(909,44,'EN',10,'#FFFFFF',True,anchor='center')
        self.txt(929,43,'Русский' if self.lang=='ru' else 'English',11,FG,limit=83)
        self.txt(1006,44,'⌄',15,FG)
        self.hit(884,25,1021,61,lambda:self.toggle('language'),('btn','lang'))
        self.button(1027,25,1166,61,'⟳  '+('Обновить' if self.lang=='ru' else 'Refresh'),
                    self.app.refresh_game_data,small=True)
        for x1,x2,txt,action,tag in [(1174,1214,'—',self.minimize_window,'min'),
                                      (1218,1256,'□',self.toggle_maximize,'max'),
                                      (1260,1305,'×',self.app.close_app,'close')]:
            self.round(x1,21,x2,60,7,'#222A30')
            self.txt((x1+x2)/2,41,txt,18,FG,anchor='center')
            self.hit(x1,21,x2,60,action,('btn',tag))

    def _usable_screen_area(self):
        """Windows work area excludes taskbar; other platforms use screen bounds."""
        if os.name == 'nt':
            try:
                import ctypes
                from ctypes import wintypes
                rect = wintypes.RECT()
                if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                    if rect.right > rect.left and rect.bottom > rect.top:
                        return rect.left, rect.top, rect.right, rect.bottom
            except (AttributeError, OSError, ValueError):
                pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def toggle_maximize(self):
        """Switch between full usable desktop and the original window size."""
        self._window_drag = None
        self._window_resize = None
        if not self.maximized:
            # Preserve window size and position before maximizing.
            self.restore_geometry = self.root.geometry()
            left, top, right, bottom = self._usable_screen_area()
            self.maximized = True
            self.root.geometry(f'{right-left}x{bottom-top}{left:+d}{top:+d}')
        else:
            self.maximized = False
            self.root.geometry(getattr(self, 'restore_geometry', '1319x747+80+80'))
            self.root.after(250, self._save_geometry)
        self.redraw()

    def on_double_click_header(self, event):
        """Standard title-bar double-click action, restricted to empty header area."""
        point = self.local(event.x, event.y)
        if point and 280 <= point[0] <= 855 and 0 <= point[1] <= 85:
            self.toggle_maximize()
            return 'break'

    def nav_image(self,page,x,y,width,height,chosen=False):
        override=self.appearance.get('nav_icons',{}).get(page,'')
        path=Path(override) if override and Path(override).is_file() else ROOT/'assets'/'ui'/'nav'/f'{page}.png'
        if not path.exists():return
        pwidth,pheight=max(1,int(self.s(width))),max(1,int(self.s(height)))
        key=(str(path),pwidth,pheight,chosen)
        if key not in self.image_cache:
            im=Image.open(path).convert('RGBA')
            im.thumbnail((pwidth,pheight),Image.Resampling.LANCZOS)
            if getattr(self,'reference_ui',False) and not (override and Path(override).is_file()):
                alpha=im.getchannel('A')
                im=Image.new('RGBA',im.size,(255,194,27,0) if chosen else (237,244,247,0))
                im.putalpha(alpha)
            elif chosen and not (override and Path(override).is_file()):
                # Black box glyph is already extracted from selected cargo.
                # Other nav assets are white: render dark when selected.
                if page!='cargo':
                    alpha=im.getchannel('A')
                    im=Image.new('RGBA',im.size,(16,22,24,0));im.putalpha(alpha)
            elif page=='cargo' and not (override and Path(override).is_file()):
                alpha=im.getchannel('A')
                im=Image.new('RGBA',im.size,(231,234,235,0));im.putalpha(alpha)
            self.image_cache[key]=ImageTk.PhotoImage(im,master=self.root)
        im=self.image_cache[key];self.refs.append(im)
        self.canvas.create_image(*self.p(x,y),image=im,anchor='center')

    def draw_nav(self):
        if getattr(self,'reference_ui',False):
            return self._draw_reference_nav()
        if getattr(self,'new_ui',False):
            self.txt(27,148,'РАЗДЕЛЫ' if self.lang=='ru' else 'WORKSPACE',11,MUTED,True)
            self.line(28,166,228,166,'#34515C')
            for page in NAV:
                y=NAV_Y[page]
                chosen=page==self.page
                surface='#263D49' if chosen else '#14232C'
                self.round(24,y,236,y+55,9,surface,YELLOW if chosen else '#29404C',2 if chosen else 1)
                if chosen:self.round(24,y+6,29,y+49,2,YELLOW)
                self.nav_image(page,58,y+27,36,36,False)
                self.txt(91,y+27,self.t(page),15,FG,chosen,limit=136)
                # Selected border signals location; no chevron to overlap long labels.
                self.hit(24,y,239,y+56,lambda p=page:self.show(p),('nav',page))
            self.line(27,530,228,530,'#34515C')
            self.txt(28,556,'●  ЛОКАЛЬНЫЙ РЕЖИМ' if self.lang=='ru' else '●  OFFLINE MODE',11,'#81C5B1',True)
            self.txt(28,581,'Файлы игры: только чтение' if self.lang=='ru' else 'Game files: read-only',10,MUTED,limit=199)
            self.txt(29,614,'ПАРАМЕТРЫ' if self.lang=='ru' else 'PREFERENCES',10,MUTED,True)
            return
        for page in NAV:
            y=NAV_Y[page]
            chosen=(page==self.page)
            if chosen:
                self.round(29,y,243,y+56,6,YELLOW)
                self.rect(30,y+7,242,y+49,'#F8B916')
            else:
                # Clean, uninterrupted dark navigation panel.
                self.round(30,y,243,y+56,5,'#141C20')
            color='#111619' if chosen else '#F1F1F1'
            self.nav_image(page,61,y+28,40,40,chosen)
            self.txt(101,y+28,self.t(page),16,color,True if chosen else False,limit=137)
            self.hit(29,y,245,y+58,lambda p=page:self.show(p),('nav',page))

    def draw_frame(self,title):
        if getattr(self,'reference_ui',False) and self.page=='cargo':
            return self._draw_reference_frame(title)
        if getattr(self,'new_ui',False):
            self.round(262,129,1305,730,13,PANEL,'#304654')
            self.txt(280,156,title.upper(),25,FG,True)
            self.round(1072,143,1286,176,11,'#1E3440','#3B5967')
            self.txt(1178,159,'●  ЛОКАЛЬНАЯ БАЗА' if self.lang=='ru' else '●  LOCAL DATABASE',10,'#83D0B4',True,anchor='center',limit=191)
            self.line(280,179,1287,179,'#344C5B')
            self.round(262,233,759,704,12,'#14232D','#344C5B')
            self.round(767,233,1303,704,12,'#14232D','#344C5B')
            return
        self.rect(251,123,1311,703,PANEL)
        # The workspace is continuous across the full width of the window.
        self.txt(281,155,title,26,FG,True)
        self.rr_panel(258,235,759,700)
        self.rr_panel(769,235,1309,700)

    def toggle(self,name):self.popup=None if self.popup==name else name;self.redraw()
    def choose_sort(self,val):
        self.app.config['sort']=val
        save_json(SETTINGS_FILE,self.app.config)
        self.popup=None;self.offset=0;self.manual_offset=0;self.redraw()
    def change(self,key,val):
        self.popup=None
        self.app.change(key,val)
    def search_ui(self):
        if getattr(self,'new_ui',False):
            self.round(281,186,553,222,7,'#213540','#425B67')
            self.txt(296,203,'⌕',25,YELLOW)
            self.txt(581,203,'Сортировка:' if self.lang=='ru' else 'Sort:',13,MUTED)
            return
        self.round(281,186,553,222,7,'#20272B',BORDER)
        self.txt(297,203,'⌕',25,FG)
        self.txt(581,203,'Сортировка:' if self.lang=='ru' else 'Sort:',13)
    def visible_cargo(self):
        if getattr(self,'reference_ui',False) and self.page=='cargo':
            return self._reference_visible_cargo()
        q=self.search.get().strip().casefold()
        verified={cid for rec in BUILTIN_RECIPES+self.app.official for cid in (list(rec.get('inputs',{}))+list(rec.get('outputs',{})))}
        entries=[x for x in CARGO_DB
                 if (not self.cargo_verified_only or x['id'] in verified)
                 and q in (' '.join([x['id'],x.get('ru',''),x.get('en','')])).casefold()]
        return sort_cargo(entries,self.app.config['sort'],self.lang)
    def toggle_cargo_scope(self):
        self.cargo_verified_only=not self.cargo_verified_only
        self.offset=0
        entries=self.visible_cargo()
        if entries and self.selected_cargo not in {c['id'] for c in entries}:
            self.selected_cargo=entries[0]['id']
        self.selection_y=None
        self.redraw()

    def draw_cargo(self):
        if getattr(self,'reference_ui',False):
            return self._draw_reference_cargo()
        self.draw_frame(self.t('cargo'))
        self.search_ui()
        self.round(905,186,1160,225,6,'#253039',BORDER)
        self.txt(921,204,('Из игровых рецептов ▾' if self.cargo_verified_only else 'Весь каталог ▾') if self.lang=='ru'
                 else ('Game-recipe cargo ▾' if self.cargo_verified_only else 'All catalog cargo ▾'),12,FG,True,limit=222)
        self.hit(905,186,1161,227,self.toggle_cargo_scope,('btn','verified'))
        sort_code=self.app.config['sort']
        sort_labels={
            'name_asc':'По алфавиту (А–Я)' if self.lang=='ru' else 'Alphabetical (A–Z)',
            'name_desc':'По алфавиту (Я–А)' if self.lang=='ru' else 'Alphabetical (Z–A)',
            'slots_asc':'Слоты ↑' if self.lang=='ru' else 'Slots ↑',
            'slots_desc':'Слоты ↓' if self.lang=='ru' else 'Slots ↓'}
        self.round(683,187,875,223,7,'#252D32',BORDER)
        self.txt(699,205,sort_labels[sort_code],12,FG,limit=151)
        self.txt(855,205,'⌄',18)
        self.hit(683,187,875,224,lambda:self.toggle('sort'),('btn','sort'))
        visible=self.visible_cargo()
        self.offset=min(self.offset,max(0,len(visible)-self.row_count()))
        self.draw_rows(visible,'cargo')
        before=set(self.canvas.find_all())
        self.draw_cargo_detail()
        self.slide_detail(before)

    def draw_rows(self,items,kind):
        # Rows respond to the appearance editor's row-height setting.
        visible=items[self.offset:self.offset+self.row_count()]
        if not visible and kind=='recipes':
            self.txt(286,330,'Нет подтверждённых рецептов.' if self.lang=='ru' else 'No verified recipes.',17,MUTED)
            self.txt(286,370,'Добавь свой или импортируй из игры' if self.lang=='ru' else 'Create or import from game files',12,MUTED)
        target=None
        for i,item in enumerate(visible):
            step=self.appearance.get('row_height',71)
            y=247+i*step
            id_=item['id']
            selected=(self.selected_cargo==id_ if kind=='cargo' else self.selected_recipe is item)
            hovered=self.hover==('row',id_)
            amount=(self.hover_strength if self.animations_on() and self.appearance.get('hover_glow',True) else 1.) if hovered else 0.
            bg=('#55451D' if selected else self.app.mix(ROW,'#5C4B21',amount*.53))
            border=self.app.mix('#26323A','#E9B329',amount*.82)
            self.round(271,y,726,y+step-5,9,bg,border)
            if selected:target=y
            if kind=='recipes':
                # New imported/personal recipes have no bundled recipe art: use output cargo icon.
                output_cid=next(iter(item.get('outputs',{})),None)
                self.image(output_cid,320,y+(step-5)/2,80,min(step-9,61)) if output_cid else None
            else:self.image(id_,320,y+(step-5)/2,80,min(step-9,61))
            text=display_cargo(id_,self.lang) if kind=='cargo' else text_value(item.get('name'),self.lang)
            self.txt(379+(self.appearance.get('padding',12)-12)*.6,y+(21 if kind=='recipes' else (step-5)/2),text,14,FG,True if selected else False,limit=318)
            if kind=='recipes':self.txt(379,y+step-19,display_recipe_location(item,self.lang),10,MUTED,limit=336)
            if kind=='cargo':
                sz=item.get('slots');label=(f'{sz} '+('слота' if self.lang=='ru' and sz in (2,3,4) else 'слот' if self.lang=='ru' and sz==1 else 'слотов' if self.lang=='ru' else 'slots') if sz is not None else '—')
            else: label=''
            if kind=='cargo':
                self.round(635,y+max(6,(step-38)/2),712,y+max(6,(step-38)/2)+33,6,'#353B40', '#6E767B')
                self.txt(673,y+(step-5)/2,label,11,FG,anchor='center',limit=69)
            action=(lambda cid=id_:self.select_cargo(cid)) if kind=='cargo' else (lambda rec=item:self.select_recipe(rec))
            self.hit(271,y,727,y+step-5,action,('row',id_))
        # Eased yellow focus border follows the selected row.
        self.selection_target_y=target
        if target is None:self.selection_y=None
        elif self.selection_y is None or not self.animations_on() or not self.appearance.get('smooth_select',True):self.selection_y=float(target)
        if self.selection_y is not None:
            yy=self.selection_y
            if self.animations_on():
                self.round(267,yy-3,730,yy+step-2,12,'', '#745516', 2)
                self.round(269,yy-1,728,yy+step-4,10,'', '#C99316', 2)
            self.round(271,yy,726,yy+step-5,9,'',YELLOW,2)
        # Screenshot-matched vertical scrollbar with actual scroll handling.
        self.round(738,255,749,684,5,'#10171C')
        if len(items)>self.row_count():
            h=max(46,429*self.row_count()/len(items))
            yp=256+(429-h)*(self.offset/max(1,len(items)-self.row_count()))
            self.round(740,yp,747,yp+h,3,'#88949A')
        if not items:self.txt(320,305,self.t('filter_no'),15,MUTED)
        self.round(272,682,725,689,4,'#222B2F')

    def select_cargo(self,cid):
        if cid==self.selected_cargo:return
        self.selected_cargo=cid
        if self.animations_on():
            self.detail_started=time.monotonic()
            self.queue_motion()
        self.redraw()

    def select_recipe(self,rec):
        if self.selected_recipe is rec:return
        self.selected_recipe=rec
        self.app.selected_recipe=rec
        if self.animations_on():
            self.detail_started=time.monotonic()
            self.queue_motion()
        self.redraw()

    def slide_detail(self, before):
        """Translate the detail contents on each animation frame (not the panel)."""
        if not self.animations_on() or not self.appearance.get('slide_detail',True) or not self.detail_started:return
        progress=min(1.,(time.monotonic()-self.detail_started)/(.24*100/max(30,self.appearance.get('animation_speed',100))))
        ease=1-(1-progress)**3
        dx=self.s(28*(1-ease))
        if dx>.35:
            for obj in set(self.canvas.find_all())-before:
                self.canvas.move(obj,dx,0)
        if progress>=1:self.detail_started=0

    def draw_cargo_detail(self):
        cid=self.selected_cargo
        if cid not in CARGO:self.selected_cargo=cid=next(iter(CARGO))
        item=CARGO[cid]
        name=display_cargo(cid,self.lang)
        self.title_band(779,248,name,417)
        self.image(cid,891,393,225,171)
        self.round(1040,316,1288,428,9,'#1A2228','#324048')
        self.txt(1057,354,'▰',21,MUTED)
        self.txt(1102,354,'Размер:' if self.lang=='ru' else 'Size:',13)
        slots=item.get('slots')
        label=(f'{slots} '+ ('слота' if slots in (2,3,4) else 'слот' if slots==1 else 'слотов') if self.lang=='ru' else f'{slots} slots') if slots is not None else '—'
        self.round(1186,335,1277,373,6,YELLOW)
        self.txt(1232,354,label,12,'#181A1B',True,anchor='center')
        self.line(1052,382,1278,382,'#394248')
        self.txt(1057,405,'◇',22,MUTED)
        self.txt(1103,405,'Тип:' if self.lang=='ru' else 'Type:',13)
        cat=(CAT_RU if self.lang=='ru' else CAT_EN).get(item.get('category',''),item.get('category',''))
        self.txt(1267,405,cat,12,FG,anchor='e',limit=125)
        self.txt(1058,438,('Вес: ' if self.lang=='ru' else 'Weight: ')
                 + cargo_weight_label(item,self.lang),12,MUTED,limit=215)
        self.line(796,457,1284,457,'#343B42')
        self.txt(800,478,'⚒',26,YELLOW)
        self.txt(850,479,'Используется в крафте:' if self.lang=='ru' else 'Used in crafting:',17,FG,True)
        related=[r for r in BUILTIN_RECIPES+self.app.official+self.app.custom if cid in r.get('inputs',{})]
        if related:
            for i,rec in enumerate(related[:2]):
                y=495+i*44
                self.round(800,y,1282,y+38,6,'#293239')
                self.txt(816,y+19,text_value(rec.get('name'),self.lang),13,FG,limit=424)
                self.txt(1259,y+19,'›',24,FG,anchor='center')
                self.hit(800,y,1285,y+38,lambda r=rec:self.open_recipe(r),('btn',rec['id']))
        else:self.txt(814,524,self.t('not_used'),13,MUTED)
        self.line(798,587,1284,587,'#343B42')
        self.txt(800,611,'▣',25,YELLOW)
        self.txt(850,610,'Можно создать из:' if self.lang=='ru' else 'Produced from:',17,FG,True)
        source=[r for r in BUILTIN_RECIPES+self.app.official+self.app.custom if cid in r.get('outputs',{})]
        if source:
            self.txt(818,642,text_value(source[0].get('name'),self.lang),13,MUTED,limit=430)
            self.hit(814,624,1253,667,lambda r=source[0]:self.open_recipe(r),('btn','source'))
        else:self.txt(818,642,'—  '+'Нет рецептов крафта' if self.lang=='ru' else '—  No crafting recipes',13,MUTED)
        # Non-destructive cargo icon editing; only the selected cargo is changed.
        self.button(801,662,1040,692,self.t('change_icon'),
                    lambda cid=cid:self.app.change_cargo_icon(cid),small=True)
        if has_custom_icon(cid):
            self.button(1051,662,1284,692,self.t('reset_icon'),
                        lambda cid=cid:self.app.restore_cargo_icon(cid),small=True)

    def open_recipe(self,rec):
        self.previous_context={'page':self.page,'cargo':self.selected_cargo,
                               'offset':self.offset,'manual_offset':self.manual_offset,
                               'query':self.search.get(),'sort':self.app.config['sort']}
        self.selected_recipe=rec;self.app.selected_recipe=rec;self.show('recipes')
        self.selected_recipe=rec
        rows=self.visible_recipes()
        self.offset=next((i for i,x in enumerate(rows) if x is rec or x.get('id')==rec.get('id')),0)
        self.redraw()

    def go_back(self):
        ctx=self.previous_context
        if not ctx:return
        self.previous_context=None
        self.show(ctx['page'])
        self.selected_cargo=ctx['cargo']
        self.app.config['sort']=ctx['sort']
        self.offset=ctx['offset']
        self.manual_offset=ctx['manual_offset']
        self.search.set(ctx['query'])
        self.redraw()

    def visible_recipes(self):
        return filter_recipes(BUILTIN_RECIPES+self.app.official+self.app.custom,self.recipes_region,self.search.get(),self.lang)
    def draw_recipes(self):
        self.draw_frame(self.t('recipes'))
        if self.previous_context:
            self.button(903,183,1290,220,('← Назад к грузу' if self.lang=='ru' else '← Back to cargo'),self.go_back,small=True)
        self.search_ui()
        self.round(683,187,875,223,7,'#252D32',BORDER)
        self.txt(694,205,display_region(self.recipes_region,self.lang) if self.recipes_region else self.t('all_regions'),12,FG,limit=157)
        self.txt(856,204,'⌄',18)
        self.hit(683,187,875,224,lambda:self.toggle('region'),('btn','region'))
        self.draw_rows(self.visible_recipes(),'recipes')
        before=set(self.canvas.find_all())
        self.draw_recipe_detail()
        self.slide_detail(before)

    def draw_recipe_detail(self):
        rec=self.selected_recipe
        if not rec:
            self.title_band(779,248,self.t('recipe_title'),417)
            self.txt(803,334,self.t('choose_recipe'),17,MUTED,limit=440)
            self.txt(803,374,'Импортируй craftSettings из своих игровых файлов' if self.lang=='ru' else 'Import craftSettings from your game files',12,MUTED,limit=459)
        else:
            self.title_band(779,248,text_value(rec.get('name'),self.lang),417)
            self.txt(806,324,display_recipe_location(rec,self.lang),12,MUTED,limit=460)
            self.txt(803,353,self.t('components'),17,FG,True)
            items=list(rec.get('inputs',{}).items())
            if not items and rec.get('generator'):
                self.txt(809,396,'⚡ '+self.t('no_inputs'),13,YELLOW,limit=460)
            for i,(cid,qty) in enumerate(items[:3]):
                yy=378+i*58
                self.round(799,yy,1275,yy+52,6,'#252F35')
                self.image(cid,841,yy+26,55,46)
                self.txt(884,yy+26,display_cargo(cid,self.lang),13,FG,limit=306)
                self.txt(1252,yy+26,'×'+str(qty),17,YELLOW,True,anchor='e')
            yy=558
            self.line(800,yy,1273,yy,'#364047')
            self.txt(803,580,'↓  '+self.t('result'),17,YELLOW,True)
            outs=list(rec.get('outputs',{}).items())
            for i,(cid,qty) in enumerate(outs[:2]):
                y=603+i*45
                self.image(cid,839,y+18,48,43)
                self.txt(886,y+17,display_cargo(cid,self.lang),12,FG,limit=340)
                self.txt(1251,y+17,'×'+str(qty),15,YELLOW,True,anchor='e')
            if rec.get('source_url'):
                self.button(799,673,939,698,self.t('source'),lambda:webbrowser.open(rec['source_url']),small=True)
            if rec.get('source_image'):
                chart_path=(ROOT/rec['source_image']).resolve()
                self.button(799,673,939,698,'Схема' if self.lang=='ru' else 'Chart',
                            lambda p=chart_path:webbrowser.open(p.as_uri()),small=True)
            if rec in self.app.custom:
                self.button(946,673,1064,698,self.t('edit_recipe'),lambda:self.app.recipe_editor(rec),small=True)
                self.button(1070,673,1190,698,self.t('delete_recipe'),lambda:self.app.delete_recipe(rec),small=True)
            else:
                self.button(946,673,1123,698,self.t('copy_recipe'),lambda:self.app.recipe_editor(rec,copy=True),small=True)
            self.button(1132,673,1278,698,'Подробнее' if self.lang=='ru' else 'Details',lambda:self.recipe_full_detail(rec),small=True)
        self.button(282,705,475,730,self.t('add_recipe'),lambda:self.app.recipe_editor(),small=True)
        self.button(482,705,675,730,self.t('import_game'),self.app.import_game_data,small=True)
        self.button(682,705,771,730,'Проверка' if self.lang=='ru' else 'Inspect',
                    self.app.scan_game_folder,small=True)

    def recipe_full_detail(self,rec):
        """Scrollable text details show *all* inputs/outputs, not just preview rows."""
        win=tk.Toplevel(self.root)
        win.title(text_value(rec.get('name'),self.lang))
        win.geometry('610x550')
        win.configure(bg=PANEL)
        wrap=tk.Frame(win,bg=PANEL)
        wrap.pack(fill='both',expand=True,padx=18,pady=18)
        scroll=tk.Scrollbar(wrap)
        scroll.pack(side='right',fill='y')
        box=tk.Text(wrap,bg='#172127',fg=FG,insertbackground=FG,
                    selectbackground='#4D491E',font=('Segoe UI',12),
                    relief='flat',wrap='word',padx=16,pady=16,yscrollcommand=scroll.set)
        box.pack(side='left',fill='both',expand=True)
        scroll.configure(command=box.yview)
        name=text_value(rec.get('name'),self.lang)
        location=display_recipe_location(rec,self.lang)
        parts=[name,location,'',self.t('components')]
        for cid,n in rec.get('inputs',{}).items():
            slot=cargo_slots(cid)
            parts.append(f'  •  {display_cargo(cid,self.lang)} ×{n}'+(f'  ({slot} slots)' if slot is not None else ''))
        if not rec.get('inputs') and rec.get('generator'):parts.append(self.t('no_inputs'))
        parts += ['','↓ '+self.t('result')]
        for cid,n in rec.get('outputs',{}).items():parts.append(f'  •  {display_cargo(cid,self.lang)} ×{n}')
        notes=display_recipe_notes(rec,self.lang)
        if notes:parts+=['',notes]
        box.insert('1.0','\n'.join(parts));box.configure(state='disabled')
        tk.Button(win,text=self.t('cancel'),command=win.destroy,bg=YELLOW,fg='#151515',
                  relief='flat',font=('Segoe UI',11,'bold'),padx=20,pady=6).pack(pady=(0,14))

    def toggle_calc_scope(self):
        self.calc_verified_only=not self.calc_verified_only
        self.calc_offset=0
        self.redraw()

    def _on_calculator_search(self):
        self.calc_offset=0
        if self.page=='calculator' and self.canvas.winfo_exists():self.redraw()

    def calculator_items(self):
        query=self.calc_search.get().strip().casefold()
        verified={cid for recipe in BUILTIN_RECIPES+self.app.official
                  for cid in (list(recipe.get('inputs',{}))+list(recipe.get('outputs',{})))}
        rows=[c for c in CARGO_DB if c.get('slots') is not None
              and (not self.calc_verified_only or c['id'] in verified)
              and query in (c.get('ru','')+' '+c.get('en','')).casefold()]
        return sort_cargo(rows,self.app.config['sort'],self.lang)

    def draw_calculator(self):
        self.draw_frame(self.t('calculator'))
        self.round(273,186,732,232,8,'#20272B',BORDER)
        self.txt(290,252,'МАТЕРИАЛЫ' if self.lang=='ru' else 'MATERIALS',13,YELLOW,True)
        self.round(560,237,728,270,6,'#26333B',BORDER)
        scope_label=('Из рецептов ▾' if self.calc_verified_only else 'Все грузы ▾') if self.lang=='ru' else ('Recipe cargo ▾' if self.calc_verified_only else 'All cargo ▾')
        self.txt(574,254,scope_label,11,FG,True,limit=144)
        self.hit(560,237,729,271,self.toggle_calc_scope,('btn','scope'))
        items=self.calculator_items()
        max_rows=5
        self.calc_offset=max(0,min(self.calc_offset,max(0,len(items)-max_rows)))
        for i,c in enumerate(items[self.calc_offset:self.calc_offset+max_rows]):
            yy=280+i*68
            active=c['id']==self.calculator_cargo
            self.round(273,yy,726,yy+62,7,'#574A20' if active else ROW,YELLOW if active else BORDER)
            self.image(c['id'],317,yy+31,70,54)
            self.txt(371,yy+30,display_cargo(c['id'],self.lang),13,FG,active,limit=265)
            self.txt(705,yy+31,str(c['slots']),13,YELLOW,True,anchor='e')
            self.hit(273,yy,727,yy+62,lambda cid=c['id']:self.choose_calculator(cid),('row',c['id']))
        self.draw_scrollbar(737,280,694,len(items),max_rows,self.calc_offset)
        self.button(292,638,346,675,'−',lambda:self.qty_change(-1))
        self.txt(370,657,str(self.qty),18,FG,True,anchor='center')
        self.button(396,638,451,675,'+',lambda:self.qty_change(1))
        self.button(462,638,729,675,'＋  '+('Добавить' if self.lang=='ru' else 'Add selected'),self.add_load,selected=True,small=True)
        self.title_band(779,248,self.t('load'),417)
        self.txt(807,307,'Грузы в загрузке' if self.lang=='ru' else 'Loaded cargo',13,MUTED)
        n_rows=4
        self.load_offset=max(0,min(self.load_offset,max(0,len(self.app.load)-n_rows)))
        for i,(cid,n) in enumerate(self.app.load[self.load_offset:self.load_offset+n_rows]):
            index=self.load_offset+i
            yy=333+i*69
            self.round(802,yy,1267,yy+63,7,ROW,BORDER)
            self.image(cid,841,yy+32,54,46)
            self.txt(880,yy+22,display_cargo(cid,self.lang),12,FG,limit=247)
            self.txt(878,yy+46,str(cargo_slots(cid))+' '+('слота/ед.' if self.lang=='ru' else 'slots/ea'),10,MUTED,limit=180)
            self.button(1102,yy+13,1137,yy+48,'−',lambda j=index:self.change_load_qty(j,-1),small=True)
            self.txt(1160,yy+31,'×'+str(n),12,YELLOW,True,anchor='center')
            self.button(1185,yy+13,1220,yy+48,'+',lambda j=index:self.change_load_qty(j,1),small=True)
            self.button(1227,yy+13,1262,yy+48,'×',lambda j=index:self.remove_load(j),small=True)
        self.draw_scrollbar(1273,334,608,len(self.app.load),n_rows,self.load_offset)
        if not self.app.load:self.txt(822,390,self.t('empty_load'),15,MUTED)
        self.line(802,621,1280,621,'#39434A')
        self.txt(813,658,f'{self.t("total")}: {calculate_load(self.app.load)}',17,YELLOW,True,limit=465)
        self.button(293,689,501,722,'Черновики' if self.lang=='ru' else 'Drafts',
                    self.app.drafts_dialog,small=True)
        self.button(509,689,726,722,'Маршруты' if self.lang=='ru' else 'Routes',
                    self.app.route_planner_dialog,small=True)

    def draw_scrollbar(self,x,y1,y2,total,visible,offset):
        self.round(x,y1,x+11,y2,5,'#10171C')
        if total>visible:
            track=y2-y1
            thumb=max(38,track*visible/total)
            top=y1+(track-thumb)*(offset/(total-visible))
            self.round(x+2,top,x+9,top+thumb,3,'#9BA7AD')
            self.hit(x-7,y1,x+18,y2,lambda:self.scrollbar_click(x,y1,y2,total,visible),('scroll',x))

    def scrollbar_click(self,x,y1,y2,total,visible):
        try:
            screen_y=self.root.winfo_pointery()-self.canvas.winfo_rooty()
            pos=self.local(0,screen_y)
            if not pos:return
            fraction=max(0,min(1,(pos[1]-y1)/(y2-y1)))
            new=round((total-visible)*fraction)
            if self.page=='calculator':
                if x>1000:self.load_offset=new
                else:self.calc_offset=new
            elif self.page=='manual':self.manual_offset=new
            else:self.offset=new
            self.redraw()
        except tk.TclError:pass

    def scroll_load(self,delta):
        self.load_offset=max(0,min(max(0,len(self.app.load)-4),self.load_offset+delta))
        self.redraw()

    def choose_calculator(self,cid):self.calculator_cargo=cid;self.redraw()
    def qty_change(self,d):self.qty=max(1,min(999,self.qty+d));self.redraw()
    def add_load(self):
        if cargo_slots(self.calculator_cargo) is None:return
        # Merge duplicate cargo for a compact manifest.
        for i,(cid,qty) in enumerate(self.app.load):
            if cid==self.calculator_cargo:
                self.app.load[i]=(cid,qty+self.qty);break
        else:self.app.load.append((self.calculator_cargo,self.qty))
        self.load_offset=max(0,len(self.app.load)-4)
        self.app.save_profile_draft()
        self.redraw()
    def change_load_qty(self,index,delta):
        if 0<=index<len(self.app.load):
            cid,qty=self.app.load[index]
            new=qty+delta
            if new<1:self.app.load.pop(index)
            else:self.app.load[index]=(cid,min(new,9999))
            self.load_offset=min(self.load_offset,max(0,len(self.app.load)-4))
            self.app.save_profile_draft()
            self.redraw()
    def remove_load(self,index):
        if 0<=index<len(self.app.load):
            self.app.load.pop(index)
            self.load_offset=min(self.load_offset,max(0,len(self.app.load)-4))
            self.app.save_profile_draft()
            self.redraw()

    def manual_items(self):
        used={cid for recipe in BUILTIN_RECIPES+self.app.official for cid in list(recipe.get('inputs',{}))+list(recipe.get('outputs',{}))}
        entries=CARGO_DB if not self.manual_verified_only else [c for c in CARGO_DB if c['id'] in used]
        q=self.search.get().casefold().strip()
        if q:entries=[c for c in entries if q in (c.get('ru','')+' '+c.get('en','')).casefold()]
        return sort_cargo(entries,self.app.config['sort'],self.lang)

    def select_manual(self,cid):
        self.selected_cargo=cid
        self.app.last_selected_cargo=cid
        self.redraw()

    def draw_manual(self):
        self.draw_frame(self.t('manual'))
        self.search_ui()
        sort_labels={
            'name_asc':'По алфавиту (А–Я)' if self.lang=='ru' else 'Alphabet (A–Z)',
            'name_desc':'По алфавиту (Я–А)' if self.lang=='ru' else 'Alphabet (Z–A)',
            'slots_asc':'Слоты ↑' if self.lang=='ru' else 'Slots ↑',
            'slots_desc':'Слоты ↓' if self.lang=='ru' else 'Slots ↓'}
        self.round(683,187,875,223,7,'#252D32',BORDER)
        self.txt(699,205,sort_labels[self.app.config['sort']],12,FG,limit=157)
        self.txt(855,205,'⌄',18)
        self.hit(683,187,875,224,lambda:self.toggle('sort'),('btn','sort'))
        entries=self.manual_items()
        count=self.row_count();self.manual_offset=min(self.manual_offset,max(0,len(entries)-count))
        self.txt(285,236,(f'{len(entries)} материалов' if self.lang=='ru' else f'{len(entries)} cargo types'),12,YELLOW,True)
        step=self.appearance.get('row_height',71)
        for i,c in enumerate(entries[self.manual_offset:self.manual_offset+count]):
            y=261+i*step;cid=c['id'];active=cid==self.selected_cargo
            self.round(271,y,727,y+step-6,8,'#55451C' if active else ROW,YELLOW if active else BORDER,2 if active else 1)
            self.image(cid,316,y+(step-6)/2,70,step-9)
            self.txt(370,y+(step-6)/2,display_cargo(cid,self.lang),14,FG,active,limit=260)
            slots=c.get('slots');self.txt(699,y+(step-6)/2,str(slots) if slots is not None else '—',12,YELLOW if active else FG,anchor='e')
            self.hit(271,y,727,y+step-6,lambda id=cid:self.select_manual(id),('row',cid))
        if len(entries)>count:
            self.round(737,259,749,690,6,'#1B2329')
            height=max(44,430*count/len(entries))
            ty=259+(430-height)*self.manual_offset/max(1,len(entries)-count)
            self.round(739,ty,747,ty+height,4,'#8D9AA0')
        self.draw_cargo_detail()
        self.button(285,703,730,730,('Показать все грузы' if self.manual_verified_only else 'Только из игровых рецептов') if self.lang=='ru' else ('Show all cargo' if self.manual_verified_only else 'Only game-recipe cargo'),self.toggle_manual_scope,small=True)

    def toggle_manual_scope(self):
        self.manual_verified_only=not self.manual_verified_only
        self.manual_offset=0;self.redraw()

    def cycle_theme(self):
        themes=('game','dark','light','forest')
        current=self.app.config.get('theme','game')
        target=themes[(themes.index(current)+1)%len(themes)] if current in themes else 'game'
        self.app.change('theme',target)

    def draw_settings(self):
        self.draw_frame(self.t('settings'))
        ru=self.lang=='ru'
        self.title_band(781,247,'Настройки приложения' if ru else 'Application settings',416)
        self.txt(294,208,'ОФОРМЛЕНИЕ / APPEARANCE',18,YELLOW,True)
        self.round(275,252,721,440,8,ROW,BORDER)
        self.txt(293,289,'SnowRunner Game Edition',19,FG,True)
        preset=PRESETS[self.appearance['preset']]
        self.txt(293,329,preset['ru' if ru else 'en'],14,MUTED)
        self.txt(293,370,('Темы • цвета • фон • шрифты • размеры' if ru else 'Themes • colors • background • fonts • sizes'),12,MUTED,limit=395)
        self.button(291,394,707,438,'⚙  '+('НАСТРОИТЬ ВНЕШНИЙ ВИД' if ru else 'CUSTOMIZE APPEARANCE'),self.app.appearance_editor,selected=True,small=True)
        if getattr(self,'new_ui',False):
            self.txt(293,460,'UI: ЭКСПЕДИЦИЯ' if ru else 'UI: EXPEDITION',12,YELLOW,True)
            self.button(480,445,707,485,'Классический UI' if ru else 'Classic UI',
                        lambda:self.app.change('ui_design','classic'),small=True)
        else:
            self.txt(293,461,'UI: CLASSIC',12,YELLOW,True)
            self.button(480,445,707,485,'Новый UI' if ru else 'New UI',
                        lambda:self.app.change('ui_design','expedition'),small=True)
        self.txt(296,494,'Сервисные параметры' if ru else 'Application options',17,FG,True)
        self.button(289,524,708,567,('О программе — читать полностью' if ru else 'About — read complete text'),self.about_dialog,small=True)
        self.button(289,588,708,631,('Редактор пользовательских рецептов' if ru else 'Recipe editor'),lambda:self.app.recipe_editor(),small=True)
        self.txt(800,319,self.t('lang'),16,FG,True)
        self.button(800,345,1019,385,'Русский',lambda:self.change('lang','ru'),selected=ru,small=True)
        self.button(1035,345,1280,385,'English',lambda:self.change('lang','en'),selected=not ru,small=True)
        self.settings_step('Масштаб интерфейса' if ru else 'Interface zoom','ui_scale',449)
        self.settings_step('Размер текста' if ru else 'Text size','text_size',531)
        theme=self.app.config.get('theme','game')
        self.button(289,635,708,658,('Цветовая тема: ' if ru else 'Color theme: ')
                    + THEME_LABELS.get(theme,THEME_LABELS['game'])[0 if ru else 1] + '  ↻',
                    self.cycle_theme,small=True)
        self.button(289,663,708,707,('Подключить игровые файлы SnowRunner' if ru
                                      else 'Connect SnowRunner game files'),
                    self.app.game_connection_dialog,small=True)
        self.txt(802,603,'МИНИ-ОКНО КРАФТА' if ru else 'CRAFT OVERLAY',14,YELLOW,True)
        if hasattr(self.app,'overlay'):
            self.button(802,629,1042,669,('Показать мини-окно' if ru else 'Show overlay'),self.app.overlay.toggle,small=True)
            self.button(1047,629,1281,669,('Клавиша: ' if ru else 'Shortcut: ')+self.app.overlay.shortcut,
                        self.app.overlay.shortcut_dialog,small=True)
        self.txt(803,688,'Горячая клавиша работает поверх оконной игры' if ru else 'Hotkey works with windowed game',10,MUTED,limit=479)
        self.button(801,707,1093,735,'⬇  '+('ПРОВЕРИТЬ ОБНОВЛЕНИЯ' if ru else 'CHECK FOR UPDATES'),
                    self.app.updater.open_settings,small=True)

    def about_dialog(self):
        win=tk.Toplevel(self.root);win.title('О приложении' if self.lang=='ru' else 'About')
        win.geometry('750x560');win.configure(bg=PANEL)
        v=tk.Text(win,wrap='word',bg=PANEL,fg=FG,font=('Segoe UI',12),padx=22,pady=22,relief='flat')
        scroll=tk.Scrollbar(win,command=v.yview);scroll.pack(side='right',fill='y')
        v.configure(yscrollcommand=scroll.set);v.pack(fill='both',expand=True)
        lines=['SnowRunner Helper','',self.t('about'),'',self.t('icon_legend'),'',self.t('image_folder'),'',
               'Рецепты из локальных игровых файлов, личные рецепты и справочник по материалам.' if self.lang=='ru' else 'Local game-file recipes, custom recipes and cargo reference.']
        v.insert('1.0','\n'.join(lines));v.configure(state='disabled')

    def settings_step(self,caption,key,y):
        val=self.app.config.get(key,100)
        self.txt(803,y,caption+f'  {val}%',15,FG,True)
        self.button(1100,y-15,1150,y+20,'−',lambda k=key:self.app.adjust(k,-10),small=True)
        self.button(1157,y-15,1207,y+20,'+',lambda k=key:self.app.adjust(k,10),small=True)
        self.button(1213,y-15,1280,y+20,'100%',lambda k=key:self.change(k,100),small=True)
        self.line(804,y+31,1264,y+31,'#35424A')
        fillw=460*max(0,min(1,(val-75)/(140-75 if key=='ui_scale' else 150-75)))
        self.rect(804,y+29,804+fillw,y+34,YELLOW)

    def font_control(self,script,title,y):
        ru=self.lang=='ru'
        family=self.app.font_manager.label(script)
        self.txt(803,y,title,15,FG,True)
        self.txt(803,y+27,family,12,MUTED,limit=215)
        self.button(1040,y+9,1186,y+45,'Загрузить…' if ru else 'Import…',
                    lambda s=script:self.app.import_font(s),small=True)
        self.button(1194,y+9,1280,y+45,'Сброс' if ru else 'Reset',
                    lambda s=script:self.app.reset_font(s),small=True)

    def draw_popup(self):
        if getattr(self,'reference_ui',False) and self.page=='cargo':
            return self._draw_reference_popup()
        if not self.popup:return
        if self.popup=='sort':
            vals=[(k,self.t(k)) for k in SORT_MODES]
            x1,y1,x2=683,230,945
            self.round(x1,y1,x2,y1+4*41+9,7,'#172026',BORDER)
            for i,(val,caption) in enumerate(vals):
                yy=y1+5+i*41
                self.round(x1+6,yy,x2-6,yy+37,5,'#574619' if self.app.config['sort']==val else ROW)
                self.txt(x1+17,yy+18,caption,12,FG,limit=236)
                self.hit(x1+6,yy,x2-6,yy+37,lambda v=val:self.choose_sort(v),('popup',val))
        elif self.popup=='region':
            keys=['']+sorted({r.get('region','') for r in BUILTIN_RECIPES+self.app.official+self.app.custom if r.get('region')},key=lambda k:display_region(k,self.lang).casefold())
            maxpage=max(0,(len(keys)-1)//10)
            self.region_page=max(0,min(self.region_page,maxpage))
            x1,y1,x2=683,230,1005
            for i,key in enumerate(keys[self.region_page*10:self.region_page*10+10]):
                yy=y1+i*36
                self.round(x1,yy,x2,yy+35,4,ROW if i%2 else '#1B262C',BORDER)
                self.txt(x1+12,yy+18,display_region(key,self.lang) if key else self.t('all_regions'),12,FG,limit=306)
                self.hit(x1,yy,x2,yy+35,lambda k=key:self.choose_region(k),('popup',key))
            if maxpage:
                nav_y=y1+10*36+7
                self.round(x1,nav_y,x2,nav_y+35,5,'#263238',BORDER)
                self.txt(x1+16,nav_y+17,'◀',14,YELLOW)
                self.txt((x1+x2)/2,nav_y+17,f'{self.region_page+1} / {maxpage+1}',12,FG,anchor='center')
                self.txt(x2-26,nav_y+17,'▶',14,YELLOW)
                self.hit(x1,nav_y,x1+95,nav_y+35,lambda:self.page_regions(-1),('popup','previous'))
                self.hit(x2-95,nav_y,x2,nav_y+35,lambda:self.page_regions(1),('popup','next'))
        elif self.popup=='language':
            options=[('ru','Русский'),('en','English')]
            x1=884
            x2=1021
            for i,(key,label) in enumerate(options):
                y1=67+i*40
                self.round(x1,y1,x2,y1+38,5,ROW,BORDER)
                self.txt(x1+14,y1+19,label,12,FG,limit=x2-x1-22)
                field='lang' if self.popup=='language' else 'theme'
                self.hit(x1,y1,x2,y1+38,lambda k=key,f=field:self.change(f,k),('popup',key))
    def page_regions(self,delta):
        self.region_page=max(0,self.region_page+delta)
        self.redraw()

    def choose_region(self,key):
        self.recipes_region=key;self.offset=0;self.popup=None;self.redraw()
