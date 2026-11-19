"""Windows private font loader and language-aware font selection.

User-provided TTF/OTF files are copied to the user's own directory and
registered only for the running process; Windows system fonts are untouched.
"""
import ctypes
import os
import re
import shutil
from pathlib import Path
from core import USER_DIR

FONT_DIR = USER_DIR / 'fonts'
FONT_DIR.mkdir(parents=True, exist_ok=True)
SUPPORTED = {'.ttf', '.otf'}
EXAMPLES = {'cyrillic': 'Привет АБВ Ёж', 'latin': 'SnowRunner Craft ABC'}


def inspect_font(path, script):
    """Return family name only after verifying a file and its required glyphs."""
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError('Выберите шрифт TTF или OTF / Choose a TTF or OTF font')
    if path.stat().st_size > 35_000_000:
        raise ValueError('Слишком большой файл шрифта (макс. 35 МБ)')
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        # Pillow is required by the interface already. Its FreeType backend
        # can validate TTF/OTF when an external EXE was built without fonttools.
        # Glyph checks use an unknown-codepoint mask as a best-effort fallback.
        try:
            from PIL import ImageFont
            face=ImageFont.truetype(str(path),size=38)
            blank=face.getmask('\U0010FFFF')
            missing=[]
            for char in EXAMPLES[script]:
                if char==' ':continue
                glyph=face.getmask(char)
                if (glyph.size==blank.size and glyph.tobytes()==blank.tobytes()):
                    missing.append(char)
            if missing:
                raise ValueError('В выбранном шрифте отсутствуют символы: '+''.join(dict.fromkeys(missing)))
            return face.getname()[0] or path.stem
        except ValueError:raise
        except Exception as exc:
            raise ValueError('Не удалось прочитать шрифт TTF/OTF / Cannot read font') from exc
    try:
        f = TTFont(str(path), lazy=False)
        try:
            cmap = set()
            for table in f['cmap'].tables:
                if table.isUnicode():cmap.update(table.cmap)
            sample = EXAMPLES[script]
            missing=[c for c in sample if c!=' ' and ord(c) not in cmap]
            if missing:
                raise ValueError('В выбранном шрифте отсутствуют символы: '+''.join(dict.fromkeys(missing)))
            names=f['name']
            return (names.getDebugName(16) or names.getDebugName(1) or path.stem).strip()
        finally:f.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Не удалось прочитать шрифт TTF/OTF') from exc


class FontManager:
    def __init__(self, config):
        self.config=config
        self.families={}
        self.loaded_paths=set()
        for script in ('cyrillic','latin'):
            path=config.get('font_'+script,'')
            if path and Path(path).is_file():
                try:self._register(Path(path),script)
                except Exception:pass

    def _register(self,path,script):
        family=inspect_font(path,script)
        if os.name=='nt' and str(path) not in self.loaded_paths:
            # FR_PRIVATE: usable by Tk in this process; not installed globally.
            count=ctypes.windll.gdi32.AddFontResourceExW(str(path),0x10,None)
            if not count:raise RuntimeError('Windows не удалось подключить выбранный шрифт')
        self.loaded_paths.add(str(path))
        self.families[script]=family
        return family

    def install(self,filename,script):
        if script not in EXAMPLES:raise ValueError('Invalid script')
        src=Path(filename).resolve()
        family=inspect_font(src,script)
        # Keep a local managed copy instead of relying on removable drives.
        dest=FONT_DIR / (script + '_' + re.sub(r'[^A-Za-z0-9._-]','_',src.stem)[:64] + src.suffix.lower())
        if src!=dest:shutil.copy2(src,dest)
        try:family=self._register(dest,script)
        except Exception:
            if src!=dest:dest.unlink(missing_ok=True)
            raise
        self.config['font_'+script]=str(dest)
        return family

    def reset(self,script):
        self.config['font_'+script]=''
        self.families.pop(script,None)

    def family(self,text='',language='ru'):
        s=str(text)
        if re.search('[\u0400-\u052f]',s):script='cyrillic'
        elif re.search('[A-Za-z]',s):script='latin'
        else:script='cyrillic' if language=='ru' else 'latin'
        return self.families.get(script,'Segoe UI')

    def label(self,script):
        return self.families.get(script,'Segoe UI (по умолчанию)' if self.config.get('lang')=='ru' else 'Segoe UI (default)')
