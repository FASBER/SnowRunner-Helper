"""SnowRunner Helper v18 — profile drafts and progress tools."""
import json
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import uuid
import webbrowser
import sys
import zipfile
from pathlib import Path
from core import ROOT
from recipe_editor_ui import RecipeEditor
from official_import import import_recipes, SOURCE_DOC, describe_import_failure
from stg_inspector import inspect_path
from game_bridge import (discover_game_archives, discover_save_slots, inspect_archive,
                         inspect_save, status_summary, profile_key)
from profile_sync import ProfileStore, SaveMonitor, snapshot_save
from font_manager import FontManager
from appearance import normalize, DEFAULT, AppearanceEditor, _copy_asset
from icon_manager import (cargo_icon_path, has_custom_icon,
                          install_cargo_icon, reset_cargo_icon)
from update_config import CURRENT_VERSION
from update_ui import UpdaterUI

from core import (USER_DIR, CARGO, CARGO_DB, BUILTIN_RECIPES, REGIONS, SETTINGS_FILE,
                  CUSTOM_FILE, IMPORTED_FILE, load_game_recipes, SORT_MODES, calculate_load, cargo_slots,
                  display_cargo, display_region, display_recipe_location, display_recipe_notes, filter_recipes, load_custom,
                  load_json, save_json, sort_cargo, text_value, validate_recipe)

# The same dashboard layout and functionality work in all three themes.
THEMES = {
    'game': {
        'bg':'#10171B', 'nav':'#11191D', 'panel':'#1B242A', 'raised':'#293238',
        'input':'#20282D', 'fg':'#F1F2F0', 'muted':'#BBC2C5', 'accent':'#FFC21B',
        'accent_fg':'#14191C', 'stroke':'#39444A', 'selection':'#54451A',
    },
    'dark': {
        'bg':'#10161C', 'nav':'#131B22', 'panel':'#1D262D', 'raised':'#29343D',
        'input':'#161F26', 'fg':'#F2F0E9', 'muted':'#A4ADB3', 'accent':'#F0B43F',
        'accent_fg':'#1C1B19', 'stroke':'#38434B', 'selection':'#50472A',
    },
    'light': {
        'bg':'#ECEAE3', 'nav':'#D9D5CB', 'panel':'#F9F7F1', 'raised':'#E6E1D6',
        'input':'#FFFFFF', 'fg':'#2A2D30', 'muted':'#626B70', 'accent':'#C38322',
        'accent_fg':'#1A1813', 'stroke':'#CCC7BE', 'selection':'#F1DDAF',
    },
    'forest': {
        'bg':'#121C18', 'nav':'#16241D', 'panel':'#223328', 'raised':'#304639',
        'input':'#182821', 'fg':'#E8EBDB', 'muted':'#A0B2A2', 'accent':'#C4B56C',
        'accent_fg':'#1B2117', 'stroke':'#465B4B', 'selection':'#50583B',
    },
}
ASSETS = ROOT / 'assets'
OVERRIDE_ASSETS = (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent) / 'assets'

GROUP_COLORS = {'construction':'#E7A03A','wood':'#B98953','metal':'#B2BFC6',
                'industrial':'#7BA7CD','supplies':'#70B6A4','container':'#9DA6D9',
                'logs':'#A88B57','agriculture':'#A6C879','mission':'#D58F96',
                'special':'#8DA0AD'}
GROUP_SYMBOLS = {'construction':'▤','wood':'▥','metal':'▦','industrial':'⚙',
                 'supplies':'+','container':'□','logs':'≋','agriculture':'✿',
                 'mission':'◆','special':'◈'}

TR = {
 'ru': {
  'cargo':'Грузы', 'recipes':'Крафт', 'calculator':'Калькулятор', 'manual':'Справочник', 'settings':'Настройки',
  'subtitle':'Каталог материалов, крафт и логистика',
  'cargo_count':'ВИДОВ ГРУЗОВ', 'recipe_count':'РЕЦЕПТОВ В БАЗЕ', 'region_count':'РЕГИОНОВ',
  'offline':'ОФЛАЙН-ПОМОЩНИК', 'navigation':'РАЗДЕЛЫ', 'local':'Все данные сохраняются на этом ПК',
  'catalog':'Каталог грузов', 'catalog_desc':'Поиск и сортировка материалов по названию и занимаемому месту',
  'recipe_header':'Рецепты крафта', 'recipe_desc':'Только подтверждённые из игровых файлов и личные записи',
  'ui_title':'Оформление', 'settings_desc':'Выбор цветовой темы и языка интерфейса',
  'search':'Поиск по названию или ID...', 'sort_label':'Сортировка', 'filter_count':'Найдено грузов',
  'name_asc':'По алфавиту: А → Я', 'name_desc':'По алфавиту: Я → А',
  'slots_asc':'По слотам: сначала меньше', 'slots_desc':'По слотам: сначала больше',
  'cargo_name':'Название', 'slots':'Слоты', 'id':'ID', 'qty':'Кол-во',
  'cargo_detail':'Информация о грузе', 'choose_cargo':'Выберите груз в таблице',
  'no_standard':'Не имеет стандартного размера в слотах', 'slot_unit':'слот(ов)',
  'load':'Калькулятор загрузки', 'add_load':'+ Добавить груз', 'delete':'Убрать выбранное',
  'total':'Всего занято слотов', 'empty_load':'Список загрузки пуст',
  'must_select':'Выберите груз из таблицы.', 'cannot_load':'Для этого груза нет стандартного размера в слотах.',
  'note_slots':'Брёвна перевозятся специальными платформами. Не все грузы измеряются обычными слотами.',
  'all_regions':'Все регионы', 'recipes_count':'записей', 'filter_no':'Нет подтверждённых рецептов. Создай свой или импортируй из файлов игры.',
  'builtin':'Встроенный', 'game_imported':'Из игровых файлов', 'import_game_title':'Импорт крафтов из файлов SnowRunner', 'import_game':'Импорт из игры', 'import_none':'Не найдено распознанных рецептов craftSettings. Проверь выбранный файл. Неизвестные ID:', 'import_done':'Загружено: {n}. Нераспознанных ID: {skip}.', 'scan_game':'Проверить PAK', 'scan_title':'Проверка игровых файлов', 'custom':'Мой рецепт', 'components':'ТРЕБУЕТСЯ', 'result':'ПОЛУЧИТСЯ',
  'generator':'Генератор', 'no_inputs':'Нет входящего груза — нужен работающий генератор',
  'choose_recipe':'Выберите рецепт слева', 'source':'Открыть источник',
  'add_recipe':'+ Новый рецепт', 'edit_recipe':'Изменить', 'delete_recipe':'Удалить',
  'copy_recipe':'Копировать', 'recipe_title':'Рецепт', 'map':'Карта / место',
  'region':'Регион', 'notes':'Примечание', 'rename':'Название рецепта',
  'material_ids':'Примеры ID грузов:', 'inputs':'Ингредиенты',
  'outputs':'Результат', 'save':'Сохранить', 'cancel':'Отмена',
  'invalid':'Ошибка в рецепте', 'confirm':'Удалить пользовательский рецепт?',
  'help_edit':'Выбери груз из списка и укажи количество.',
  'user_note':'Примечание', 'no_inputs_suffix':'Расход топлива генератора не включён в расчёт',
  'not_complete':'Официальные рецепты не включены без подтверждения игровыми файлами. Импортируй свои файлы SnowRunner или создай личный рецепт.',
  'theme':'Цветовая тема', 'theme_dark':'Тёмная', 'theme_light':'Светлая',
  'theme_forest':'Лесная', 'lang':'Язык интерфейса', 'about_title':'О приложении',
  'about':'Приложение работает без интернета. Ваши рецепты и настройки сохраняются локально; встроенные рецепты нельзя редактировать, но можно копировать.',
  'export_info':'Рецепты от фанатских источников исключены. Импорт из JSON игровых производственных зон (craftSettings) или собственные рецепты. Неофициальное приложение.',
  'icon_legend':'В комплекте иллюстрации всех грузов и рецептов. Для каждого груза можно выбрать свою картинку. Это не официальные изображения игры.',
  'change_icon':'Заменить иконку', 'reset_icon':'Вернуть стандартную', 'icon_error':'Ошибка изображения',
  'icon_reset_done':'Восстановлена стандартная иконка груза.',
  'status':'Неподтверждённые рецепты исключены: импортируй реальные игровые данные или добавь личный рецепт.',
  'quick_tools':'БЫСТРЫЙ ДОСТУП', 'manage_recipes':'Открыть рецепты', 'animation':'Плавные анимации', 'craft_uses':'Используется в крафте', 'not_used':'В текущей базе рецептов не найдено', 'image_folder':'Значки грузов: выбери груз и нажми «Заменить иконку». Поддерживаются PNG, JPG, WebP. Замены хранятся в папке пользователя и не теряются после обновления.',
 },
 'en': {
  'cargo':'Cargo', 'recipes':'Craft', 'calculator':'Calculator', 'manual':'Guide', 'settings':'Settings',
  'subtitle':'Materials, crafting and logistics in one place',
  'cargo_count':'CARGO TYPES', 'recipe_count':'BUILT-IN RECIPES', 'region_count':'REGIONS',
  'offline':'OFFLINE COMPANION', 'navigation':'NAVIGATION', 'local':'All data stays on this PC',
  'catalog':'Cargo catalog', 'catalog_desc':'Search and sort materials by name or cargo slot size',
  'recipe_header':'Crafting recipes', 'recipe_desc':'Only game-file recipes and your own entries',
  'ui_title':'Appearance', 'settings_desc':'Choose your color theme and interface language',
  'search':'Search by name or ID...', 'sort_label':'Sort by', 'filter_count':'Matching cargo',
  'name_asc':'Alphabetical: A → Z', 'name_desc':'Alphabetical: Z → A',
  'slots_asc':'Cargo slots: smallest first', 'slots_desc':'Cargo slots: largest first',
  'cargo_name':'Name', 'slots':'Slots', 'id':'ID', 'qty':'Qty',
  'cargo_detail':'Cargo details', 'choose_cargo':'Select cargo in the table',
  'no_standard':'No standard cargo-slot equivalent', 'slot_unit':'slot(s)',
  'load':'Load calculator', 'add_load':'+ Add cargo', 'delete':'Remove selected',
  'total':'Total cargo slots', 'empty_load':'Your load is empty',
  'must_select':'Please select a cargo item.', 'cannot_load':'This cargo has no standard slot size.',
  'note_slots':'Logs require special trailers. Not all cargo types have a normal slot size.',
  'all_regions':'All regions', 'recipes_count':'entries', 'filter_no':'No verified recipes. Create yours or import from game files.',
  'builtin':'Built-in', 'game_imported':'From game files', 'import_game_title':'Import SnowRunner crafting data', 'import_game':'Import from game', 'import_none':'No recognized craftSettings recipes found. Check your file. Unknown IDs:', 'import_done':'Imported: {n}. Unknown cargo IDs: {skip}.', 'scan_game':'Inspect PAKs', 'scan_title':'Inspect game archives', 'custom':'My recipe', 'components':'INPUTS', 'result':'OUTPUTS',
  'generator':'Generator', 'no_inputs':'No incoming cargo — a working generator is required',
  'choose_recipe':'Choose a recipe on the left', 'source':'Open source',
  'add_recipe':'+ New recipe', 'edit_recipe':'Edit', 'delete_recipe':'Delete',
  'copy_recipe':'Copy recipe', 'recipe_title':'Recipe', 'map':'Map / facility',
  'region':'Region', 'notes':'Notes', 'rename':'Recipe name',
  'material_ids':'Example cargo IDs:', 'inputs':'Ingredients',
  'outputs':'Result', 'save':'Save', 'cancel':'Cancel',
  'invalid':'Invalid recipe', 'confirm':'Delete this custom recipe?',
  'help_edit':'Choose cargo by name and set its amount.',
  'user_note':'Notes', 'no_inputs_suffix':'Generator fuel is not included in cargo totals',
  'not_complete':'No recipes are presented as official without checking game data. Import your own SnowRunner files or create a personal recipe.',
  'theme':'Color theme', 'theme_dark':'Dark', 'theme_light':'Light',
  'theme_forest':'Forest', 'lang':'Interface language', 'about_title':'About',
  'about':'The app works offline. Your recipes and preferences are stored locally. Built-in recipes are read-only, but can be copied.',
  'export_info':'Community recipes excluded. Import craftSettings from game-zone JSON or add your own recipes. Unofficial app.',
  'icon_legend':'Illustrations cover every cargo and recipe. You can pick a custom image for each cargo. These are not official game images.',
  'change_icon':'Change icon', 'reset_icon':'Restore default', 'icon_error':'Image error',
  'icon_reset_done':'Original cargo icon restored.',
  'status':'Unverified recipes removed: import real game-zone data or create your own recipe.',
  'quick_tools':'QUICK ACCESS', 'manage_recipes':'Open recipes', 'animation':'Smooth animations', 'craft_uses':'Used in crafting', 'not_used':'Not found in the current recipe database', 'image_folder':'Select a cargo and click Change icon. PNG, JPG and WebP are supported. Your pictures persist across app updates.',
 }
}


