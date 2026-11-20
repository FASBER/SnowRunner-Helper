"""Regression tests: explicit profile selection and visible Save control."""
from __future__ import annotations
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import profile_selector_v314 as selector

SLOTS = [
    {'profile_key': '1' * 20, 'platform_hint': 'Steam', 'slot': 1,
     'path': r'C:\Games\SnowRunner\CompleteSave.cfg'},
    {'profile_key': '2' * 20, 'platform_hint': 'Steam', 'slot': 2,
     'path': r'C:\Games\SnowRunner\CompleteSave1.cfg'},
    {'profile_key': '3' * 20, 'platform_hint': 'Steam', 'slot': 3,
     'path': r'C:\Games\SnowRunner\CompleteSave2.cfg'},
]

class FakeApp:
    colors = {'panel': '#19262D', 'input': '#202D35', 'fg': '#F5F2EC',
              'accent': '#FFBE1B', 'muted': '#A4B9C5',
              'selection': '#6A5420', 'stroke': '#40515B'}
    def __init__(self, root, saved=None):
        self.root=root
        self.config={'lang':'ru','selected_game_profile':saved or 'local'}
        self.active_profile_key=saved or 'local'
        self.saved=[]
        self.synced=[]
        self._last_profile_sync_issue=''
        self.profiles=types.SimpleNamespace(read=lambda key: {'game_snapshot': {'statistics':{'money':500}}})
    def c(self, key): return self.colors[key]
    def ui_font_family(self): return 'DejaVu Sans'
    def f(self,parent):return tk.Frame(parent,bg=self.c('panel'))
    def btn(self,parent,text,command,primary=False):
        return tk.Button(parent,text=text,command=command,bg=self.c('accent') if primary else '#2B414D',
                         fg='#17222A' if primary else '#FAF9F3',relief='flat',bd=0,
                         font=('DejaVu Sans',10,'bold' if primary else 'normal'),padx=9,pady=7)
    def _local_game_paths(self):return ([r'C:\Games\SnowRunner\initial.pak'],list(SLOTS))
    def _switch_profile(self,key,source=None):
        self.saved.append((key,source))
        self.active_profile_key=key
        self.config['selected_game_profile']=key
        return True
    def _sync_active_profile(self):
        self.synced.append(self.active_profile_key)
        return {'statistics':{'money':500}}
    def _snapshot_description(self, snapshot):return 'Тестовые данные профиля (синтетические)'
    def refresh_active_profile(self):return self._sync_active_profile()
    def view_saved_progress(self):pass
    def refresh_from_installed_game(self):pass
    def drafts_dialog(self):pass
    def warehouse_preview_dialog(self):pass
    def route_planner_dialog(self):pass
    def save_structure_dialog(self):pass

def fake_sources():
    core=types.ModuleType('core')
    core.SETTINGS_FILE=Path('/tmp/not-written.json')
    core.save_json=lambda path,cfg:None
    bridge=types.ModuleType('game_bridge')
    bridge.status_summary=lambda archives,slots,lang: (
      f'Установок SnowRunner: {len(archives)}\n'
      f'Слотов сохранений: {len(slots)}\n'
      'Игровые файлы находятся в режиме только чтения.\n'
      'Активный слот определяется только выбором пользователя.')
    return {'core':core,'game_bridge':bridge}

def children(parent):
    for child in parent.winfo_children():
        yield child
        yield from children(child)

def by_text(win, text):
    return next(item for item in children(win) if item.winfo_class()=='Button' and item.cget('text')==text)

