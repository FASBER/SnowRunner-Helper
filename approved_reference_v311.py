"""Approved SnowRunner reference screen adapter (v0.31.15).

The original GameScreen's working recipe/calculator/settings logic stays intact.
Only its approved Expedition Cargo canvas presentation is adapted; all state,
profile saves, game imports and OTA security remain owned by the original app.
The artwork is cut from the user's explicitly approved reference image. User
names, balances, missions and region data are NEVER taken from that artwork.
"""
from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image,ImageTk

_INSTALLED = False
_BASE = None
_FEATURED = (
    'metal_beams', 'multistage_pump', 'garbage', 'special_cargo',
    'empty_container', 'slate_blocks', 'medium_planks', 'medium_pipes',
)


def decorate_background(image, theme='game'):
    """Use reference scenery only on the full-size Expedition work surface."""
    # Only the existing Expedition/reference canvas has this exact sidebar.
    # The classic skin must retain its original background and geometry.
    if image.size != (1319, 747) or image.getpixel((20,180))[:3] != (8,24,33):
        return image
    from core import ROOT
    path = ROOT / 'assets' / 'ui' / 'approved_reference_v316.png'
    if not path.is_file():
        path = ROOT / 'assets' / 'ui' / 'approved_reference_v311.png'
    if not path.is_file():
        return image
    try:
        with Image.open(path) as content:
            base = content.convert('RGB')
        # Keep alternate light/forest/dark theme behavior (never force dark).
        if theme != 'game':
            from PIL import ImageOps
            lower = ImageOps.grayscale(base.crop((0,109,1319,747)))
            styles = {
                'light':('#D7DFDE','#FAFBF5'),
                'forest':('#092018','#35533A'),
                'dark':('#0C1219','#263C48'),
            }
            low, high = styles.get(theme,styles['dark'])
            base.paste(ImageOps.colorize(lower,low,high),(0,109))
        return base
    except (OSError,ValueError):
        return image


def _is_ref(self):
    return bool(getattr(self,'reference_ui',False))


def _stats(self):
    """Only recognized read-only snapshot fields may appear as player data."""
    if getattr(self.app,'active_profile_key','local')=='local':
        return {'profile':'Локальный профиль','money':None,'exp':None,
                'objectives':None,'trucks':None,'garages':None}
    name = str(self.app.active_profile_key)
    result = {'profile':'Профиль '+name[:12], 'money':None,
              'exp':None,'objectives':None,'trucks':None,'garages':None}
    try:
        d=self.app.profiles.read(self.app.active_profile_key)
        snap=d.get('game_snapshot') or {}
        stats=snap.get('statistics') or {}
        result['money']=stats.get('money')
        result['exp']=stats.get('experience')
        result['objectives']=(snap.get('objectives') or {}).get('completed')
        fleet=snap.get('retained_trucks') or {}
        result['trucks']=fleet.get('count') if fleet.get('available') else None
        garages=snap.get('garages') or {}
        result['garages']=garages.get('open_count') if garages.get('available') else None
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        pass
    return result


def _action(self,page):
    self.popup=None
    if page in ('home','garage'):
        self._approved_extra=page
        self.page='cargo';self.app.page='cargo';self.redraw();return
    self._approved_extra=None
    self.show(page)


def _draw_nav(self):
    if not _is_ref(self):
        return self._v311_previous_nav()
    ru=self.lang=='ru'
    names=(('home','Главная','Home','⌂',184),
           ('cargo','Грузы','Cargo','▣',243),
           ('recipes','Крафт','Craft','⚒',300),
           ('garage','Гараж','Garage','▤',355),
           ('calculator','Калькулятор','Calculator','▦',411),
           ('settings','Настройки','Settings','⚙',660))
    focused=getattr(self,'_approved_extra',None) or self.page
    for page,russian,english,icon,y in names:
        selected = page==focused
        self.round(8,y,177,y+46,8,'#173947' if selected else '#10242E',
                   '#FFC21B' if selected else '#2E4852',2 if selected else 1)
        _nav_icon(self,page,39,y+23,selected)
        self.txt(69,y+23,russian if ru else english,16,'#F5F5F2',selected,limit=100)
        self.hit(8,y,178,y+46,lambda p=page:_action(self,p),('nav',page))
    self.line(11,645,176,645,'#23414B')


