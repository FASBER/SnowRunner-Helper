"""Friendly Tkinter recipe editor; never asks the player for JSON or cargo IDs."""
import tkinter as tk
from tkinter import ttk, messagebox
import uuid
from core import (CARGO, CARGO_DB, REGIONS, CUSTOM_FILE, save_json,
                  display_cargo, display_region, display_recipe_notes, text_value, validate_recipe)


class RecipeEditor(tk.Toplevel):
    def __init__(self, app, base=None, copy=False):
        super().__init__(app.root)
        self.app = app
        self.base = base
        self.original = base if base in app.custom and not copy else None
        self.lang = app.config['lang']
        self.ru = self.lang == 'ru'
        self.t = lambda ru, en: ru if self.ru else en
        self.title(self.t('Добавить рецепт крафта', 'Add crafting recipe') if not self.original
                   else self.t('Изменить рецепт', 'Edit crafting recipe'))
        self.geometry('870x810')
        self.minsize(750, 680)
        self.configure(bg=app.c('bg'))
        self.transient(app.root)
        self.grab_set()
        self.entries = {}
        self.materials = []
        self.cargo_list = sorted(CARGO_DB, key=lambda c: c.get(self.lang, c['en']).casefold())
        self.cargo_labels = [display_cargo(c['id'], self.lang) for c in self.cargo_list]
        self.id_by_label = dict(zip(self.cargo_labels, (c['id'] for c in self.cargo_list)))
        self.label_by_id = {cid:label for label,cid in self.id_by_label.items()}
        self.build()

    def label(self, parent, text, **kw):
        opts={'bg':self.app.c('panel'),'fg':self.app.c('fg'),
              'font':(self.app.ui_font_family(text),self.app.sized(11))}
        opts.update(kw)
        return tk.Label(parent, text=text, **opts)

    def block(self, parent):
        return tk.Frame(parent, bg=self.app.c('panel'))

    def field(self, parent, title, key, default=''):
        self.label(parent, title, anchor='w').pack(fill='x', pady=(10, 3))
        var = tk.StringVar(value=default)
        edit = self.app.ent(parent, var)
        edit.pack(fill='x', ipady=5)
        self.entries[key] = var
        return var

    def build(self):
        outer = tk.Frame(self, bg=self.app.c('panel'))
        outer.pack(fill='both', expand=True, padx=16, pady=16)
        header = self.label(outer, self.t('НОВЫЙ РЕЦЕПТ', 'NEW RECIPE'),
                            font=(self.app.ui_font_family(), self.app.sized(17), 'bold'))
        header.pack(anchor='w', padx=19, pady=(14, 2))
        self.label(outer, self.t('Выбери материалы и количество — никаких кодов и JSON.',
                                'Choose materials and amounts — no codes or JSON.'),
                   fg=self.app.c('muted')).pack(anchor='w', padx=19, pady=(0, 10))
        # The footer is sticky, while the form scrolls on smaller laptop screens.
        buttons=tk.Frame(outer,bg=self.app.c('panel'))
        buttons.pack(side='bottom',anchor='e',fill='x',padx=19,pady=13)
        self.app.btn(buttons,self.t('Сохранить рецепт','Save recipe'),self.save,primary=True).pack(side='right',padx=(10,0))
        self.app.btn(buttons,self.t('Отмена','Cancel'),self.destroy).pack(side='right')
        holder=tk.Frame(outer,bg=self.app.c('panel'))
        holder.pack(fill='both',expand=True,padx=19,pady=(0,5))
        canvas=tk.Canvas(holder,bg=self.app.c('panel'),highlightthickness=0)
        scroll=ttk.Scrollbar(holder,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True)
        content=tk.Frame(canvas,bg=self.app.c('panel'))
        canvas.create_window((0,0),window=content,anchor='nw',tags='form_body')
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure('form_body',width=e.width))
        content.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        self.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-int(e.delta/120) or (1 if e.delta<0 else -1),'units'))
        self.bind('<Button-4>',lambda e:canvas.yview_scroll(-1,'units'))
        self.bind('<Button-5>',lambda e:canvas.yview_scroll(1,'units'))
        self.field(content, self.t('1. Название рецепта (можно не заполнять)',
                                   '1. Recipe name (optional)'), 'name',
                   text_value(self.base.get('name'), self.lang) if self.base else '')
        regions = [(display_region(code, self.lang), code) for code in REGIONS if code not in ('user_chart', 'game_files')]
        regions.append((self.t('Мой регион', 'My region'), 'custom'))
        self.region_names = dict(regions)
        self.region_values = {v:k for k,v in regions}
        old_region = (self.base or {}).get('region', 'custom')
        old_region = old_region if old_region in self.region_values else 'custom'
        self.label(content,self.t('2. Выбери регион', '2. Select region'),anchor='w').pack(fill='x',pady=(10,3))
        self.region_var = tk.StringVar(value=self.region_values[old_region])
        self.reg_combo = ttk.Combobox(content, values=list(self.region_names), state='readonly',
                                      textvariable=self.region_var, style='Dashboard.TCombobox')
        self.reg_combo.pack(fill='x', ipady=4)
        map_value = (self.base or {}).get('map', '')
        # A copied game recipe already selects its map via the dropdown; never
        # prefill an internal filename into the visible free-text location field.
        if str(map_value).startswith(('level_ru_', 'level_us_', 'RU_', 'US_')):
            map_value = ''
        self.field(content, self.t('Карта / завод / место (необязательно)',
                                   'Map / factory / place (optional)'), 'map', map_value)
        self.label(content,self.t('3. Что потребуется для производства',
                                   '3. Materials needed'),anchor='w').pack(fill='x',pady=(13,3))
        self.input_rows = self.block(content)
        self.input_rows.pack(fill='x')
        self.app.btn(content,self.t('+ Добавить материал', '+ Add material'),
                     lambda:self.add_material('input')).pack(anchor='w',pady=(4,4))
        self.label(content,self.t('4. Что получится после крафта',
                                   '4. Crafting result'),anchor='w').pack(fill='x',pady=(11,3))
        self.output_rows = self.block(content)
        self.output_rows.pack(fill='x')
        self.app.btn(content,self.t('+ Добавить результат', '+ Add result'),
                     lambda:self.add_material('output')).pack(anchor='w',pady=(4,4))
        self.generator_var=tk.BooleanVar(value=bool((self.base or {}).get('generator', False)))
        tk.Checkbutton(content,text=self.t('Нужен генератор / энергия', 'Requires generator / energy'),
                       variable=self.generator_var,bg=self.app.c('panel'),fg=self.app.c('fg'),
                       selectcolor=self.app.c('input'),activebackground=self.app.c('panel'),
                       activeforeground=self.app.c('fg'),
                       command=self.update_preview).pack(anchor='w',pady=(8,0))
        self.field(content,self.t('Примечание (необязательно)', 'Notes (optional)'), 'notes',
                   display_recipe_notes(self.base, self.lang) if self.base else '')
        self.label(content,self.t('ПРЕДПРОСМОТР', 'LIVE PREVIEW'),anchor='w').pack(fill='x',pady=(12,4))
        self.preview=tk.Label(content,text='',anchor='w',justify='left',wraplength=770,
                              bg=self.app.c('raised'),fg=self.app.c('accent'),padx=12,pady=11,
                              font=(self.app.ui_font_family(),self.app.sized(11),'bold'))
        self.preview.pack(fill='x')
        for cid,qty in (self.base or {}).get('inputs',{}).items(): self.add_material('input',cid,qty)
        for cid,qty in (self.base or {}).get('outputs',{}).items(): self.add_material('output',cid,qty)
        if not self.materials:
            self.add_material('input','metal_rolls',1)
            self.add_material('output','metal_beams',1)
        self.update_preview()

    def add_material(self, direction, cid=None, qty=1):
        parent = self.input_rows if direction=='input' else self.output_rows
        row=self.block(parent)
        row.pack(fill='x',pady=3)
        var=tk.StringVar(value=self.label_by_id.get(cid,self.cargo_labels[0]))
        combo=ttk.Combobox(row,textvariable=var,values=self.cargo_labels,state='readonly',
                           style='Dashboard.TCombobox',width=56)
        combo.pack(side='left',fill='x',expand=True)
        self.label(row, ' × ').pack(side='left')
        qvar=tk.StringVar(value=str(qty))
        spin=tk.Spinbox(row,from_=1,to=999,textvariable=qvar,width=5,
                        bg=self.app.c('input'),fg=self.app.c('fg'),
                        buttonbackground=self.app.c('raised'),relief='flat')
        spin.pack(side='left',padx=(0,9))
        entry={'row':row,'direction':direction,'cargo':var,'qty':qvar}
        self.materials.append(entry)
        self.app.btn(row,self.t('Убрать','Remove'),lambda:self.remove_material(entry)).pack(side='left')
        combo.bind('<<ComboboxSelected>>',lambda e:self.update_preview())
        qvar.trace_add('write',lambda *_:self.update_preview())
        self.update_preview()

    def remove_material(self,entry):
        self.materials.remove(entry)
        entry['row'].destroy()
        self.update_preview()

    def build_parts(self):
        inputs,outputs={},{}
        for item in self.materials:
            cid=self.id_by_label.get(item['cargo'].get())
            if not cid:
                raise ValueError(self.t('Выбери груз из списка.', 'Choose a cargo from the list.'))
            try:count=int(item['qty'].get())
            except ValueError:count=0
            if count < 1 or count > 999:
                raise ValueError(self.t('Количество должно быть от 1 до 999.', 'Quantity must be from 1 to 999.'))
            target=inputs if item['direction']=='input' else outputs
            target[cid]=target.get(cid,0)+count
        return inputs,outputs

    def update_preview(self):
        if not hasattr(self,'preview'):return
        try:
            inputs,outputs=self.build_parts()
            def fmt(items): return ' + '.join(f'{n} × {display_cargo(cid,self.lang)}' for cid,n in items.items())
            inp=fmt(inputs) or (self.t('Генератор','Generator') if self.generator_var.get() else '—')
            out=fmt(outputs) or '—'
            self.preview.configure(text=inp+'\n   ↓\n'+out)
        except (ValueError,tk.TclError):
            self.preview.configure(text=self.t('Проверь количество грузов', 'Check amounts'))

    def save(self):
        try:
            ins,outs=self.build_parts()
            if not outs:
                raise ValueError(self.t('Добавь хотя бы один результат крафта.', 'Add at least one output.'))
            if not ins and not self.generator_var.get():
                raise ValueError(self.t('Добавь исходный материал или включи генератор.',
                                        'Add an input or enable generator.'))
            name=self.entries['name'].get().strip() or self.t(
                'Производство: '+', '.join(display_cargo(cid,'ru') for cid in outs),
                'Craft: '+', '.join(display_cargo(cid,'en') for cid in outs))
            # The same typed name is used in both languages for user text.
            new={'id':self.original['id'] if self.original else 'user-'+uuid.uuid4().hex[:12],
                 'name':{'ru':name,'en':name},
                 'region':self.region_names[self.region_var.get()],
                 'map':self.entries['map'].get().strip(),
                 'inputs':ins,'outputs':outs,'generator':self.generator_var.get(),
                 'notes':{'ru':self.entries['notes'].get().strip(),
                          'en':self.entries['notes'].get().strip()},
                 'verified':'user_created'}
            validate_recipe(new)
            # User-made recipes are never labeled official.
        except (ValueError,KeyError) as exc:
            messagebox.showerror(self.t('Ошибка рецепта','Recipe error'),str(exc),parent=self)
            return
        if self.original is None:self.app.custom.append(new)
        else:self.app.custom[self.app.custom.index(self.original)]=new
        save_json(CUSTOM_FILE,self.app.custom)
        self.app.selected_recipe=new
        self.destroy()
        self.app.render()