@unittest.skipUnless(bool(__import__('os').environ.get('DISPLAY')), 'Needs Tk display (xvfb-run in CI)')
class ProfileDialogTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk()
        self.root.withdraw()
        self.app=FakeApp(self.root)
        self.patch=patch.dict(sys.modules,fake_sources())
        self.patch.start()
        self.msg1=patch('tkinter.messagebox.showinfo')
        self.msg2=patch('tkinter.messagebox.showwarning')
        self.msg3=patch('tkinter.messagebox.showerror')
        self.msg1.start();self.msg2.start();self.msg3.start()
        self.win=selector.game_connection_dialog(self.app)
        self.win.update_idletasks()
        self.listbox=next(item for item in children(self.win) if item.winfo_class()=='Listbox')
    def tearDown(self):
        self.msg3.stop();self.msg2.stop();self.msg1.stop();self.patch.stop()
        self.root.destroy()
    def test_slots_include_local_and_all_three_saves(self):
        self.assertEqual(self.listbox.size(),4)
        self.assertIn('локальный',self.listbox.get(0).lower())
        self.assertIn('слот 1',self.listbox.get(1))
        self.assertIn('слот 2',self.listbox.get(2))
        self.assertIn('слот 3',self.listbox.get(3))
    def test_select_only_does_not_switch(self):
        self.listbox.selection_clear(0,'end')
        self.listbox.selection_set(2)
        self.listbox.event_generate('<<ListboxSelect>>')
        self.assertEqual(self.app.active_profile_key,'local')
        self.assertEqual(self.app.saved,[])
        self.assertIn('Будет сохранён', [x.cget('text') for x in children(self.win) if x.winfo_class()=='Label'][-2])
    def test_save_button_explicitly_persists_chosen_slot(self):
        self.listbox.selection_clear(0,'end')
        self.listbox.selection_set(2)
        self.listbox.event_generate('<<ListboxSelect>>')
        by_text(self.win,'СОХРАНИТЬ ВЫБРАННЫЙ ПРОФИЛЬ').invoke()
        self.assertEqual(self.app.active_profile_key,SLOTS[1]['profile_key'])
        self.assertEqual(self.app.config['selected_game_profile'],SLOTS[1]['profile_key'])
        self.assertEqual(self.app.synced,[SLOTS[1]['profile_key']])
    def test_local_profile_can_be_saved_explicitly(self):
        self.listbox.selection_clear(0,'end')
        self.listbox.selection_set(0)
        by_text(self.win,'СОХРАНИТЬ ВЫБРАННЫЙ ПРОФИЛЬ').invoke()
        self.assertEqual(self.app.active_profile_key,'local')
        self.assertEqual(self.app.synced,[])
    def test_buttons_fully_visible_at_960x665(self):
        self.win.update()
        for text in ['СОХРАНИТЬ ВЫБРАННЫЙ ПРОФИЛЬ','Обновить список','Закрыть',
                     'Папка игры','Папка сохранений','Считать прогресс','Детали прогресса',
                     'Импорт рецептов','Черновики','Склады','Маршруты','Схема сохранения']:
            button=by_text(self.win,text)
            self.assertTrue(button.winfo_ismapped(),text)
            self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),
                                 self.win.winfo_rooty()+self.win.winfo_height(),text)
    def test_saved_slot_is_preselected_after_reopening(self):
        self.app.active_profile_key=SLOTS[2]['profile_key']
        self.app.config['selected_game_profile']=SLOTS[2]['profile_key']
        self.win.destroy()
        self.win=selector.game_connection_dialog(self.app)
        self.win.update_idletasks()
        lb=next(item for item in children(self.win) if item.winfo_class()=='Listbox')
        self.assertEqual(lb.curselection(),(3,))
    def test_rescan_does_not_save_pending_selection(self):
        self.listbox.selection_clear(0,'end')
        self.listbox.selection_set(2)
        by_text(self.win,'Обновить список').invoke()
        self.assertEqual(self.app.active_profile_key,'local')
        self.assertEqual(self.app.saved,[])
        self.assertEqual(self.listbox.curselection(),(2,))

class WiringTests(unittest.TestCase):
    def test_install_is_idempotent_and_script_compatible(self):
        cls=type('Application',(),{'game_connection_dialog':lambda self:None})
        main=types.SimpleNamespace(Application=cls)
        with patch.dict(sys.modules,{'__main__':main}):
            self.assertGreaterEqual(selector.install_profile_selector(),1)
            self.assertEqual(selector.install_profile_selector(),0)
        self.assertIs(cls.game_connection_dialog,selector.game_connection_dialog)
    def test_labels_never_infer_active_from_mtime(self):
        self.assertIn('слот 2',selector.label_for_slot(SLOTS[1]))
        self.assertIn('локальный',selector.label_for_slot(None).lower())
        self.assertNotIn('active',selector.label_for_slot(SLOTS[1],False).lower())

if __name__=='__main__':unittest.main()