def _nav_icon(self,page,x,y,selected):
    """Actual icon artwork cropped from the approved reference, not substitutes."""
    from core import ROOT
    custom=getattr(self,'appearance',{}).get('nav_icons',{}).get(page,'')
    path=Path(custom) if custom and Path(custom).is_file() else ROOT/'assets'/'ui'/'approved_nav'/f'{page}.png'
    if not path.is_file():return
    try:
        cache=getattr(self,'_approved_nav_cache',None)
        if cache is None:cache=self._approved_nav_cache={}
        key=(page,str(path),selected,max(1,int(self.s(44))))
        if key not in cache:
            with Image.open(path) as source:
                img=source.convert('RGBA')
            if selected and not custom:
                alpha=img.getchannel('A')
                img=Image.new('RGBA',img.size,(255,194,27,0))
                img.putalpha(alpha)
            dim=key[3]
            img.thumbnail((dim,dim),Image.Resampling.LANCZOS)
            cache[key]=ImageTk.PhotoImage(img,master=self.root)
        if hasattr(self,'refs'):self.refs.append(cache[key])
        self.canvas.create_image(*self.p(x,y),image=cache[key],anchor='center')
    except (OSError,ValueError):pass


def _draw_toolbar(self):
    if not _is_ref(self):
        return self._v311_previous_toolbar()
    from game_ui import FG,MUTED,YELLOW
    ru=self.lang=='ru'
    stats=_stats(self)
    # The image supplies the decorative masthead/title; these are actual
    # clickable native-window controls, not a dead screenshot.
    self.hit(1185,0,1225,25,self.minimize_window,('btn','min'))
    self.hit(1231,0,1268,45,self.toggle_maximize,('btn','max'))
    self.hit(1271,0,1319,45,self.app.close_app,('btn','close'))
    # Actual profile is never substituted with the mockup's fictional account.
    self.txt(212,128,('Игрок:' if ru else 'Profile:'),12,MUTED)
    self.txt(267,131,stats['profile'],15,FG,True,limit=180)
    self.line(470,118,470,159,'#365563')
    self.txt(491,125,'★',24,YELLOW,True)
    self.txt(524,119,'Опыт' if ru else 'XP',10,MUTED)
    self.txt(524,144,_number(stats['exp']),17,FG,True)
    self.line(641,118,641,159,'#365563')
    self.txt(661,125,'▣',21,YELLOW,True)
    self.txt(691,119,'Баланс' if ru else 'Balance',10,MUTED)
    self.txt(691,144,(_number(stats['money'])+' ₵') if stats['money'] is not None else 'Нет данных',17,FG,True,limit=194)
    self.line(875,118,875,159,'#365563')
    self.txt(889,126,'Выполнено заданий:' if ru else 'Completed tasks:',11,MUTED)
    self.txt(1039,127,_number(stats['objectives']),15,FG,True,limit=110)
    self.round(1108,116,1279,151,6,'#183A46','#54707A')
    self.txt(1194,133,'⟳  ОБНОВИТЬ' if ru else '⟳  REFRESH',12,FG,True,anchor='center')
    self.hit(1108,116,1279,151,self.app.refresh_game_data,('btn','refresh_game'))


def _number(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool) and value >= 0:
        return f'{value:,.0f}'.replace(',',' ')
    return '—'


def _available_locations(self, field):
    """Build filter choices only from actual recipe records containing cargo."""
    from game_ui import CARGO, BUILTIN_RECIPES
    values=set()
    for rec in BUILTIN_RECIPES+self.app.official+self.app.custom:
        raw=rec.get(field)
        if (isinstance(raw,str) and raw.strip() and
                any(cid in CARGO for cid in list(rec.get('inputs',{}))+list(rec.get('outputs',{})))):
            values.add(raw.strip())
    return sorted(values,key=lambda x:_location_label(x,self.lang).casefold())