class Application:
    def __init__(self, root):
        self.root = root
        self.config = load_json(SETTINGS_FILE, {'theme': 'game', 'lang': 'ru', 'sort': 'name_asc'})
        if not isinstance(self.config, dict):
            self.config = {}
        if self.config.get('theme') not in THEMES: self.config['theme'] = 'game'
        # One-time opt-in to the newly approved screenshot theme. Existing user
        # language, sorting and custom recipes remain unchanged.
        if not self.config.get('v05_game_theme_offered'):
            self.config['theme'] = 'game'
            self.config['v05_game_theme_offered'] = True
            save_json(SETTINGS_FILE, self.config)
        if self.config.get('lang') not in TR: self.config['lang'] = 'ru'
        if self.config.get('sort') not in SORT_MODES: self.config['sort'] = 'name_asc'
        self.config['ui_scale'] = max(75,min(140,int(self.config.get('ui_scale',100))))
        self.config['text_size'] = max(75,min(150,int(self.config.get('text_size',100))))
        self.config['theme']='game'  # The SnowRunner canvas supports classic and expedition UI skins
        if self.config.get('ui_design') not in ('classic','expedition'):
            self.config['ui_design']='expedition'
        self.config['appearance']=normalize(self.config.get('appearance'))
        self.config['ui_scale']=self.config['appearance']['ui_scale']
        self.config['text_size']=self.config['appearance']['text_size']
        self.config['animations']=self.config['appearance']['animations']
        for script in ('cyrillic','latin'):
            if self.config.get('font_'+script) and not self.config['appearance'].get('font_'+script):
                self.config['appearance']['font_'+script]=self.config['font_'+script]
        self.font_manager=FontManager(self.config)
        # Windows taskbar/window icon from the approved cargo visual language.
        try:
            self._window_icon=tk.PhotoImage(file=str(ROOT/'assets/ui/app_icon.png'))
            root.iconphoto(True,self._window_icon)
        except (tk.TclError,OSError):
            self._window_icon=None
        self._tk_base_scaling=float(root.tk.call('tk','scaling'))
        self.page = 'cargo'
        self.last_selected_cargo = 'metal_beams'
        self.game = None
        self._photos = {}
        self._animation_tokens = {}
        if 'animations' not in self.config: self.config['animations'] = True
        self.custom = load_custom()
        self.official = load_game_recipes()
        self.profiles = ProfileStore(USER_DIR / 'profiles')
        self.save_monitor = SaveMonitor()
        self.active_profile_key = self.config.get('selected_game_profile', 'local')
        self._profile_save_error = None
        try:
            self.load = self.profiles.manifest(self.active_profile_key)
        except (OSError, ValueError) as exc:
            # Never clobber an unreadable old profile with a new empty one.
            self._profile_save_error = str(exc)
            self.load = []
        self._draft_saved_load = list(self.load)
        self._last_profile_sync_issue = ''
        self.selected_recipe = None
        root.geometry('1320x850')
        root.minsize(1060, 680)
        self._window_initialized=False
        self.render()
        from craft_overlay import CraftOverlay
        self.overlay = CraftOverlay(self)
        self.root.protocol('WM_DELETE_WINDOW', self.close_app)
        self.updater = UpdaterUI(self)
        self.root.after(3500, self.updater.start_auto)
        self.root.after(12000, self._background_profile_cycle)

    def t(self, key):
        return TR[self.config['lang']].get(key, key)

    def c(self, key):
        return THEMES[self.config['theme']][key]

    def f(self, parent, color='panel', **kw):
        return tk.Frame(parent, bg=self.c(color), **kw)

    def ui_font_family(self,text=''):
        return self.font_manager.family(text,self.config['lang'])

    def sized(self,size):
        return max(7,round(size*self.config.get('text_size',100)/100))

    def lbl(self, parent, text='', fg='fg', size=11, bold=False, bg='panel', **kw):
        return tk.Label(parent, text=text, bg=self.c(bg), fg=self.c(fg),
                        font=(self.ui_font_family(text), self.sized(size), 'bold' if bold else 'normal'), **kw)

    def btn(self, parent, label, cmd, primary=False, **kw):
        color = 'accent' if primary else 'raised'
        w = tk.Button(parent, text=label, command=cmd,
                      bg=self.c(color), fg=self.c('accent_fg' if primary else 'fg'),
                      activebackground=self.c('accent'),
                      activeforeground=self.c('accent_fg'), padx=15, pady=10,
                      borderwidth=0, relief='flat', cursor='hand2',
                      font=(self.ui_font_family(label), self.sized(10), 'bold' if primary else 'normal'), **kw)
        normal = self.c(color)
        hover = self.mix(normal, self.c('accent'), .18 if primary else .32)
        w.bind('<Enter>', lambda e: self.animate_bg(w,hover))
        w.bind('<Leave>', lambda e: self.animate_bg(w,normal))
        return w

    def ent(self, parent, variable=None):
        return tk.Entry(parent, textvariable=variable, bg=self.c('input'),
                        fg=self.c('fg'), insertbackground=self.c('fg'),
                        font=(self.ui_font_family(), self.sized(11)), relief='flat', highlightthickness=1,
                        highlightbackground=self.c('stroke'), highlightcolor=self.c('accent'))

    def panel(self, parent, color='panel'):
        return tk.Frame(parent, bg=self.c(color), highlightthickness=1,
                        highlightbackground=self.c('stroke'), highlightcolor=self.c('stroke'))

    def title(self, parent, title, detail=''):
        r = self.f(parent)
        r.pack(fill='x', padx=19, pady=(17, 12))
        self.lbl(r, title, size=12, bold=True).pack(side='left')
        if detail:
            self.lbl(r, detail, fg='muted', size=9).pack(side='right')
        return r

    def photo(self, cid, size=64, recipe=False):
        """Recipe art stays bundled; cargo prefers persistent user choices."""
        key = ('recipe' if recipe else 'cargo', cid, 128 if size > 64 else (64 if size > 32 else 32))
        if key in self._photos:
            return self._photos[key]
        if recipe:
            filename = OVERRIDE_ASSETS / 'recipes' / f'{cid}.png'
            if not filename.exists():filename = ASSETS / 'recipes' / f'{cid}.png'
            if not filename.exists() and cid in CARGO: filename = cargo_icon_path(cid)
        else:
            filename = cargo_icon_path(cid, legacy_folder=OVERRIDE_ASSETS / 'cargo')
        if not filename or not filename.exists():
            return None
        try:
            from PIL import Image, ImageTk
            with Image.open(filename) as img:
                img = img.convert('RGBA')
                img.thumbnail((max(24,size), max(24,size)), Image.Resampling.LANCZOS)
                im = ImageTk.PhotoImage(img, master=self.root)
            self._photos[key] = im
            return im
        except (OSError, tk.TclError, ValueError):
            return None

    def change_cargo_icon(self, cid):
        """Open file picker and persist this cargo's replacement image."""
        if cid not in CARGO:
            return False
        path = filedialog.askopenfilename(parent=self.root,
                    title=(self.t('change_icon') + ' — ' + display_cargo(cid, self.config['lang'])),
                    filetypes=[('Images / Изображения','*.png *.jpg *.jpeg *.webp'),
                               ('PNG','*.png'),('JPEG','*.jpg *.jpeg'),('WebP','*.webp')])
        if not path:
            return False
        try:
            install_cargo_icon(cid, path)
        except (OSError, ValueError) as err:
            messagebox.showerror(self.t('icon_error'), str(err), parent=self.root)
            return False
        self.refresh_cargo_icons()
        return True

    def restore_cargo_icon(self, cid):
        if cid not in CARGO or not has_custom_icon(cid):
            return False
        try:
            reset_cargo_icon(cid)
        except OSError as err:
            messagebox.showerror(self.t('icon_error'), str(err), parent=self.root)
            return False
        self.refresh_cargo_icons()
        return True

    def refresh_cargo_icons(self):
        self._photos.clear()
        if self.game is not None:
            self.game.image_cache.clear()
            self.game.redraw()
        else:
            self.render()

    def icon(self, parent, cid, size=45, color='panel', recipe=False):
        im = self.photo(cid, size=size, recipe=recipe)
        if im is not None:
            return tk.Label(parent, image=im, bg=self.c(color), borderwidth=0)
        cv = tk.Canvas(parent, width=size, height=size,
                       bg=self.c(color), highlightthickness=0, borderwidth=0)
        cv.create_rectangle(2, 2, size-2, size-2, fill='#BD9552', outline='')
        cv.create_text(size/2, size/2, text='▣', fill='#182A35', font=(self.ui_font_family(), int(size*.44), 'bold'))
        return cv

    @staticmethod
    def mix(a, b, f):
        """Eased interpolation of two #RRGGBB colors."""
        f = max(0.0, min(1.0, float(f)))
        channels = [round(int(a[i:i+2], 16) * (1-f) + int(b[i:i+2], 16) * f) for i in (1,3,5)]
        return '#' + ''.join(f'{v:02X}' for v in channels)

    def animate_bg(self, widget, target, duration=180, children=False):
        """Non-blocking hover highlight; safely cancels an older animation."""
        if not widget.winfo_exists(): return
        if not self.config.get('animations', True):
            widgets = [widget] + (widget.winfo_children() if children else [])
            for item in widgets:
                try: item.configure(bg=target)
                except tk.TclError: pass
            return
        token = object()
        self._animation_tokens[id(widget)] = token
        try: initial = widget.cget('bg')
        except tk.TclError: return
        steps = max(2, round(duration / 18))
        def tick(step):
            if not widget.winfo_exists() or self._animation_tokens.get(id(widget)) is not token:return
            x = step / steps
            eased = 1 - (1 - x)**3
            color = self.mix(initial, target, eased)
            for item in [widget] + (widget.winfo_children() if children else []):
                try: item.configure(bg=color)
                except tk.TclError: pass
            if step < steps: self.root.after(18, lambda: tick(step + 1))
        tick(0)

    def intro_line(self, parent):
        """Static accent line in legacy themes; old reveal animation removed."""
        line=tk.Frame(parent, height=3, bg=self.c('accent'))
        line.pack(fill='x', pady=(0,9))

    def configure_style(self):
        st = ttk.Style(self.root)
        st.theme_use('clam')
        st.configure('Cargo.Treeview', background=self.c('panel'),
                     fieldbackground=self.c('panel'), foreground=self.c('fg'),
                     borderwidth=0, rowheight=69, font=(self.ui_font_family(), self.sized(10)))
        st.configure('Cargo.Treeview.Heading', background=self.c('raised'),
                     foreground=self.c('fg'), relief='flat', borderwidth=0,
                     padding=(9, 11), font=(self.ui_font_family(), self.sized(10), 'bold'))
        st.map('Cargo.Treeview', background=[('selected', self.c('selection'))],
               foreground=[('selected', self.c('fg'))])
        st.configure('Dashboard.TCombobox', padding=(9, 7),
                     fieldbackground=self.c('input'), background=self.c('raised'),
                     foreground=self.c('fg'), arrowcolor=self.c('accent'))
        st.map('Dashboard.TCombobox', fieldbackground=[('readonly', self.c('input'))],
               foreground=[('readonly', self.c('fg'))],
               selectbackground=[('readonly', self.c('input'))],
               selectforeground=[('readonly', self.c('fg'))])
        self.root.option_add('*TCombobox*Listbox.background', self.c('panel'))
        self.root.option_add('*TCombobox*Listbox.foreground', self.c('fg'))
        self.root.option_add('*TCombobox*Listbox.selectBackground', self.c('accent'))

    def render(self):
        self.root.tk.call('tk','scaling',self._tk_base_scaling*(self.config.get('ui_scale',100)/100 if self.config['theme']!='game' else 1))
        # The game screenshot skin is implemented as a real interactive canvas,
        # not a static screenshot. Other color themes retain the original UI.
        if self.config['theme'] == 'game':
            for child in self.root.winfo_children():
                if not isinstance(child,tk.Toplevel): child.destroy()
            from game_ui import GameScreen
            self.game = GameScreen(self)
            return
        self.game = None
        self.root.unbind('<MouseWheel>')
        self.root.unbind('<Button-4>')
        self.root.unbind('<Button-5>')
        for child in self.root.winfo_children(): child.destroy()
        self.configure_style()
        self.root.configure(bg=self.c('bg'))
        self.root.title('SnowRunner Helper  |  v' + CURRENT_VERSION)
        shell = self.f(self.root, 'bg')
        shell.pack(fill='both', expand=True, padx=12, pady=12)
        sidebar = self.panel(shell, 'nav')
        sidebar.pack(side='left', fill='y', padx=(0,12))
        sidebar.configure(width=221)
        sidebar.pack_propagate(False)
        self.sidebar = sidebar
        brand = self.f(sidebar, 'nav')
        brand.pack(fill='x', padx=17, pady=(27,26))
        self.lbl(brand, 'SNOWRUNNER', bg='nav', fg='fg',bold=True,size=15).pack(anchor='w')
        marker = tk.Frame(brand,bg=self.c('accent'),height=4)
        marker.pack(fill='x',pady=(7,7))
        self.lbl(brand, 'HELPER',bg='nav',fg='accent',bold=True,size=11).pack(anchor='w')
        self.nav_container = self.f(sidebar,'nav')
        self.nav_container.pack(fill='x',padx=10)
        self.draw_nav()
        footer = self.f(sidebar, 'nav')
        footer.pack(side='bottom', fill='x', padx=17,pady=20)
        self.lbl(footer,'●  '+self.t('offline'),bg='nav',fg='accent',bold=True,size=9).pack(anchor='w')
        self.lbl(footer,'v'+CURRENT_VERSION+'  /  OFFROAD EDITION',bg='nav',fg='muted',size=8).pack(anchor='w',pady=(8,0))
        main = self.f(shell,'bg')
        main.pack(side='left',fill='both',expand=True)
        header = tk.Canvas(main,height=126,bg=self.c('bg'),highlightthickness=0)
        header.pack(fill='x',pady=(0,14))
        img = self.photo_header()
        if img is not None:
            header.create_image(0,0,image=img,anchor='nw')
        header.create_rectangle(0,0,425,126,fill='#152029',outline='')
        header.create_text(23,38,anchor='w',text='SNOWRUNNER',fill='#F5F0E7',
                           font=(self.ui_font_family(), self.sized(24),'bold'))
        header.create_rectangle(23,60,267,65,fill='#D99C30',outline='')
        header.create_text(24,90,anchor='w',text='HELPER',fill='#F2BB50',
                           font=(self.ui_font_family(), self.sized(15),'bold'))
        self.btn(header,'RU / EN', lambda:self.show('settings')).place(relx=.84,y=15,anchor='ne')
        self.btn(header,'⚙', lambda:self.show('settings')).place(relx=.97,y=15,anchor='ne')
        self.page_header=self.f(main,'bg')
        self.page_header.pack(fill='x',pady=(0,8))
        self.body=self.f(main,'bg')
        self.body.pack(fill='both',expand=True)
        self.show(self.page)

    def photo_header(self):
        path=ASSETS/'ui'/'header.png'
        if not path.exists(): return None
        if 'header' not in self._photos:
            try:self._photos['header']=tk.PhotoImage(file=str(path))
            except tk.TclError:return None
        return self._photos['header']

    def draw_nav(self):
        for w in self.nav_container.winfo_children(): w.destroy()
        for page,glyph in [('cargo','▣'),('recipes','⚒'),('calculator','▦'),('manual','▤'),('settings','⚙')]:
            selected = (page == self.page)
            bg='selection' if selected else 'nav'
            item=self.f(self.nav_container,bg,cursor='hand2')
            item.pack(fill='x',pady=4)
            label_a=self.lbl(item,glyph,bg=bg,fg='accent' if selected else 'muted',size=16)
            label_a.pack(side='left',padx=(14,13),pady=13)
            label_b=self.lbl(item,self.t(page),bg=bg,fg='fg' if selected else 'muted',size=11,bold=selected)
            label_b.pack(side='left')
            for widget in (item,label_a,label_b):
                widget.bind('<Button-1>',lambda event,p=page:self.show(p))
                if not selected:
                    widget.bind('<Enter>',lambda event,w=item:self.animate_bg(w,self.c('raised'),children=True))
                    widget.bind('<Leave>',lambda event,w=item:self.animate_bg(w,self.c('nav'),children=True))

    def show(self,page):
        if self.game is not None:
            self.game.show(page)
            return
        self.page=page
        self.draw_nav()
        for w in self.page_header.winfo_children():w.destroy()
        page_titles={
            'cargo':('cargo','catalog_desc'),
            'recipes':('recipes','recipe_desc'),
            'calculator':('calculator','load'),
            'manual':('manual','icon_legend'),
            'settings':('settings','settings_desc'),
        }
        name, desc=page_titles[page]
        heading=self.f(self.page_header,'bg')
        heading.pack(side='left')
        self.lbl(heading,self.t(name),bg='bg',size=22,bold=True).pack(anchor='w')
        self.lbl(heading,self.t(desc),bg='bg',fg='muted',size=10).pack(anchor='w',pady=(3,0))
        for w in self.body.winfo_children():w.destroy()
        self.intro_line(self.body)
        getattr(self,'page_'+page)()

    def page_cargo(self):
        left = self.panel(self.body)
        left.pack(side='left', fill='both', expand=True, padx=(0, 13))
        right_outer = self.panel(self.body)
        right_outer.pack(side='right', fill='both')
        right_outer.configure(width=334)
        right_outer.pack_propagate(False)
        # The whole load planner remains reachable on compact laptop screens.
        right_canvas = tk.Canvas(right_outer, bg=self.c('panel'),
                                 borderwidth=0, highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_outer, orient='vertical', command=right_canvas.yview)
        right = self.f(right_canvas)
        right.bind('<Configure>', lambda e: right_canvas.configure(scrollregion=right_canvas.bbox('all')))
        right_canvas.create_window((0, 0), window=right, anchor='nw', tags='inner')
        right_canvas.bind('<Configure>', lambda e: right_canvas.itemconfigure('inner', width=e.width))
        right_canvas.configure(yscrollcommand=right_scroll.set)
        right_canvas.pack(side='left', fill='both', expand=True)
        right_scroll.pack(side='right', fill='y')

        top = self.f(left)
        top.pack(fill='x', padx=18, pady=(18, 11))
        self.lbl(top, self.t('search'), fg='muted', size=9).pack(anchor='w', pady=(0, 5))
        q = tk.StringVar()
        search = self.ent(top, q)
        search.pack(fill='x', ipady=8)
        search.focus_set()
        sort_row = self.f(left)
        sort_row.pack(fill='x', padx=18, pady=(0, 11))
        self.lbl(sort_row, self.t('sort_label'), size=10, bold=True).pack(side='left', padx=(0, 12))
        modes = list(SORT_MODES)
        sort_names = [self.t(mode) for mode in modes]
        selected_sort = tk.StringVar(value=self.t(self.config['sort']))
        sort_combo = ttk.Combobox(sort_row, state='readonly', values=sort_names,
                                  textvariable=selected_sort, style='Dashboard.TCombobox')
        sort_combo.pack(side='left', fill='x', expand=True)
        count_label = self.lbl(left, '', fg='muted', size=9)
        count_label.pack(anchor='w', padx=19, pady=(0, 8))

        table_holder = self.f(left)
        table_holder.pack(fill='both', expand=True, padx=17, pady=(0, 15))
        cols = ('name', 'slots')
        table = ttk.Treeview(table_holder, show='tree headings', columns=cols,
                             style='Cargo.Treeview', selectmode='browse')
        table.heading('name', text=self.t('cargo_name'), command=lambda: change_sort(
            'name_desc' if self.config['sort'] == 'name_asc' else 'name_asc'))
        table.heading('slots', text=self.t('slots'), command=lambda: change_sort(
            'slots_desc' if self.config['sort'] == 'slots_asc' else 'slots_asc'))
        table.heading('#0', text='')
        table.column('#0', minwidth=73, width=73, stretch=False, anchor='center')
        table.column('name', minwidth=190, width=270, stretch=True)
        table.column('slots', minwidth=60, width=67, stretch=False, anchor='center')
        scrollbar = ttk.Scrollbar(table_holder, orient='vertical', command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        table.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        table.tag_configure('odd', background=self.c('raised'))
        table.tag_configure('even', background=self.c('panel'))

        self.title(right, self.t('cargo_detail'))
        detail = self.f(right)
        detail.pack(fill='x', padx=19, pady=(0, 12))
        self.title(right, self.t('load'))
        qty_row = self.f(right)
        qty_row.pack(fill='x', padx=19)
        self.lbl(qty_row, self.t('qty'), size=10).pack(side='left')
        number = tk.Spinbox(qty_row, from_=1, to=999, width=7, relief='flat',
                            bg=self.c('input'), fg=self.c('fg'),
                            buttonbackground=self.c('raised'),
                            font=(self.ui_font_family(), self.sized(11)))
        number.pack(side='right')
        history = tk.Listbox(right, bg=self.c('input'), fg=self.c('fg'),
                             selectbackground=self.c('selection'),
                             selectforeground=self.c('fg'), relief='flat',
                             highlightthickness=0, font=(self.ui_font_family(), self.sized(10)), height=5)
        history.pack(fill='both', expand=False, padx=19, pady=(10, 8))
        total = self.lbl(right, '', size=13, bold=True, fg='accent')
        total.pack(anchor='w', padx=19, pady=(2, 10))

        def current_id():
            selection = table.selection()
            return selection[0] if selection else None

        def display_detail(_=None):
            for w in detail.winfo_children(): w.destroy()
            cid = current_id()
            if cid:
                self.last_selected_cargo = cid
            if not cid:
                self.lbl(detail, self.t('choose_cargo'), fg='muted',
                         size=10, wraplength=290).pack(anchor='w', pady=8)
                return
            overview = self.f(detail)
            overview.pack(fill='x', pady=(0,9))
            self.icon(overview, cid, 51).pack(side='left', padx=(0, 10), pady=3)
            cargo_info = self.f(overview)
            cargo_info.pack(side='left', fill='x', expand=True)
            self.lbl(cargo_info, display_cargo(cid, self.config['lang']), bold=True,
                     size=11, wraplength=205, justify='left').pack(anchor='w')
            self.lbl(cargo_info, cid, fg='muted', size=9).pack(anchor='w', pady=(3, 2))
            size = cargo_slots(cid)
            self.lbl(cargo_info, (f'{size} {self.t("slot_unit")}' if size is not None
                              else self.t('no_standard')), fg='accent', size=10,
                     bold=True, wraplength=205, justify='left').pack(anchor='w')
            icon_controls = self.f(detail)
            icon_controls.pack(fill='x', pady=(2, 9))
            self.btn(icon_controls, self.t('change_icon'), lambda c=cid:self.change_cargo_icon(c)).pack(fill='x', pady=(0, 4))
            if has_custom_icon(cid):
                self.btn(icon_controls, self.t('reset_icon'), lambda c=cid:self.restore_cargo_icon(c)).pack(fill='x')
            used = [r for r in (BUILTIN_RECIPES + self.official + self.custom) if cid in r.get('inputs',{}) or cid in r.get('outputs',{})]
            self.lbl(detail,self.t('craft_uses')+':',size=9,fg='muted').pack(anchor='w',pady=(7,4))
            if not used:
                self.lbl(detail,self.t('not_used'),size=9,fg='muted').pack(anchor='w')
            for rec in used[:2]:
                self.btn(detail,'↗  '+text_value(rec.get('name'),self.config['lang'])[:31],
                         lambda r=rec:self.open_recipe(r)).pack(fill='x',pady=2)

        table.bind('<<TreeviewSelect>>', display_detail)

        def refresh_history():
            history.delete(0, 'end')
            for cid, n in self.load:
                history.insert('end', f'{display_cargo(cid, self.config["lang"])} ×{n}  =  {n*cargo_slots(cid)}')
            total.configure(text=f'{self.t("total")}: {calculate_load(self.load)}')

        def add():
            cid = current_id()
            if not cid:
                messagebox.showinfo(self.t('catalog'), self.t('must_select'))
                return
            if cargo_slots(cid) is None:
                messagebox.showinfo(self.t('catalog'), self.t('cannot_load'))
                return
            try:
                qty = int(number.get())
                if qty <= 0: return
            except ValueError:
                return
            self.load.append((cid, qty))
            refresh_history()

        def remove():
            selection = history.curselection()
            if selection:
                self.load.pop(selection[0])
                refresh_history()

        self.btn(right, self.t('add_load'), add, primary=True).pack(fill='x', padx=19, pady=(2, 7))
        self.btn(right, self.t('delete'), remove).pack(fill='x', padx=19, pady=(0, 11))
        self.lbl(right, self.t('note_slots'), fg='muted', size=9,
                 wraplength=265, justify='left').pack(anchor='w', padx=19, pady=(0, 17))

        def query(*_):
            previous = current_id()
            term = q.get().strip().casefold()
            visible = [x for x in CARGO_DB if term in
                       ' '.join((x['id'], x.get('ru',''), x.get('en',''))).casefold()]
            visible = sort_cargo(visible, self.config['sort'], self.config['lang'])
            table.delete(*table.get_children())
            for i, item in enumerate(visible):
                table.insert('', 'end', iid=item['id'], tags=('odd' if i % 2 else 'even',),
                             image=self.photo(item['id'], 64),
                             values=(display_cargo(item['id'], self.config['lang']),
                                     item['slots'] if item['slots'] is not None else '—'))
            count_label.configure(text=f'{self.t("filter_count")}: {len(visible)} / {len(CARGO_DB)}')
            if previous and table.exists(previous):
                table.selection_set(previous)
            elif self.last_selected_cargo and table.exists(self.last_selected_cargo):
                table.selection_set(self.last_selected_cargo)
            elif visible:
                table.selection_set(visible[0]['id'])
            display_detail()

        def change_sort(mode):
            self.config['sort'] = mode
            save_json(SETTINGS_FILE, self.config)
            selected_sort.set(self.t(mode))
            query()

        def sort_selected(_=None):
            idx = sort_names.index(selected_sort.get()) if selected_sort.get() in sort_names else 0
            change_sort(modes[idx])

        self.cargo_sort = sort_combo  # Helps keyboard use and functional UI tests.
        self.cargo_table = table
        self.cargo_search = q
        sort_combo.bind('<<ComboboxSelected>>', sort_selected)
        q.trace_add('write', query)
        query()
        refresh_history()

    def open_recipe(self, recipe):
        self.selected_recipe=recipe
        self.show('recipes')

    def page_calculator(self):
        p=self.panel(self.body)
        p.pack(fill='both',expand=True)
        self.title(p,self.t('load'))
        line=self.f(p)
        line.pack(fill='x',padx=20,pady=10)
        shown=sorted(CARGO_DB,key=lambda x:display_cargo(x['id'],self.config['lang']))
        pick=ttk.Combobox(line,state='readonly',values=[display_cargo(x['id'],self.config['lang']) for x in shown],style='Dashboard.TCombobox',width=40)
        pick.pack(side='left',padx=(0,12))
        pick.current(0)
        qty=tk.Spinbox(line,from_=1,to=999,width=7,relief='flat',bg=self.c('input'),fg=self.c('fg'),buttonbackground=self.c('raised'))
        qty.pack(side='left',padx=(0,12))
        display=tk.Listbox(p,height=12,bg=self.c('input'),fg=self.c('fg'),selectbackground=self.c('selection'),relief='flat',font=(self.ui_font_family(), self.sized(11)))
        display.pack(fill='both',expand=True,padx=20,pady=16)
        total=self.lbl(p,'',size=16,bold=True,fg='accent')
        total.pack(anchor='w',padx=20,pady=(2,17))
        def refresh():
            display.delete(0,'end')
            for cid,n in self.load:
                display.insert('end',f'   {display_cargo(cid,self.config["lang"])}   ×{n}   =   {n*cargo_slots(cid)}')
            total.configure(text=f'{self.t("total")}: {calculate_load(self.load)}')
        def add():
            cid=shown[pick.current()]['id']
            if cargo_slots(cid) is None:
                messagebox.showinfo(self.t('load'),self.t('cannot_load'));return
            try: n=int(qty.get())
            except ValueError:return
            if n<1:return
            self.load.append((cid,n));refresh()
        def delete():
            selection=display.curselection()
            if selection:self.load.pop(selection[0]);refresh()
        buttons=self.f(p)
        buttons.pack(fill='x',padx=20,pady=(0,22))
        self.btn(buttons,self.t('add_load'),add,primary=True).pack(side='left',padx=(0,10))
        self.btn(buttons,self.t('delete'),delete).pack(side='left')
        refresh()

    def page_manual(self):
        p=self.panel(self.body)
        p.pack(fill='both',expand=True)
        self.title(p,f'{len(CARGO_DB)} / {len(BUILTIN_RECIPES)+len(self.official)}',self.t('offline'))
        self.lbl(p,self.t('icon_legend'),size=11,fg='muted',wraplength=760,justify='left').pack(anchor='w',padx=20,pady=(4,9))
        self.lbl(p,self.t('image_folder'),size=10,fg='accent',wraplength=760,justify='left').pack(anchor='w',padx=20,pady=(0,16))
        rows=self.f(p)
        rows.pack(fill='x',padx=20,pady=8)
        for c in CARGO_DB[:12]:
            item=self.f(rows,'raised')
            item.pack(side='left',padx=3)
            self.icon(item,c['id'],32,color='raised').pack(padx=4,pady=3)
        self.title(p,self.t('about_title'))
        self.lbl(p,self.t('not_complete'),size=11,fg='muted',wraplength=780,justify='left').pack(anchor='w',padx=20,pady=(0,13))
        self.btn(p,'MapRunner — Cargo',lambda:webbrowser.open('https://www.maprunner.info/cargo')).pack(anchor='w',padx=20,pady=(3,6))
        self.btn(p,'Saber Interactive — Crafting Zones',lambda:webbrowser.open(SOURCE_DOC)).pack(anchor='w',padx=20)

    def page_recipes(self):
        left = self.panel(self.body)
        left.pack(side='left', fill='both', padx=(0, 13))
        left.configure(width=438)
        left.pack_propagate(False)
        right = self.panel(self.body)
        right.pack(side='left', fill='both', expand=True)
        self.title(left, self.t('recipe_header'),
                   f'{len(BUILTIN_RECIPES) + len(self.official) + len(self.custom)} {self.t("recipes_count")}')
        filters = self.f(left)
        filters.pack(fill='x', padx=18, pady=(0, 12))
        region_keys = sorted({r.get('region','') for r in BUILTIN_RECIPES + self.official + self.custom if r.get('region')}, key=lambda k: display_region(k, self.config['lang']).casefold())
        regions = [self.t('all_regions')] + [display_region(k, self.config['lang']) for k in region_keys]
        region_var = tk.StringVar(value=regions[0])
        region_combo = ttk.Combobox(filters, values=regions, textvariable=region_var,
                                    state='readonly', style='Dashboard.TCombobox')
        region_combo.pack(fill='x', pady=(0, 10))
        q = tk.StringVar()
        self.ent(filters, q).pack(fill='x', ipady=7)
        holder = self.f(left)
        holder.pack(fill='both', expand=True, padx=16, pady=(0, 10))
        canvas = tk.Canvas(holder, bg=self.c('panel'), highlightthickness=0)
        scroll = ttk.Scrollbar(holder, orient='vertical', command=canvas.yview)
        listing = self.f(canvas)
        listing.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=listing, anchor='nw', tags='inner')
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure('inner', width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        detail_canvas = tk.Canvas(right, bg=self.c('panel'), highlightthickness=0)
        detail_scroll = ttk.Scrollbar(right, orient='vertical', command=detail_canvas.yview)
        self.recipe_right = self.f(detail_canvas)
        self.recipe_right.bind('<Configure>', lambda e: detail_canvas.configure(scrollregion=detail_canvas.bbox('all')))
        detail_canvas.create_window((0, 0), window=self.recipe_right, anchor='nw', tags='inner')
        detail_canvas.bind('<Configure>', lambda e: detail_canvas.itemconfigure('inner', width=e.width))
        detail_canvas.configure(yscrollcommand=detail_scroll.set)
        detail_canvas.pack(side='left', fill='both', expand=True)
        detail_scroll.pack(side='right', fill='y')

        def update(*_):
            for w in listing.winfo_children(): w.destroy()
            ix = regions.index(region_var.get()) if region_var.get() in regions else 0
            key = region_keys[ix-1] if ix else ''
            visible = filter_recipes(BUILTIN_RECIPES + self.official + self.custom, key, q.get(), self.config['lang'])
            if not visible:
                self.lbl(listing, self.t('filter_no'), fg='muted').pack(padx=15, pady=25)
            for recipe in visible:
                out = next(iter(recipe.get('outputs', {})), None)
                active = (self.selected_recipe is recipe)
                color = 'selection' if active else 'raised'
                card = self.f(listing, color, cursor='hand2')
                card.pack(fill='x', pady=(0, 8))
                if out: self.icon(card, recipe['id'] if self.photo(recipe['id'],64,recipe=True) else out, 41, color=color, recipe=bool(self.photo(recipe['id'],64,recipe=True))).pack(side='left', padx=12, pady=10)
                desc = self.f(card, color)
                desc.pack(side='left', fill='both', expand=True, pady=9)
                self.lbl(desc, text_value(recipe.get('name'), self.config['lang']),
                         bg=color, size=10, bold=True, anchor='w',
                         wraplength=265, justify='left').pack(fill='x')
                area = display_recipe_location(recipe, self.config['lang'])
                self.lbl(desc, area, bg=color, fg='muted', size=9,
                         anchor='w', wraplength=270, justify='left').pack(fill='x', pady=(4, 0))
                if recipe.get('generator'):
                    self.lbl(card, '⚡', bg=color, fg='accent', size=14).pack(side='right', padx=7)
                def click(_event=None, r=recipe):
                    self.selected_recipe = r
                    self.show_recipe_detail(r)
                    update()
                for widget in [card, *card.winfo_children(), *desc.winfo_children()]:
                    widget.bind('<Button-1>', click)
        region_combo.bind('<<ComboboxSelected>>', update)
        q.trace_add('write', update)
        update()
        actions = self.f(left)
        actions.pack(fill='x', padx=18, pady=(0, 16))
        self.btn(actions, self.t('add_recipe'), lambda: self.recipe_editor(), primary=True).pack(side='left',padx=(0,7))
        self.btn(actions, self.t('import_game'), self.import_game_data).pack(side='left', padx=(0,7))
        self.btn(actions, self.t('scan_game'), self.scan_game_folder).pack(side='left')
        self.show_recipe_detail(self.selected_recipe)

    def material_row(self, parent, cid, qty):
        row = self.f(parent, 'raised')
        row.pack(fill='x', padx=18, pady=4)
        self.icon(row, cid, 37, color='raised').pack(side='left', padx=(10, 12), pady=6)
        info = self.f(row, 'raised')
        info.pack(side='left', fill='x', expand=True)
        self.lbl(info, display_cargo(cid, self.config['lang']), bg='raised',
                 size=10, bold=True, anchor='w').pack(fill='x')
        slots = cargo_slots(cid)
        self.lbl(info, f'{slots} {self.t("slot_unit")}' if slots is not None else
                 self.t('no_standard'), bg='raised', size=9, fg='muted', anchor='w').pack(fill='x')
        self.lbl(row, '×' + str(qty), bg='raised', size=14,
                 fg='accent', bold=True).pack(side='right', padx=12)

    def show_recipe_detail(self, recipe):
        for w in self.recipe_right.winfo_children(): w.destroy()
        if recipe is None:
            self.title(self.recipe_right, self.t('recipe_title'))
            self.lbl(self.recipe_right, self.t('filter_no'),
                     fg='muted').pack(anchor='w', padx=20, pady=(12, 25))
            self.lbl(self.recipe_right, self.t('not_complete'), fg='muted',
                     size=10, wraplength=470, justify='left').pack(anchor='w', padx=20)
            return
        self.title(self.recipe_right, self.t('recipe_title'),
                   self.t('custom') if recipe in self.custom else self.t('game_imported'))
        output = next(iter(recipe.get('outputs', {})), None)
        if output: self.icon(self.recipe_right, recipe['id'] if self.photo(recipe['id'],64,recipe=True) else output, 58, recipe=bool(self.photo(recipe['id'],64,recipe=True))).pack(anchor='w', padx=20, pady=(3, 8))
        self.lbl(self.recipe_right, text_value(recipe.get('name'), self.config['lang']),
                 size=16, bold=True, wraplength=460, justify='left').pack(anchor='w', padx=20)
        area = display_recipe_location(recipe, self.config['lang'])
        self.lbl(self.recipe_right, area, fg='muted', size=10, wraplength=480,
                 justify='left').pack(anchor='w', padx=20, pady=(5, 18))
        self.lbl(self.recipe_right, self.t('components'), fg='muted',
                 size=10, bold=True).pack(anchor='w', padx=20, pady=(0, 7))
        if recipe.get('inputs'):
            for cid, qty in recipe['inputs'].items(): self.material_row(self.recipe_right, cid, qty)
        elif recipe.get('generator'):
            self.lbl(self.recipe_right, '⚡  ' + self.t('no_inputs'),
                     fg='accent', size=11, wraplength=470,
                     justify='left').pack(anchor='w', padx=20, pady=8)
            self.lbl(self.recipe_right, self.t('no_inputs_suffix'), fg='muted',
                     size=9).pack(anchor='w', padx=20)
        self.lbl(self.recipe_right, '↓', fg='accent', size=19).pack(anchor='w', padx=22, pady=8)
        self.lbl(self.recipe_right, self.t('result'), fg='muted',
                 size=10, bold=True).pack(anchor='w', padx=20, pady=(0, 7))
        for cid, qty in recipe.get('outputs', {}).items(): self.material_row(self.recipe_right, cid, qty)
        if display_recipe_notes(recipe, self.config['lang']):
            self.lbl(self.recipe_right, display_recipe_notes(recipe, self.config['lang']),
                     fg='muted', size=9, wraplength=470, justify='left').pack(anchor='w', padx=20, pady=(16, 3))
        actions = self.f(self.recipe_right)
        actions.pack(fill='x', padx=20, pady=(21, 16))
        if recipe.get('source_url'):
            self.btn(actions, self.t('source'),
                     lambda: webbrowser.open(recipe['source_url'])).pack(side='left', padx=(0, 7))
        if recipe.get('source_image'):
            image_path = (ROOT / recipe['source_image']).resolve()
            self.btn(actions, 'Открыть схему' if self.config['lang']=='ru' else 'View chart',
                     lambda p=image_path: webbrowser.open(p.as_uri())).pack(side='left', padx=(0, 7))
        if recipe in self.custom:
            self.btn(actions, self.t('edit_recipe'),
                     lambda: self.recipe_editor(recipe)).pack(side='left', padx=(0, 7))
            self.btn(actions, self.t('delete_recipe'),
                     lambda: self.delete_recipe(recipe)).pack(side='left')
        else:
            self.btn(actions, self.t('copy_recipe'),
                     lambda: self.recipe_editor(recipe, copy=True)).pack(side='left')

    def delete_recipe(self, recipe):
        if recipe not in self.custom: return
        if messagebox.askyesno(self.t('delete_recipe'), self.t('confirm')):
            self.custom.remove(recipe)
            save_json(CUSTOM_FILE, self.custom)
            self.selected_recipe = None
            self.render()

    def recipe_editor(self, base=None, copy=False):
        return RecipeEditor(self, base, copy)

    def _write_scan_report(self, file):
        report = inspect_path(file, lang=self.config['lang'])
        location = USER_DIR / 'SNOWRUNNER_SCAN_REPORT.txt'
        location.write_text(report['report'], encoding='utf-8')
        return report, location

    def _scan_summary(self, report, location):
        if self.config['lang'] == 'ru':
            return (f'Проверено архивов/файлов: {report["files"]}\n'
                    f'Найдено STG: {report["stg"]}\n'
                    f'Найдено JSON: {report["json"]}\n'
                    f'Ошибок чтения: {report["errors"]}\n\n'
                    f'Технический отчёт сохранён:\n{location}\n\n'
                    'Важно: это проверка формата, а не декодирование рецептов из STG. '
                    'Для настоящего декодера нужен образец data.stg.')
        return (f'Files checked: {report["files"]}\nSTG found: {report["stg"]}\n'
                f'JSON found: {report["json"]}\nRead errors: {report["errors"]}\n\n'
                f'Diagnostic report saved to:\n{location}\n\n'
                'This identifies files; it does not decode STG recipes. '
                'An actual data.stg sample is needed to develop a decoder.')

    def scan_game_folder(self):
        typical = Path('E:/SteamLibrary/steamapps/common/SnowRunner/preload/paks/client')
        initial = typical if typical.is_dir() else Path.home()
        folder = filedialog.askdirectory(parent=self.root, title=self.t('scan_title'),
                                         initialdir=str(initial))
        if not folder:
            return
        try:
            report, location = self._write_scan_report(folder)
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror(self.t('scan_title'), str(exc), parent=self.root)
            return
        messagebox.showinfo(self.t('scan_title'), self._scan_summary(report, location),
                            parent=self.root)

    def import_game_data(self):
        file=filedialog.askopenfilename(parent=self.root,
            title=self.t('import_game_title'),
            filetypes=[('Game cache / JSON / PAK / ZIP / STG','*.cache_block *.json *.pak *.zip *.stg'),('All files','*.*')])
        if not file:return
        if Path(file).suffix.lower() == '.stg':
            try:
                report, location = self._write_scan_report(file)
            except (OSError, ValueError, RuntimeError) as exc:
                messagebox.showerror(self.t('scan_title'),str(exc),parent=self.root)
                return
            messagebox.showinfo(self.t('scan_title'),self._scan_summary(report,location),parent=self.root)
            return
        try:
            entries,report=import_recipes(file,CARGO)
        except Exception as exc:
            messagebox.showerror(self.t('import_game_title'),str(exc),parent=self.root)
            return
        if not entries:
            detail = describe_import_failure(file, report, self.config['lang'])
            if Path(file).suffix.lower() in ('.pak', '.zip'):
                try:
                    analysis, location = self._write_scan_report(file)
                    detail += '\n\n' + self._scan_summary(analysis, location)
                except (OSError, ValueError, RuntimeError):
                    pass
            messagebox.showinfo(self.t('import_game_title'),detail,parent=self.root)
            return
        # Retain existing game-sourced recipes and deduplicate by ID.
        merged={entry['id']:entry for entry in self.official}
        builtin_ids={r['id'] for r in BUILTIN_RECIPES}
        merged.update({entry['id']:entry for entry in entries if entry['id'] not in builtin_ids})
        save_json(IMPORTED_FILE,list(merged.values()))
        self.official=list(merged.values())
        messagebox.showinfo(self.t('import_game_title'),
            self.t('import_done').format(n=len(entries),skip=len(report['unknown_ids'])),
            parent=self.root)
        self.selected_recipe=None
        self.render()

    def _save_profile_draft(self, force=False):
        """Synchronous per-profile autosave, including before any switch or exit."""
        if self._profile_save_error:
            raise ValueError(self._profile_save_error)
        current = list(self.load)
        if force or current != self._draft_saved_load:
            self.profiles.save_draft(self.active_profile_key, current)
            self._draft_saved_load = current

    def save_profile_draft(self):
        """Called after editing the calculator; error is reported without data loss."""
        try:
            self._save_profile_draft()
        except (OSError, ValueError) as exc:
            self._last_profile_sync_issue = str(exc)

    def close_app(self):
        try:
            self._save_profile_draft(force=True)
        except (OSError, ValueError) as exc:
            if not messagebox.askyesno('SnowRunner',
                    ('Не удалось сохранить черновик: ' + str(exc) + '\nЗакрыть без сохранения?' if self.config['lang']=='ru'
                     else 'Unable to save the draft: ' + str(exc) + '\nExit without saving?'), parent=self.root):
                return
        self.root.destroy()

    def _switch_profile(self, key, source=None):
        """Never switch based on timestamps; explicit user confirmation required."""
        ru = self.config['lang'] == 'ru'
        if key == self.active_profile_key:
            return True
        prompt = ('Сохранить текущий черновик в исходном профиле и переключиться?\n'
                  '«Нет» — продолжить работу и переключиться позже.' if ru else
                  'Save the current draft in its original profile and switch?\n'
                  'No — finish your work and switch later.')
        if not messagebox.askyesno('SnowRunner — профиль' if ru else 'SnowRunner — profile',
                                   prompt, parent=self.root):
            return False
        try:
            next_load = self.profiles.manifest(key)
            self._save_profile_draft(force=True)
        except (OSError, ValueError) as exc:
            messagebox.showerror('SnowRunner', str(exc), parent=self.root)
            return False
        self.active_profile_key = key
        self.config['selected_game_profile'] = key
        save_json(SETTINGS_FILE, self.config)
        self._draft_saved_load = list(next_load)
        self.load = next_load
        self._profile_save_error = None
        self._last_profile_sync_issue = ''
        self.render()
        return True

    def _active_slot_path(self):
        if self.active_profile_key == 'local':
            return None
        try:
            archives, slots = self._local_game_paths()
        except OSError:
            return None
        for slot in slots:
            if slot['profile_key'] == self.active_profile_key:
                return Path(slot['path'])
        # No fallback to a different slot if selected file was moved/deleted.
        return None

    def _sync_active_profile(self):
        """Read a stable game save and update ONLY the corresponding app snapshot."""
        source = self._active_slot_path()
        if source is None:
            raise ValueError('Selected game save not found; choose its folder again')
        snapshot, signature = snapshot_save(source)
        self.profiles.save_game_snapshot(self.active_profile_key, source, snapshot, signature)
        self.save_monitor.pending.pop(str(source.resolve()), None)
        self._last_profile_sync_issue = ''
        return snapshot

    def refresh_active_profile(self):
        ru = self.config['lang'] == 'ru'
        if self.active_profile_key == 'local':
            messagebox.showinfo('SnowRunner',
                 'Сначала выбери игровой профиль.' if ru else 'Select a game profile first.',
                 parent=self.root)
            return
        try:
            report = self._sync_active_profile()
        except (OSError, ValueError) as exc:
            messagebox.showerror('SnowRunner', str(exc), parent=self.root)
            return
        messagebox.showinfo('SnowRunner', self._snapshot_description(report), parent=self.root)

    def _snapshot_description(self, snap):
        ru = self.config['lang'] == 'ru'
        stats = snap.get('statistics') or {}
        trucks = snap.get('retained_trucks') or {}
        objectives = snap.get('objectives') or {}
        visited = snap.get('visited_levels') or {}
        garages = snap.get('garages') or {}
        cargo = snap.get('cargo_depots') or {}
        def displayed(number):
            return '?' if number is None else str(number)
        if ru:
            return '\n'.join([
                'Сводка сохранения (только чтение):',
                'Деньги: ' + displayed(stats.get('money')),
                'Опыт: ' + displayed(stats.get('experience')),
                'Заданий завершено (finishedObjs): ' + displayed(objectives.get('completed')),
                'Записей активных заданий: ' + displayed(objectives.get('known_entries')),
                'Посещённых карт: ' + displayed(visited.get('count')),
                'Открытых гаражей (статус 2): ' + displayed(garages.get('open_count')),
                'Машин на хранении: ' + displayed(trucks.get('count')),
                ('Возможные остатки складов: ' + str(cargo.get('count', 0)) +
                 ' (формат не подтверждён, в расчёты не включаются).'),
                'Туман карт и машины внутри гаражей: ещё не распознаются.',
            ])
        return '\n'.join([
            'Read-only game save snapshot:',
            'Money: ' + displayed(stats.get('money')),
            'Experience: ' + displayed(stats.get('experience')),
            'Completed objectives (finishedObjs): ' + displayed(objectives.get('completed')),
            'Active objective records: ' + displayed(objectives.get('known_entries')),
            'Visited maps: ' + displayed(visited.get('count')),
            'Open garages (status 2): ' + displayed(garages.get('open_count')),
            'Retained trucks: ' + displayed(trucks.get('count')),
            ('Possible depot records: ' + str(cargo.get('count', 0)) +
             ' (unverified schema, excluded from calculations).'),
            'Map fog and vehicles physically inside garages: not yet decoded.',
        ])

    def _snapshot_details_text(self, snap):
        ru = self.config['lang'] == 'ru'
        lines = [self._snapshot_description(snap), '', ('Детали сохранения' if ru else 'Save details'),
                 ('Идентификаторы из игровых файлов, без изменения игры.' if ru
                  else 'Game-file identifiers; the game is never modified.')]
        def section(ru_header, en_header, values, unavailable=None):
            lines.extend(['', ru_header if ru else en_header])
            if values is None:
                lines.append(unavailable or ('Нет подтверждённых данных' if ru else 'No verified data'))
            elif not values:
                lines.append('(пусто)' if ru else '(empty)')
            else:
                lines.extend(' • '+str(x) for x in values)
        levels = snap.get('visited_levels') or {}
        section('Посещённые карты', 'Visited maps', levels.get('items') if levels.get('available') else None)
        garages = snap.get('garages') or {}
        if garages.get('available'):
            statuses = garages.get('statuses', {})
            section('Статусы гаражей: 2 = открыт', 'Garage statuses: 2 = open',
                    [f'{m}: {code}' for m, code in sorted(statuses.items())] if statuses else garages.get('opened', []))
        else:
            section('Статусы гаражей', 'Garage statuses', None)
        objectives = snap.get('objectives') or {}
        section('Завершённые задания (finishedObjs)', 'Completed objectives (finishedObjs)',
                objectives.get('finished_ids') if objectives.get('completed') is not None else None)
        fleet = snap.get('retained_trucks') or {}
        section('Машины на хранении, по моделям', 'Retained truck models',
                [f'{model}: {amount}' for model,amount in sorted(fleet.get('models', {}).items())]
                if fleet.get('available') else None)
        depots = snap.get('cargo_depots') or {}
        lines.extend(['', ('Предварительные данные складов — НЕ подтверждены' if ru
                           else 'Candidate warehouse data — NOT VERIFIED')])
        if depots.get('candidates'):
            for item in depots['candidates']:
                lines.append('[' + item['warehouse_id'] + ']')
                for cargo, quantity in item['cargo'].items():
                    suffix = ' (код -1; вероятно без ограничений)' if quantity == -1 and ru else (
                        ' (code -1; likely unlimited)' if quantity == -1 else '')
                    lines.append('   ' + cargo + ': ' + str(quantity) + suffix)
        else:
            lines.append('Соответствующих полей не обнаружено.' if ru else 'No corresponding fields found.')
        lines.append(('Эти остатки не используются для расчётов и списаний.' if ru
                      else 'Candidate quantities are not used for planning or deductions.'))
        if depots.get('truncated') or levels.get('truncated') or garages.get('truncated') or objectives.get('finished_truncated'):
            lines.append('Часть данных усечена для безопасности.' if ru else 'Some data truncated for safety.')
        return '\n'.join(lines)

    def view_saved_progress(self):
        ru = self.config['lang'] == 'ru'
        if self.active_profile_key == 'local':
            messagebox.showinfo('SnowRunner', 'Выбери игровой профиль.' if ru else 'Select a game profile.', parent=self.root)
            return
        try:
            snap = self.profiles.read(self.active_profile_key).get('game_snapshot')
        except (OSError, ValueError) as exc:
            messagebox.showerror('SnowRunner', str(exc), parent=self.root)
            return
        if not snap:
            messagebox.showinfo('SnowRunner', 'Сначала считай сохранение.' if ru else 'Read the save first.', parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title('Прогресс SnowRunner — только чтение' if ru else 'SnowRunner Progress — read-only')
        win.geometry('890x630')
        win.configure(bg=self.c('panel'))
        header = tk.Label(win, text='Прогресс игры' if ru else 'Game progress',
                          bg=self.c('panel'), fg=self.c('accent'), font=(self.ui_font_family(),16,'bold'))
        header.pack(anchor='w',padx=18,pady=(12,6))
        area = self.f(win)
        area.pack(fill='both',expand=True,padx=18,pady=6)
        scrollbar = tk.Scrollbar(area)
        scrollbar.pack(side='right',fill='y')
        txt = tk.Text(area,wrap='word',bg=self.c('input'),fg=self.c('fg'),
                      insertbackground=self.c('fg'),font=(self.ui_font_family(),10),
                      relief='flat',padx=12,pady=10,yscrollcommand=scrollbar.set)
        txt.pack(fill='both',expand=True)
        scrollbar.config(command=txt.yview)
        report = self._snapshot_details_text(snap)
        txt.insert('1.0',report)
        txt.config(state='disabled')
        def copy_summary():
            win.clipboard_clear()
            win.clipboard_append(report)
        self.btn(win,'Копировать сводку' if ru else 'Copy report',copy_summary).pack(anchor='e',padx=18,pady=(4,12))
        win.lift()
        return win

    def _background_profile_cycle(self):
        """Tk scheduled disk checks; never assumes another slot is currently in use."""
        try:
            self.save_profile_draft()
            if self.active_profile_key != 'local':
                source = self._active_slot_path()
                if source is not None:
                    data = self.profiles.read(self.active_profile_key)
                    state = self.save_monitor.check(source, data.get('last_signature'))
                    if state == 'changed':
                        try:
                            self._sync_active_profile()
                        except (OSError, ValueError) as exc:
                            self._last_profile_sync_issue = str(exc)
        except (OSError, ValueError) as exc:
            self._last_profile_sync_issue = str(exc)
        finally:
            try:
                if self.root.winfo_exists():
                    self.root.after(12000, self._background_profile_cycle)
            except tk.TclError:
                pass

    def save_structure_dialog(self):
        """Inspect the selected save's *redacted schema* without changing the file."""
        from save_diagnostics import report_save_structure
        source = self._active_slot_path()
        ru = self.config.get('lang') == 'ru'
        if source is None:
            messagebox.showinfo('SnowRunner', 'Сначала выбери сохранение.' if ru else 'Select a save first.', parent=self.root)
            return None
        try:
            report = report_save_structure(source)
        except (OSError, ValueError) as exc:
            messagebox.showerror('SnowRunner', str(exc), parent=self.root)
            return None
        win = tk.Toplevel(self.root)
        win.title('Структура сохранения (без значений)' if ru else 'Save structure (redacted)')
        win.geometry('840x610')
        win.configure(bg=self.c('panel'))
        tk.Label(win, text=('Диагностика структуры — скрыты значения и ID' if ru
                           else 'Structure diagnostics — values and IDs omitted'),
                 bg=self.c('panel'), fg=self.c('accent'), font=(self.ui_font_family(), 13, 'bold')).pack(anchor='w',padx=14,pady=10)
        txt = tk.Text(win, bg=self.c('input'), fg=self.c('fg'), wrap='none', relief='flat',
                      font=('Consolas', 10))
        txt.pack(fill='both', expand=True, padx=14, pady=(0,8))
        txt.insert('1.0', report)
        txt.configure(state='disabled')
        def copy():
            win.clipboard_clear()
            win.clipboard_append(report)
        self.btn(win, 'Копировать схему' if ru else 'Copy schema', copy).pack(anchor='e',padx=14,pady=(0,10))
        win.lift()
        return win

    def route_planner_dialog(self):
        """Manual stop ordering and profile-bound logistics plans."""
        from route_ui import open_route_planner
        return open_route_planner(self)

    def warehouse_preview_dialog(self):
        """Tentative per-warehouse planning after explicit manual cargo-ID mapping."""
        from depot_ui import open_depot_preview
        return open_depot_preview(self)

    def drafts_dialog(self):
        """Manage named load plans and recovery history in the selected profile."""
        from draft_ui import open_draft_manager
        return open_draft_manager(self)

    def game_connection_dialog(self):
        """Profile UI: manual selection, read-only snapshots, safe draft switches."""
        ru = self.config['lang'] == 'ru'
        win = tk.Toplevel(self.root)
        win.title('Подключение SnowRunner и профили' if ru else 'SnowRunner connection and profiles')
        win.geometry('960x665')
        win.minsize(720, 535)
        win.configure(bg=self.c('panel'))
        tk.Label(win,text=('Подключение и игровые профили' if ru else 'Game connection and profiles'),
                 bg=self.c('panel'),fg=self.c('accent'),font=(self.ui_font_family(),19,'bold')).pack(anchor='w',padx=24,pady=(18,6))
        tk.Label(win,text=('Источник — файлы игры. Черновики хранятся отдельно, в папке приложения.' if ru
                           else 'Game files are read-only. Drafts stay separately in app data.'),
                 bg=self.c('panel'),fg=self.c('fg'),font=(self.ui_font_family(),10)).pack(anchor='w',padx=24)
        status = tk.Label(win,text='',anchor='w',bg=self.c('panel'),fg=self.c('accent'),
                          font=(self.ui_font_family(),10,'bold'))
        status.pack(fill='x',padx=24,pady=(8,6))
        select_label = ('Найденные слоты (выбор вручную):' if ru else 'Discovered save slots (manual selection):')
        tk.Label(win,text=select_label,bg=self.c('panel'),fg=self.c('fg'),
                 font=(self.ui_font_family(),10,'bold')).pack(anchor='w',padx=24)
        slots_list = tk.Listbox(win,height=5,selectmode='browse',bg=self.c('input'),fg=self.c('fg'),
                                selectbackground=self.c('selection'),
                                font=(self.ui_font_family(),10),borderwidth=0,exportselection=False)
        slots_list.pack(fill='x',padx=24,pady=(5,8))
        result = tk.Text(win,wrap='word',bg=self.c('input'),fg=self.c('fg'),
                         insertbackground=self.c('fg'),font=(self.ui_font_family(),10),
                         relief='flat',highlightthickness=1,highlightbackground=self.c('stroke'),
                         padx=12,pady=12)
        result.pack(fill='both',expand=True,padx=24,pady=(4,10))
        slot_items = []

        def update_summary():
            nonlocal slot_items
            try:
                archives, found_slots = self._local_game_paths()
                slot_items = found_slots
                active = self.active_profile_key
                status.configure(text=('Выбранный профиль: ' if ru else 'Selected profile: ') +
                                 ('Мой локальный' if active == 'local' and ru else
                                  ('Local draft' if active == 'local' else active)))
                slots_list.delete(0, 'end')
                for item in slot_items:
                    mark = '● ' if item['profile_key'] == active else '   '
                    slots_list.insert('end',f'{mark}{item["platform_hint"]} — слот {item["slot"]} — {item["path"]}')
                lines = [status_summary(archives,found_slots,self.config['lang'])]
                if active != 'local':
                    try:
                        data = self.profiles.read(active)
                        if data.get('game_snapshot'):
                            lines.extend(['',self._snapshot_description(data['game_snapshot'])])
                            lines.append(('Обновлено: ' if ru else 'Updated: ')+str(data.get('last_synced_utc','?')))
                        else: lines.append(('Данные ещё не прочитаны.' if ru else 'No snapshot read yet.'))
                    except (OSError, ValueError) as exc:lines.append(str(exc))
                if self._last_profile_sync_issue:
                    lines.append(('Последняя ошибка: ' if ru else 'Last error: ')+self._last_profile_sync_issue)
                body='\n'.join(lines)
            except OSError as exc:
                body=str(exc)
            result.configure(state='normal')
            result.delete('1.0','end')
            result.insert('1.0',body)
            result.configure(state='disabled')

        def select_profile():
            chosen = slots_list.curselection()
            if not chosen:return
            item = slot_items[chosen[0]]
            if self._switch_profile(item['profile_key'], item['path']):
                # Populate only the explicitly selected profile; unavailable data remains unknown.
                try:self._sync_active_profile()
                except (OSError, ValueError) as exc:self._last_profile_sync_issue = str(exc)
                update_summary()

        def choose_game():
            folder=filedialog.askdirectory(parent=win,
                title='Папка SnowRunner' if ru else 'SnowRunner installation',
                initialdir=self.config.get('game_install_dir') or str(Path.home()))
            if folder:
                self.config['game_install_dir']=folder
                save_json(SETTINGS_FILE,self.config)
                update_summary()

        def choose_saves():
            folder=filedialog.askdirectory(parent=win,
                title='Папка сохранений' if ru else 'Save folder',
                initialdir=self.config.get('game_save_dir') or str(Path.home()))
            if folder:
                self.config['game_save_dir']=folder
                save_json(SETTINGS_FILE,self.config)
                update_summary()

        actions=self.f(win)
        actions.pack(fill='x',padx=24,pady=(0,7))
        self.btn(actions,'Обновить список' if ru else 'Rescan',update_summary).pack(side='left',padx=(0,7))
        self.btn(actions,'Папка игры' if ru else 'Game folder',choose_game).pack(side='left',padx=(0,7))
        self.btn(actions,'Сохранения' if ru else 'Save folder',choose_saves).pack(side='left',padx=(0,7))
        self.btn(actions,'Выбрать профиль' if ru else 'Switch profile',select_profile,primary=True).pack(side='left')
        extra=self.f(win)
        extra.pack(fill='x',padx=24,pady=(0,7))
        self.btn(extra,'Мой локальный профиль' if ru else 'Local draft',
                 lambda: (self._switch_profile('local') and update_summary())).pack(side='left',padx=(0,7))
        def sync_now():
            self.refresh_active_profile()
            update_summary()
        self.btn(extra,'Считать сохранение' if ru else 'Read selected save',sync_now).pack(side='left',padx=(0,7))
        self.btn(extra,'Детали прогресса' if ru else 'Progress details',
                 self.view_saved_progress).pack(side='left',padx=(0,7))
        self.btn(extra,'Импорт рецептов' if ru else 'Import recipes',
                 self.refresh_from_installed_game).pack(side='left')
        drafts_row=self.f(win)
        drafts_row.pack(fill='x',padx=24,pady=(0,6))
        self.btn(drafts_row,'Черновики и история загрузки' if ru else 'Load drafts and history',
                 self.drafts_dialog).pack(side='left')
        self.btn(drafts_row,'Склады: просмотр остатков' if ru else 'Warehouse estimates',
                 self.warehouse_preview_dialog).pack(side='left',padx=(8,0))
        self.btn(drafts_row,'Маршруты' if ru else 'Routes',
                 self.route_planner_dialog).pack(side='left',padx=(8,0))
        self.btn(drafts_row,'Схема сохранения' if ru else 'Save schema',
                 self.save_structure_dialog).pack(side='left',padx=(8,0))
        tk.Label(win,text=('Проверка каждые 12 секунд; синхронизируется лишь вручную выбранный профиль.\n'
                           'Изменённый файл ≠ активное сохранение игры.' if ru else
                           'Checks every 12 seconds, syncing only the explicitly selected profile.\n'
                           'Changed file does not prove the active in-game slot.'),
                 justify='left',bg=self.c('panel'),fg=self.c('muted'),font=(self.ui_font_family(),9)).pack(anchor='w',padx=24,pady=(0,11))
        update_summary()
        win.lift()
        return win

    def select_game_directory(self):
        """Associate a local SnowRunner installation without touching game files."""
        folder = filedialog.askdirectory(parent=self.root,
            title=('Папка установленной SnowRunner' if self.config['lang']=='ru' else 'SnowRunner installation folder'),
            initialdir=self.config.get('game_install_dir') or str(Path.home()))
        if folder:
            self.config['game_install_dir'] = folder
            save_json(SETTINGS_FILE, self.config)
            self.detect_game_data()

    def select_save_directory(self):
        folder = filedialog.askdirectory(parent=self.root,
            title=('Папка сохранений SnowRunner' if self.config['lang']=='ru' else 'SnowRunner save folder'),
            initialdir=self.config.get('game_save_dir') or str(Path.home()))
        if folder:
            self.config['game_save_dir'] = folder
            save_json(SETTINGS_FILE, self.config)
            self.detect_game_data()

    def _local_game_paths(self):
        """Explicit folders remain optional; never infer which save is active."""
        game_folder = self.config.get('game_install_dir')
        save_folder = self.config.get('game_save_dir')
        archives = discover_game_archives([game_folder], only_extra=True) if game_folder else discover_game_archives()
        slots = discover_save_slots([save_folder], only_extra=True) if save_folder else discover_save_slots()
        return archives, slots

    def detect_game_data(self):
        lang = self.config['lang']
        try:
            archives, slots = self._local_game_paths()
            lines = [status_summary(archives, slots, lang)]
            for archive in archives[:3]:
                try:
                    report = inspect_archive(archive)
                    lines.append(f'{archive.name}: XML={report["xml"]}, JSON={report["json"]}, cache={report["cache_blocks"]}')
                except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
                    lines.append(f'{archive.name}: {exc}')
            ok = 0
            errors = []
            for slot in slots:
                try:
                    inspect_save(slot['path'])
                    ok += 1
                except (OSError, ValueError, RuntimeError) as exc:
                    errors.append(f'Slot {slot["slot"]}: {exc}')
            lines.append(('JSON-сохранений прочитано: ' if lang=='ru' else 'JSON saves read: ')+str(ok))
            lines.extend(errors[:5])
            result = '\n'.join(lines)
        except (OSError, PermissionError) as exc:
            result = str(exc)
        messagebox.showinfo(('Подключение SnowRunner' if lang=='ru' else 'SnowRunner connection'),
                            result, parent=self.root)
        return result

    def refresh_from_installed_game(self):
        """Import verified crafting records from the selected installed initial.pak.

        Existing recipes are preserved if extraction has no verified results.
        """
        lang = self.config['lang']
        try:
            archives, _slots = self._local_game_paths()
        except OSError as exc:
            messagebox.showerror('SnowRunner', str(exc), parent=self.root)
            return
        if not archives:
            messagebox.showinfo('SnowRunner',
                ('initial.pak не найден. Укажи папку установленной игры.' if lang=='ru'
                 else 'initial.pak was not found. Select the installed game folder.'), parent=self.root)
            return
        archive = archives[0]  # if multiple installations exist, ask user which one
        if len(archives) > 1:
            # Importing the wrong game version would silently mix data.
            messagebox.showinfo('SnowRunner',
                ('Обнаружено несколько установок. Укажи нужную через «Выбрать папку игры».'
                 if lang=='ru' else 'Multiple installations detected. Select the game folder explicitly.'),
                parent=self.root)
            return
        try:
            entries, report = import_recipes(archive, CARGO)
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
            messagebox.showerror('SnowRunner', str(exc), parent=self.root)
            return
        if not entries:
            messagebox.showinfo('SnowRunner', describe_import_failure(archive, report, lang), parent=self.root)
            return
        builtin_ids = {r['id'] for r in BUILTIN_RECIPES}
        merged = {r['id']:r for r in self.official}
        merged.update({r['id']:r for r in entries if r['id'] not in builtin_ids})
        save_json(IMPORTED_FILE, list(merged.values()))
        self.official = list(merged.values())
        self.selected_recipe = None
        messagebox.showinfo('SnowRunner',
            (f'Рецепты загружены напрямую из {archive.name}: {len(entries)}.' if lang=='ru'
             else f'Recipes imported directly from {archive.name}: {len(entries)}.'), parent=self.root)
        self.render()

    def page_settings(self):
        pane = self.panel(self.body)
        pane.pack(fill='both', expand=True)
        self.title(pane, self.t('theme'))
        preview = self.f(pane)
        preview.pack(fill='x', padx=23, pady=(4, 24))
        for theme in ('game', 'dark', 'light', 'forest'):
            sample = THEMES[theme]
            active = self.config['theme'] == theme
            card = tk.Frame(preview, bg=sample['panel'], highlightthickness=2 if active else 1,
                            highlightbackground=self.c('accent') if active else self.c('stroke'),
                            cursor='hand2', width=160, height=94)
            card.pack(side='left', padx=(0, 13))
            card.pack_propagate(False)
            strip = tk.Frame(card, bg=sample['accent'], height=6)
            strip.pack(fill='x', padx=12, pady=(13, 10))
            title = tk.Label(card, text=('✓ ' if active else '') + ('SnowRunner / Game' if theme == 'game' else self.t('theme_' + theme)),
                             bg=sample['panel'], fg=sample['fg'], font=(self.ui_font_family(), self.sized(11), 'bold'))
            title.pack(anchor='w', padx=12)
            def choose(_event=None, target=theme): self.change('theme', target)
            for widget in (card, strip, title): widget.bind('<Button-1>', choose)
        self.title(pane, self.t('lang'))
        languages = self.f(pane)
        languages.pack(anchor='w', padx=23, pady=(4, 25))
        for code, title in (('ru', 'Русский'), ('en', 'English')):
            self.btn(languages, ('✓  ' if self.config['lang'] == code else '') + title,
                     lambda value=code: self.change('lang', value),
                     primary=self.config['lang'] == code).pack(side='left', padx=(0, 12))
        self.title(pane, 'Обновления программы' if self.config['lang']=='ru' else 'Program updates')
        update_line=self.f(pane)
        update_line.pack(anchor='w',padx=23,pady=(4,12))
        self.btn(update_line, 'Проверить обновления' if self.config['lang']=='ru' else 'Check for updates',
                 self.updater.open_settings).pack(side='left',padx=(0,12))
        self.lbl(update_line,'v'+CURRENT_VERSION, fg='muted',size=10).pack(side='left')
        self.title(pane, self.t('animation'))
        motion_var=tk.BooleanVar(value=bool(self.config.get('animations',True)))
        tk.Checkbutton(pane,text=self.t('animation'),variable=motion_var,
                       command=lambda:self.change('animations',motion_var.get()),
                       bg=self.c('panel'),fg=self.c('fg'),selectcolor=self.c('input'),
                       activebackground=self.c('panel'),activeforeground=self.c('fg'),
                       font=(self.ui_font_family(), self.sized(11))).pack(anchor='w',padx=23,pady=(4,18))
        self.title(pane, 'Масштаб и шрифты' if self.config['lang']=='ru' else 'Scale and fonts')
        for name,key in ((('Масштаб окна' if self.config['lang']=='ru' else 'UI zoom'),'ui_scale'),
                         (('Размер текста' if self.config['lang']=='ru' else 'Text size'),'text_size')):
            line=self.f(pane);line.pack(anchor='w',padx=23,pady=(0,5))
            self.lbl(line,f'{name}: {self.config[key]}%',size=10).pack(side='left',padx=(0,10))
            self.btn(line,'−',lambda k=key:self.adjust(k,-10)).pack(side='left',padx=3)
            self.btn(line,'+',lambda k=key:self.adjust(k,10)).pack(side='left',padx=3)
        for code,title in (('cyrillic','Кириллица / Cyrillic'),('latin','Латиница / Latin')):
            line=self.f(pane);line.pack(anchor='w',padx=23,pady=(0,4))
            self.lbl(line,title+': '+self.font_manager.label(code),size=9).pack(side='left',padx=(0,10))
            self.btn(line,'TTF / OTF',lambda k=code:self.import_font(k)).pack(side='left',padx=4)
            self.btn(line,'↺',lambda k=code:self.reset_font(k)).pack(side='left',padx=4)
        self.title(pane, ('Подключение к установленной SnowRunner' if self.config['lang']=='ru'
                          else 'Connect installed SnowRunner'))
        game_buttons = self.f(pane)
        game_buttons.pack(anchor='w', padx=23, pady=(4, 8))
        is_ru = self.config['lang']=='ru'
        self.btn(game_buttons, 'Найти игру и сохранения' if is_ru else 'Find game and saves',
                 self.detect_game_data).pack(side='left',padx=(0,8))
        self.btn(game_buttons, 'Выбрать папку игры' if is_ru else 'Select game folder',
                 self.select_game_directory).pack(side='left',padx=(0,8))
        self.btn(game_buttons, 'Выбрать сохранения' if is_ru else 'Select save folder',
                 self.select_save_directory).pack(side='left')
        self.btn(pane, 'Обновить рецепты из initial.pak' if is_ru else 'Refresh recipes from initial.pak',
                 self.refresh_from_installed_game).pack(anchor='w', padx=23, pady=(0, 12))
        self.lbl(pane, ('Чтение только для просмотра. Активное сохранение не угадывается. '
                        'Для актуальных данных дождитесь записи сохранения игрой.' if is_ru else
                        'Read-only. Active save is never guessed. Data refreshes after the game saves to disk.'),
                 fg='muted', size=9, wraplength=780,
                 justify='left').pack(anchor='w',padx=23,pady=(0,15))
        self.title(pane, self.t('about_title'))
        for key in ('about', 'export_info', 'icon_legend', 'image_folder', 'not_complete'):
            self.lbl(pane, self.t(key), fg='muted', size=10, wraplength=780,
                     justify='left').pack(anchor='w', padx=23, pady=(2, 9))
        self.lbl(pane, str(CUSTOM_FILE), fg='muted', size=9,
                 wraplength=800, justify='left').pack(anchor='w', padx=23, pady=(10, 0))

    def appearance_editor(self):
        AppearanceEditor(self)

    def apply_appearance(self, settings):
        settings=normalize(settings)
        # Keep personal theme artwork inside the user's settings directory.
        managed=USER_DIR/'appearance_assets'
        for key in ('background_image','header_image'):
            path=settings.get(key,'')
            if path and Path(path).is_file() and Path(path).resolve().parent!=managed.resolve():
                try:settings[key]=_copy_asset(path,managed)
                except (OSError,ValueError) as exc:messagebox.showwarning('Image',str(exc),parent=self.root)
        for kind,path in list(settings.get('nav_icons',{}).items()):
            if path and Path(path).is_file() and Path(path).resolve().parent!=managed.resolve():
                try:settings['nav_icons'][kind]=_copy_asset(path,managed)
                except (OSError,ValueError) as exc:messagebox.showwarning('Icon',str(exc),parent=self.root)
        self.config['appearance']=settings
        self.config['theme']='game'
        self.config['ui_scale']=settings['ui_scale']
        self.config['text_size']=settings['text_size']
        self.config['animations']=settings['animations']
        for script in ('cyrillic','latin'):
            path=settings.get('font_'+script, '')
            if path and path!=self.config.get('font_'+script,''):
                try:self.font_manager.install(path,script)
                except (OSError,ValueError,RuntimeError) as exc:
                    messagebox.showerror('Font',str(exc),parent=self.root)
            elif not path and self.config.get('font_'+script):
                self.font_manager.reset(script)
        save_json(SETTINGS_FILE,self.config)
        self.render()

    def import_font(self, script):
        prompt=('Кириллица' if script=='cyrillic' else 'Латиница') if self.config['lang']=='ru' else ('Cyrillic' if script=='cyrillic' else 'Latin')
        picked=filedialog.askopenfilename(parent=self.root,title=prompt,filetypes=[('TrueType/OpenType','*.ttf *.otf'),('All files','*.*')])
        if not picked:return
        try:
            self.font_manager.install(picked,script)
        except (ValueError,RuntimeError,OSError) as exc:
            messagebox.showerror('Шрифт / Font',str(exc),parent=self.root)
            return
        save_json(SETTINGS_FILE,self.config)
        self.render()

    def reset_font(self, script):
        self.font_manager.reset(script)
        save_json(SETTINGS_FILE,self.config)
        self.render()

    def adjust(self,key,delta):
        limits={'ui_scale':(75,150),'text_size':(75,160)}
        lo,hi=limits[key]
        self.change(key,max(lo,min(hi,int(self.config.get(key,100))+delta)))

    def change(self, key, value):
        self.config[key] = value
        if key in ('ui_scale','text_size','animations'):
            self.config.setdefault('appearance',{})[key]=value
        save_json(SETTINGS_FILE, self.config)
        self.render()


if __name__ == '__main__':
    root = tk.Tk()
    Application(root)
    root.mainloop()
