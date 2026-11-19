"""Data model and validation; uses only the Python standard library."""
import json
import sys
import re
from pathlib import Path

APP_NAME = 'SnowRunnerCraftAssistant'
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
USER_DIR = Path.home() / APP_NAME
USER_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = USER_DIR / 'settings.json'
CUSTOM_FILE = USER_DIR / 'recipes.json'
IMPORTED_FILE = USER_DIR / 'game_recipes.json'

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default

def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

CARGO_DB = load_json(ROOT / 'catalog.json', {}).get('cargo', [])
CARGO = {entry['id']: entry for entry in CARGO_DB}
REGIONS_DATA = load_json(ROOT / 'recipes_builtin.json', {})
BUILTIN_RECIPES = REGIONS_DATA.get('recipes', [])
REGIONS = REGIONS_DATA.get('regions', {})
ALIASES = {'concrete_slabs': 'concrete_slab','large_pipes':'large_pipe', 'oil_barrel':'oil_barrels'}

def display_cargo(cid, lang='ru'):
    cid = ALIASES.get(cid, cid)
    entry = CARGO.get(cid)
    return entry.get(lang, entry['en']) if entry else cid.replace('_',' ').title()

_INTERNAL_MAP = re.compile(r'^(?:level_(?:ru|us)_|(?:ru|us)_\d{2}_|prog_)', re.I)

def display_region(region, lang='ru'):
    """Translate a map/region key for players, never exposing internal map codes."""
    lang = lang if lang in ('ru', 'en') else 'ru'
    if not region:
        return 'Регион не указан' if lang == 'ru' else 'Region not specified'
    item=REGIONS.get(str(region))
    if item:
        name=text_value(item,lang)
        if name and not _INTERNAL_MAP.match(name):return name
    if _INTERNAL_MAP.match(str(region)):
        return 'Карта не определена' if lang == 'ru' else 'Unknown map'
    return str(region)

def display_recipe_location(recipe, lang='ru'):
    """Location label for a whole recipe without duplicate map codes."""
    region=recipe.get('region','') or ''
    map_key=recipe.get('map','') or ''
    if region in REGIONS:
        known=display_region(region,lang)
        if _INTERNAL_MAP.match(str(map_key)) or map_key==region or not map_key:
            return known
        # A custom recipe may have a real factory name, separate from the region.
        return known+' — '+str(map_key)
    # An imported recipe may have the map stored only in its map property.
    if map_key in REGIONS:return display_region(map_key,lang)
    region_label=display_region(region,lang)
    if map_key and not _INTERNAL_MAP.match(str(map_key)) and map_key!=region:
        region_label+=' — '+str(map_key)
    return region_label

def display_recipe_notes(recipe, lang='ru'):
    """Do not surface facility IDs from imported game metadata or older cache versions."""
    if recipe.get('verified')=='local_game_data':
        result='Рецепт из игровых файлов.' if lang=='ru' else 'Recipe from game files.'
        if recipe.get('unlock_condition')=='objective_reward':
            result+=(' Производство открывается после выполнения задания.' if lang=='ru'
                     else ' Crafting unlocks after a mission.')
        return result
    return text_value(recipe.get('notes'),lang)

def text_value(value, lang='ru'):
    return value.get(lang, value.get('en', '')) if isinstance(value, dict) else str(value or '')

def cargo_slots(cid):
    entry=CARGO.get(ALIASES.get(cid,cid))
    return entry.get('slots') if entry else None

def calculate_load(items):
    """Return occupied standard cargo slots; error on non-standard loads."""
    total=0
    for cid, qty in items:
        slots=cargo_slots(cid)
        if slots is None:
            raise ValueError(f'No standard cargo slot size: {cid}')
        if not isinstance(qty,int) or isinstance(qty,bool) or qty<1:
            raise ValueError(f'Invalid quantity: {qty}')
        total+=slots*qty
    return total

def validate_recipe(recipe):
    if not isinstance(recipe,dict): raise ValueError('Not a recipe object')
    name=recipe.get('name')
    if not text_value(name,'ru').strip(): raise ValueError('Recipe name is required')
    if not str(recipe.get('region','')).strip(): raise ValueError('Region is required')
    ins,outs=recipe.get('inputs'),recipe.get('outputs')
    if not isinstance(ins,dict) or not isinstance(outs,dict) or not outs:
        raise ValueError('Inputs and outputs must be objects, outputs cannot be empty')
    for key,value in list(ins.items())+list(outs.items()):
        if key not in CARGO and key not in ALIASES:
            raise ValueError(f'Unknown cargo ID: {key}')
        if not isinstance(value,int) or isinstance(value,bool) or value<1:
            raise ValueError(f'Invalid quantity for {key}: {value}')
    if not ins and not recipe.get('generator'):
        raise ValueError('Empty inputs require a generator flag')
    return True

def load_custom():
    result=load_json(CUSTOM_FILE, [])
    return result if isinstance(result,list) else []

def load_game_recipes():
    entries=load_json(IMPORTED_FILE, [])
    if not isinstance(entries,list): return []
    result=[]
    for recipe in entries:
        try: validate_recipe(recipe)
        except (ValueError,TypeError,KeyError): continue
        if recipe.get('verified')=='local_game_data':result.append(recipe)
    return result

def all_recipes():
    return BUILTIN_RECIPES + load_game_recipes() + load_custom()


def filter_recipes(recipes, region='', query='', lang='ru'):
    q=query.casefold().strip()
    result=[]
    for recipe in recipes:
        if region and recipe.get('region')!=region: continue
        fields=[text_value(recipe.get('name'),lang),text_value(recipe.get('name'),'en'),
                display_recipe_location(recipe,lang),display_region(recipe.get('region',''),'en')]
        for cid in {*recipe.get('inputs',{}),*recipe.get('outputs',{})}:
            fields += [display_cargo(cid,'ru'),display_cargo(cid,'en')]
        if q and q not in ' '.join(fields).casefold(): continue
        result.append(recipe)
    return result

# The sorting modes are stable identifiers stored in the user's settings.json.
SORT_MODES = ('name_asc', 'name_desc', 'slots_asc', 'slots_desc')
_RU_ALPHA = {ch: i for i, ch in enumerate('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')}


def _sort_name(entry, lang):
    """Locale-independent, case-insensitive names (including correct Russian Ё order)."""
    name = str(entry.get(lang) or entry.get('en') or entry['id']).casefold()
    if lang == 'ru':
        return tuple((0, _RU_ALPHA[c]) if c in _RU_ALPHA else (1, ord(c)) for c in name)
    return name


def sort_cargo(entries, mode='name_asc', lang='ru'):
    """Sort copies of cargo entries, keeping loads without standard slots last.

    Equal-size cargo items always retain an ascending alphabetical tie-breaker,
    even for descending size order. No modifications to the input collection.
    """
    if mode not in SORT_MODES:
        mode = 'name_asc'
    if lang not in ('ru', 'en'):
        lang = 'ru'
    if mode.startswith('name_'):
        return sorted(entries, key=lambda x: (_sort_name(x, lang), x['id']),
                      reverse=(mode == 'name_desc'))
    sign = 1 if mode == 'slots_asc' else -1
    return sorted(entries, key=lambda x: (
        x.get('slots') is None,
        (x.get('slots') or 0) * sign,
        _sort_name(x, lang), x['id']))