def _location_label(key,lang):
    from core import display_region
    label=display_region(key,lang)
    return label if label not in ('Карта не определена','Unknown map') else key


def _choose_location(self,field,value):
    setattr(self,'_v311_filter_'+field,value)
    self.offset=0
    self.popup=None
    self._v311_popup_page=0
    rows=self.visible_cargo()
    if rows and self.selected_cargo not in {x['id'] for x in rows}:
        self.selected_cargo=rows[0]['id']
    self.redraw()


def _visible(self):
    from game_ui import CARGO_DB, sort_cargo
    q=self.search.get().strip().casefold()
    category=getattr(self,'cargo_category','')
    region=getattr(self,'_v311_filter_region','')
    map_name=getattr(self,'_v311_filter_map','')
    if region or map_name:
        from game_ui import BUILTIN_RECIPES
        found=set()
        for rec in BUILTIN_RECIPES+self.app.official+self.app.custom:
            if ((not region or rec.get('region')==region) and
                    (not map_name or rec.get('map')==map_name)):
                found.update(rec.get('inputs',{}))
                found.update(rec.get('outputs',{}))
    else:found=None
    items=[x for x in CARGO_DB
           if (found is None or x['id'] in found)
           and (not category or self._reference_category(x)==category)
           and q in (x['id']+' '+x.get('ru','')+' '+x.get('en','')).casefold()]
    ordered=sort_cargo(items,self.app.config['sort'],self.lang)
    if not q and not category and self.app.config['sort']=='name_asc':
        byid={x['id']:x for x in ordered}
        order=[byid[k] for k in _FEATURED if k in byid]
        return order+[x for x in ordered if x['id'] not in _FEATURED]
    return ordered


def _show_location_popup(self,option):
    self._v311_popup_page=0
    self.toggle(option)

def _draw_cargo(self):
    if not _is_ref(self):
        return self._v311_previous_reference_cargo()
    if getattr(self,'_approved_extra',None) in ('home','garage'):
        return _draw_extra(self,self._approved_extra)
    from game_ui import CARGO,FG,MUTED,YELLOW
    from core import display_cargo
    from cargo_weight_v317 import cargo_weight_label
    ru=self.lang=='ru'
    # Reference: separate persistent left catalog and right detail panel.
    self.round(197,177,908,709,7,'#071922','#294550')
    self.round(914,177,1295,709,8,'#0B212C','#42616E')
    self.txt(206,201,'ГРУЗЫ' if ru else 'CARGO',27,FG,True)
    self.line(206,216,894,216,'#34525B')
    # Filters are all true controls with working popups.
    self.round(206,225,450,256,6,'#1A3745','#385F6D')
    self.txt(219,241,'⌕',26,YELLOW,True)
    self.txt(465,240,'Сортировка:' if ru else 'Sort:',12,FG)
    self.round(542,225,673,256,5,'#0A202A','#32535F')
    keys={'name_asc':('По названию','By name'),'name_desc':('Название Я–А','Name Z–A'),
          'slots_asc':('Слоты ↑','Slots ↑'),'slots_desc':('Слоты ↓','Slots ↓')}
    self.txt(554,240,keys.get(self.app.config['sort'],keys['name_asc'])[0 if ru else 1],11,FG,limit=96)
    self.txt(661,240,'⌄',18,FG,anchor='center')
    self.hit(542,225,673,256,lambda:self.toggle('ref_sort'),('btn','sort'))
    self.txt(702,240,'Карта:' if ru else 'Map:',12,FG)
    self.round(753,225,895,256,5,'#0A202A','#32535F')
    map_filter=getattr(self,'_v311_filter_map','')
    self.txt(764,240,_location_label(map_filter,self.lang) if map_filter else ('Все карты' if ru else 'All maps'),11,FG,limit=109)
    self.txt(883,240,'⌄',18,FG,anchor='center')
    self.hit(753,225,895,256,lambda:_show_location_popup(self,'v311_maps'),('btn','maps'))
    self.txt(463,282,'Регион:' if ru else 'Region:',12,FG)
    self.round(516,268,658,298,5,'#0A202A','#32535F')
    region_filter=getattr(self,'_v311_filter_region','')
    self.txt(526,282,_location_label(region_filter,self.lang) if region_filter else ('Все регионы' if ru else 'All regions'),11,FG,limit=112)
    self.txt(647,282,'⌄',18,FG,anchor='center')
    self.hit(516,268,658,298,lambda:_show_location_popup(self,'v311_regions'),('btn','regions'))
    self.txt(698,282,'Категория:' if ru else 'Category:',12,FG)
    self.round(766,268,895,298,5,'#0A202A','#32535F')
    category=self._reference_category_name(self.cargo_category) if self.cargo_category else ('Все категории' if ru else 'All categories')
    self.txt(776,282,category,11,FG,limit=100)
    self.txt(882,282,'⌄',17,FG,anchor='center')
    self.hit(766,268,895,298,lambda:self.toggle('ref_category'),('btn','category'))
    entries=self.visible_cargo()
    if not getattr(self,'_v311_opened_cargo_once',False):
        self.offset=0;self._v311_opened_cargo_once=True
    self.offset=max(0,min(self.offset,max(0,len(entries)-8)))
    if entries and self.selected_cargo not in {x['id'] for x in entries}:
        self.selected_cargo=entries[0]['id']
    for i,item in enumerate(entries[self.offset:self.offset+8]):
        y=309+i*45
        cid=item['id']; selected=cid==self.selected_cargo
        surface='#55411A' if selected else '#102F3A' if i%2 else '#0B2630'
        self.round(201,y,890,y+45,6,surface,'#FFCC20' if selected else '#2D4C56',2 if selected else 1)
        self.image(cid,249,y+22,76,41)
        self.txt(302,y+22,display_cargo(cid,self.lang),15,FG,selected,limit=242)
        category=self._reference_category_name(self._reference_category(item))
        self.round(544,y+10,648,y+36,11,'#193C48' if not selected else '#4B4528','#3A5D67')
        self.txt(596,y+22,category,10,FG,anchor='center',limit=96)
        self.line(655,y+10,655,y+35,'#39545D')
        self._reference_weight_icon(695,y+22)
        self.txt(714,y+22,cargo_weight_label(item,self.lang),11,FG,limit=82)
        self.line(769,y+10,769,y+35,'#39545D')
        self._reference_slot_icon(796,y+22)
        count=item.get('slots')
        caption=(('× '+str(count)+' '+('слот' if count==1 else 'слота' if count in (2,3,4) else 'слотов')) if ru
                 else ('× '+str(count)+' slots')) if count is not None else '—'
        self.txt(820,y+22,caption,12,FG,limit=68)
        self.hit(201,y,892,y+45,lambda cid=cid:_select(self,cid),('row',cid))
    # Vertical list scroll bar retains a real mouse click target.
    self.round(899,309,906,680,4,'#163440')
    if len(entries)>8:
        h=max(35,371*8/len(entries))
        yp=309+(371-h)*self.offset/max(1,len(entries)-8)
        self.round(900,yp,906,yp+h,3,YELLOW)
        self.hit(894,309,910,681,lambda:_scroll_to(self),('btn','scroll'))
    else:self.round(900,310,906,678,3,YELLOW)
    if not entries:self.txt(239,345,'Грузы не найдены' if ru else 'No cargo found',16,MUTED)
    _draw_detail(self)


def _select(self,cid):
    self.selected_cargo=cid
    self.app.last_selected_cargo=cid
    self.cargo_detail_open=False
    self.popup=None
    self.redraw()


def _scroll_to(self):
    self.offset=(self.offset+8)%max(1,len(self.visible_cargo()))
    self.redraw()


def _related_recipes(self,cid):
    from game_ui import BUILTIN_RECIPES
    results=[]
    for recipe in BUILTIN_RECIPES + self.app.official + self.app.custom:
        if cid in recipe.get('inputs',{}):
            results.append(recipe)
    return results


def _draw_detail(self):
    from game_ui import CARGO,FG,MUTED,YELLOW
    from core import display_cargo,text_value
    from cargo_weight_v317 import cargo_weight_label
    cid=self.selected_cargo
    if cid not in CARGO: return
    item=CARGO[cid]; ru=self.lang=='ru'
    name=display_cargo(cid,self.lang)
    # Persistent detail card. Different cargo selection changes it immediately.
    self.txt(1066,210,name,20,FG,True,anchor='center',limit=330)
    self.image(cid,982,268,132,95)
    self.round(1064,235,1168,261,12,'#193846','#395666')
    self.txt(1116,248,self._reference_category_name(self._reference_category(item)),11,FG,anchor='center',limit=98)
    self._reference_weight_icon(1084,281)
    self.txt(1100,281,cargo_weight_label(item,self.lang),14,FG,limit=80)
    self.line(1175,268,1175,296,'#365460')
    self._reference_slot_icon(1197,282)
    slots=item.get('slots')
    label=('× '+str(slots)+' '+('слот' if slots==1 else 'слота' if slots in (2,3,4) else 'слотов') if ru
           else '× '+str(slots)+' slots') if slots is not None else '—'
    self.txt(1221,282,label,12,FG,limit=69)
    self.line(929,309,1281,309,'#40565C')
    self.txt(941,333,'▣',23,YELLOW,True)
    self.txt(967,331,'Используется в:' if ru else 'Used in:',16,FG,True)
    related=_related_recipes(self,cid)
    if related:
        # Distinguish regionally different recipes sharing the same name;
        # never show identical-looking bullet points with no context.
        from core import display_recipe_location
        titles=[text_value(r.get('name'),self.lang) or '—' for r in related]
        duplicates={title for title in titles if titles.count(title)>1}
        for i,r in enumerate(related[:3]):
            y=361+i*29
            name=titles[i]
            if name in duplicates:
                location=display_recipe_location(r,self.lang)
                if location and location not in ('Регион не указан','Region not specified'):
                    name+=' — '+location
            self.txt(965,y,'•',22,YELLOW)
            self.txt(984,y,name,11,FG,limit=290)
            self.hit(964,y-13,1283,y+13,lambda rec=r:self.open_recipe(rec),('btn','recipe'))
        if len(related)>3:
            self.txt(1218,430,('+'+str(len(related)-3)),10,YELLOW,anchor='e')
    else:
        self.txt(954,383,'Нет подтверждённых рецептов' if ru else 'No verified recipes',12,MUTED)
    self.line(929,434,1281,434,'#40565C')
    self.txt(942,455,'☷',21,YELLOW,True)
    self.txt(969,453,'Связанные задания:' if ru else 'Related tasks:',16,FG,True)
    # The catalog has no cargo-to-objective mapping. Do not invent it.
    self.txt(954,491,'Нет подтверждённых данных' if ru else 'No verified data',12,MUTED)
    self.line(929,538,1281,538,'#40565C')
    self.txt(942,562,'⌖',24,YELLOW,True)
    self.txt(968,559,'Расположение:' if ru else 'Location:',16,FG,True)
    location=_location(self,cid)
    if location:
        self.txt(949,603,location,12,FG,limit=319)
    else:
        self.txt(949,603,'Карта и регион не подтверждены' if ru else 'Map and region unverified',12,MUTED,limit=320)
    self.line(929,656,1281,656,'#40565C')
    from cargo_weight_v317 import MAPRUNNER_PACKED_MASS_KG
    source=('MapRunner' if cid in MAPRUNNER_PACKED_MASS_KG else
            ('локальные файлы игры' if item.get('mass_source') in ('local_game_data','official_game_files') else 'нет данных'))
    self.txt(935,685,('Источник веса: ' if ru else 'Weight source: ')+source,10,MUTED,limit=245)
    self.txt(1275,685,'⚙ Иконка' if ru else '⚙ Icon',10,YELLOW,anchor='e',limit=77)
    self.hit(1180,663,1285,701,lambda cid=cid:self.app.change_cargo_icon(cid),('btn','icon'))


def _location(self,cid):
    # Explicit game recipe map names only, never a guessed location from art.
    from game_ui import BUILTIN_RECIPES
    from core import display_recipe_location
    found=[]
    for recipe in BUILTIN_RECIPES+self.app.official+self.app.custom:
        if cid in recipe.get('inputs',{}) or cid in recipe.get('outputs',{}):
            label=display_recipe_location(recipe,self.lang)
            if label and label not in found and label not in ('Регион не указан','Region not specified','Карта не определена','Unknown map'):
                found.append(label)
    return found[0] if found else ''


def _popup(self):
    if not _is_ref(self):
        return self._v311_previous_popup()
    from game_ui import CARGO_DB,FG,YELLOW
    ru=self.lang=='ru'
    if self.popup=='ref_sort':
        labels=[('name_asc','По названию','By name'),('name_desc','Название Я–А','Name Z–A'),
                ('slots_asc','Слоты ↑','Slots ↑'),('slots_desc','Слоты ↓','Slots ↓')]
        self.round(543,256,694,416,7,'#0A202B','#446879')
        for i,(key,r,en) in enumerate(labels):
            y=263+i*37
            self.round(547,y,689,y+34,4,'#4D3F1A' if self.app.config['sort']==key else '#15333E')
            self.txt(558,y+17,r if ru else en,12,FG,limit=124)
            self.hit(548,y,690,y+34,lambda k=key:self.choose_sort(k),('popup',key))
    elif self.popup=='ref_category':
        categories=['']+sorted({self._reference_category(item) for item in CARGO_DB})
        y0=298;rowheight=min(31,max(19,390//max(len(categories),1)))
        self.round(745,y0,898,y0+rowheight*len(categories)+10,7,'#09212A','#42616C')
        for i,key in enumerate(categories):
            y=y0+5+i*rowheight
            self.round(749,y,893,y+rowheight-2,3,'#57431C' if self.cargo_category==key else '#143440')
            self.txt(759,y+rowheight/2,self._reference_category_name(key) if key else ('Все' if ru else 'All'),10,FG,limit=128)
            self.hit(749,y,894,y+rowheight,lambda k=key:self._reference_choose_category(k),('popup',key))
    elif self.popup in ('v311_maps','v311_regions'):
        field='map' if self.popup=='v311_maps' else 'region'
        x,y=(753,258) if field=='map' else (516,300)
        options=['']+_available_locations(self,field)
        if len(options)==1:
            self.round(x,y,x+163,y+76,6,'#0B232E','#45616B')
            self.txt(x+10,y+22,'Нет подтверждённых карт' if field=='map' and ru else
                     'Нет подтверждённых регионов' if ru else 'No verified location data',10,FG,limit=145)
            self.txt(x+10,y+51,'Выбери папку игры' if ru else 'Select game data',10,'#A6BAC3')
            self.hit(x,y,x+164,y+77,lambda:self.toggle(self.popup),('popup','close'))
        else:
            page=max(0,int(getattr(self,'_v311_popup_page',0)))
            max_page=max(0,(len(options)-1)//9)
            page=min(page,max_page)
            shown=options[page*9:page*9+9]
            h=len(shown)*31+12+(37 if max_page else 0)
            self.round(x,y,x+169,y+h,6,'#0B232E','#45616B')
            for i,key in enumerate(shown):
                cy=y+6+i*31
                self.round(x+4,cy,x+164,cy+29,4,'#524219' if key==getattr(self,'_v311_filter_'+field,'') else '#153440')
                self.txt(x+11,cy+15,_location_label(key,self.lang) if key else ('Все' if ru else 'All'),10,FG,limit=148)
                self.hit(x+4,cy,x+164,cy+30,lambda k=key,f=field:_choose_location(self,f,k),('popup','location'))
            if max_page:
                by=y+8+31*len(shown)
                self.txt(x+84,by+13,f'{page+1}/{max_page+1}',10,YELLOW,anchor='center')
                self.txt(x+20,by+13,'◀',13,FG)
                self.txt(x+146,by+13,'▶',13,FG)
                def navigate(step):
                    self._v311_popup_page=max(0,min(max_page,page+step));self.redraw()
                self.hit(x+1,by,x+53,by+29,lambda:navigate(-1),('popup','prev'))
                self.hit(x+116,by,x+167,by+29,lambda:navigate(1),('popup','next'))
    elif self.popup:
        return self._v311_previous_popup()


def _draw_extra(self,page):
    """Approved-look home and garage dashboards; no example save data."""
    from game_ui import FG,MUTED,YELLOW
    ru=self.lang=='ru'
    name=('ГЛАВНАЯ' if page=='home' else 'ГАРАЖ') if ru else ('HOME' if page=='home' else 'GARAGE')
    self.round(197,177,1295,709,8,'#0A202A','#375764')
    self.txt(219,205,name,27,FG,True)
    self.line(219,223,1273,223,'#36515B')
    data=_stats(self)
    local=self.app.active_profile_key=='local'
    # Profile banner: this is an actual selected save name, not a mocked user.
    self.round(220,243,1271,296,8,'#12313D','#365965')
    self.txt(237,268,('АКТИВНЫЙ ПРОФИЛЬ' if ru else 'ACTIVE PROFILE'),12,MUTED,True)
    self.txt(475,268,data['profile'],16,FG,True,limit=545)
    self.txt(1250,268,('НЕ ПОДКЛЮЧЁН' if local else 'ПОДКЛЮЧЁН') if ru else
             ('NOT CONNECTED' if local else 'CONNECTED'),11,'#E9BA56' if local else '#90D8BA',True,anchor='e')
    if page=='home':
        values=(('money','БАЛАНС','BALANCE','₵'),('exp','ОПЫТ','EXPERIENCE','★'),
                ('objectives','ВЫПОЛНЕНО ЗАДАНИЙ','COMPLETED TASKS','✓'),
                ('trucks','МАШИН В ХРАНИЛИЩЕ','STORED TRUCKS','▣'))
        for i,(key,r,en,symbol) in enumerate(values):
            col=i%2;row=i//2;x=221+col*524;y=318+row*114
            self.round(x,y,x+505,y+98,9,'#132D38','#385763')
            self.round(x+11,y+13,x+52,y+52,7,'#263F46','#48636B')
            self.txt(x+31,y+32,symbol,24,YELLOW,True,anchor='center')
            self.txt(x+65,y+28,r if ru else en,12,MUTED,True,limit=420)
            self.txt(x+65,y+66,_number(data[key]),20,FG,True)
        self.txt(239,569,'БЫСТРЫЕ ДЕЙСТВИЯ' if ru else 'QUICK ACTIONS',15,YELLOW,True)
        actions=[('ГРУЗЫ','CARGO','cargo'),('КРАФТ','CRAFT','recipes'),('КАЛЬКУЛЯТОР','CALCULATOR','calculator')]
        for i,(r,en,target) in enumerate(actions):
            x=221+i*349
            self.round(x,605,x+329,652,7,'#183947','#456571')
            self.txt(x+164,629,r if ru else en,14,FG,True,anchor='center')
            self.hit(x,605,x+329,653,lambda target=target:_action(self,target),('btn','go_'+target))
        self.txt(224,682,'Обновление считывает только выбранное сохранение.' if ru else
                 'Refresh only reads the explicitly selected save.',11,MUTED)
    else:
        fleet=[('trucks','МАШИН В ХРАНИЛИЩЕ','STORED VEHICLES'),('garages','ОТКРЫТО ГАРАЖЕЙ','OPEN GARAGES')]
        for i,(key,r,en) in enumerate(fleet):
            x=221+i*524
            self.round(x,316,x+505,420,8,'#15303D','#3A5D68')
            self.txt(x+21,343,r if ru else en,14,MUTED,True)
            self.txt(x+21,390,_number(data[key]),27,YELLOW,True)
        self.round(221,438,1270,637,9,'#102A35','#345664')
        self.txt(243,467,'ТЕХНИКА ПО МОДЕЛЯМ' if ru else 'VEHICLES BY MODEL',17,FG,True)
        models={}
        if not local:
            try:
                snapshot=(self.app.profiles.read(self.app.active_profile_key).get('game_snapshot') or {})
                models=(snapshot.get('retained_trucks') or {}).get('models') or {}
                if not isinstance(models,dict):models={}
            except (OSError,ValueError,TypeError,KeyError,AttributeError):models={}
        if models:
            for i,(model,count) in enumerate(sorted(models.items())[:4]):
                y=504+i*30
                self.txt(254,y,model,12,FG,limit=840)
                self.txt(1171,y,str(count),13,YELLOW,True,anchor='e')
        else:
            self.txt(253,531,'Нет подтверждённых данных о машинах.' if ru else
                     'No verified vehicle data.',14,MUTED)
        self.round(873,651,1267,696,7,'#183B48','#5A7985')
        self.txt(1070,674,'ПОДКЛЮЧИТЬ СОХРАНЕНИЕ' if ru else 'CONNECT GAME SAVE',12,FG,True,anchor='center')
        self.hit(873,651,1267,697,self.app.game_connection_dialog,('btn','connect_save'))


def _redraw(self):
    self._v311_previous_redraw()
    if not _is_ref(self):return
    # Original GameScreen assumes a wide one-column catalogue: relocate its
    # *real tkinter Entry*, never paint a dead text box on top of it.
    if self.page=='cargo' and getattr(self,'_approved_extra',None) is None:
        x,y=self.p(251,226)
        self.search_entry.place(x=int(x),y=int(y),width=max(25,int(194*self.sx)),height=max(18,int(28*self.sy)))
        self.search_entry.configure(bg='#1A3745',fg='#F2F5F2',insertbackground='#FFC21B')
        if not self.search.get() and self.root.focus_get()!=self.search_entry:
            xx,yy=self.p(258,241)
            self.search_placeholder.place(x=int(xx),y=int(yy-12*self.sy),
                width=int(178*self.sx),height=max(20,int(25*self.sy)))
            self.search_placeholder.configure(bg='#1A3745',fg='#8799A3',anchor='w')
            self.search_placeholder.lift()
    elif getattr(self,'_approved_extra',None) is not None:
        self.search_entry.place_forget();self.search_placeholder.place_forget()


def install_approved_ui():
    """Install presentation hooks on the real class, preserving all other APIs."""
    global _INSTALLED
    if _INSTALLED:return
    module=sys.modules.get('game_ui')
    cls=getattr(module,'GameScreen',None) if module else None
    if cls is None:return
    cls._v311_previous_nav=cls.draw_nav
    cls._v311_previous_toolbar=cls.draw_toolbar
    cls._v311_previous_reference_cargo=cls._draw_reference_cargo
    cls._v311_previous_popup=cls._draw_reference_popup
    cls._v311_previous_redraw=cls.redraw
    cls.draw_nav=_draw_nav
    cls.draw_toolbar=_draw_toolbar
    cls._reference_visible_cargo=_visible
    cls._draw_reference_cargo=_draw_cargo
    cls._draw_reference_popup=_popup
    cls.redraw=_redraw
    cls._approved_ui_v311=True
    from ui_repair_v312 import install_workspace_fix, install_editor_preview
    install_workspace_fix(cls)
    install_editor_preview()
    from expedition_upgrade_v316 import install_expedition_upgrade
    install_expedition_upgrade(cls)
    from hotkey_upgrade_v316 import install_hotkey_improvement
    install_hotkey_improvement()
    _INSTALLED=True
