"""Interactive installer-path selection UI preview only; actual installer uses Inno Setup.

This window does not install anything. Run to preview the proposed directory-selection
step and test the Browse button before compiling the native Windows setup executable.
"""
from pathlib import Path
import os
import sys
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

BASE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1120, 720
OUT = Path(sys.argv[1]) if len(sys.argv)>1 else None
BASECOL = '#081821'
PANEL = '#09212B'
INPUT = '#102E39'
STROKE = '#22505B'
TEXT = '#F1F6F6'
MUTED = '#91B1BC'
GOLD = '#FFC521'

root=tk.Tk()
root.title('SnowRunner Helper — установщик (предварительный просмотр)')
root.geometry(f'{WIDTH}x{HEIGHT}+90+60')
root.resizable(False,False)
root.configure(bg=BASECOL)
root.update_idletasks()

head=Image.open(BASE/'assets/ui/v24_approved_header.png').convert('RGB')
head=head.resize((WIDTH,78),Image.Resampling.LANCZOS)
img=ImageTk.PhotoImage(head)
header=tk.Label(root,image=img,bg=BASECOL,bd=0)
header.place(x=0,y=0,width=WIDTH,height=78)

# Horizontal separation
separator=tk.Frame(root,bg=STROKE)
separator.place(x=0,y=78,width=WIDTH,height=2)

left=tk.Frame(root,bg='#081A24',width=286,height=640)
left.place(x=0,y=80)
left.pack_propagate(False)
sep=tk.Frame(root,bg=STROKE)
sep.place(x=286,y=80,width=2,height=640)

def label(parent, txt, x,y, fontsize=14, fg=TEXT, bold=False, bg=None):
    o=tk.Label(parent,text=txt,fg=fg,bg=bg or parent.cget('bg'),font=('DejaVu Sans',fontsize,'bold' if bold else 'normal'),anchor='w',justify='left',bd=0)
    o.place(x=x,y=y);return o
label(left,'ЭТАПЫ УСТАНОВКИ',22,35,15,GOLD,True)
steps=['Приветствие','Выбор папки','Дополнительно','Установка','Завершение']
for i,step in enumerate(steps):
    y=107+i*70
    if i==1:
        f=tk.Frame(left,bg='#163643',highlightbackground=GOLD,highlightthickness=1)
        f.place(x=16,y=y-10,width=254,height=56)
        lab=tk.Label(left,text='02',font=('DejaVu Sans',17,'bold'),fg=GOLD,bg='#163643');lab.place(x=30,y=y)
        label(left,step,82,y+3,15,TEXT,True,bg='#163643')
    else:
        label(left,f'0{i+1}',30,y,17,MUTED)
        label(left,step,82,y+3,15,MUTED)

label(left,'БЕЗОПАСНАЯ УСТАНОВКА',22,531,10,'#74CEB8',True)
label(left,'Данные профилей и файлы',22,552,11,MUTED)
label(left,'игры не изменяются',22,574,11,MUTED)

main=tk.Frame(root,bg=BASECOL)
main.place(x=288,y=80,width=WIDTH-288,height=640)
label(main,'ВЫБОР ПАПКИ УСТАНОВКИ',42,39,26,TEXT,True)
label(main,'Укажите, куда установить SnowRunner Helper.',42,96,14,MUTED)

panel=tk.Frame(main,bg=PANEL,highlightthickness=1,highlightbackground=STROKE)
panel.place(x=42,y=166,width=746,height=284)
label(panel,'Расположение приложения',23,22,17,TEXT,True)
label(panel,'Можно выбрать другой диск или любую доступную папку.',23,59,12,MUTED)

path_default=os.path.join('%LOCALAPPDATA%','Programs','SnowRunner Helper')
path_value=tk.StringVar(value=path_default)
path_entry=tk.Entry(panel,textvariable=path_value,font=('DejaVu Sans',12),fg=TEXT,bg=INPUT,insertbackground=GOLD,relief='flat',bd=8,highlightthickness=1,highlightbackground=STROKE,highlightcolor=GOLD)
path_entry.place(x=23,y=104,width=553,height=55)

def browse():
    selected=filedialog.askdirectory(title='Выберите папку установки')
    if selected:
        path_value.set(selected)
        status.configure(text='Выбранная папка: '+selected)

browse_button=tk.Button(panel,text='Обзор…',font=('DejaVu Sans',14,'bold'),fg='#09212B',bg=GOLD,activebackground='#E4AF11',relief='flat',bd=0,command=browse)
browse_button.place(x=587,y=104,width=132,height=55)
status=tk.Label(panel,text='Папку можно изменить вручную или через кнопку «Обзор…».',fg='#7FD0BC',bg=PANEL,font=('DejaVu Sans',11),anchor='w')
status.place(x=23,y=182,width=694)
label(panel,'Установка: для текущего пользователя · без прав администратора',23,224,11,MUTED)

label(main,'При обновлении установщик предложит ранее выбранную папку.',42,477,12,MUTED)
label(main,'Размер установленных файлов будет известен после сборки EXE.',42,503,12,MUTED)

border=tk.Frame(main,bg=STROKE);border.place(x=0,y=555,width=832,height=1)
label(main,'v25  ·  ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР',42,576,10,MUTED,True)

btn_prev=tk.Button(main,text='‹  Назад',font=('DejaVu Sans',13),fg=TEXT,bg=INPUT,activebackground=INPUT,relief='flat',bd=0)
btn_prev.place(x=413,y=568,width=109,height=45)
btn_next=tk.Button(main,text='Далее  ›',font=('DejaVu Sans',13,'bold'),fg=BASECOL,bg=GOLD,activebackground='#E4AF11',relief='flat',bd=0)
btn_next.place(x=536,y=568,width=120,height=45)
btn_cancel=tk.Button(main,text='Отмена',font=('DejaVu Sans',13),fg=TEXT,bg=INPUT,activebackground=INPUT,relief='flat',bd=0,command=root.destroy)
btn_cancel.place(x=669,y=568,width=109,height=45)
root.update()

if OUT:
    def capture():
        from PIL import ImageGrab
        x,y=root.winfo_rootx(), root.winfo_rooty()
        im=ImageGrab.grab(bbox=(x,y,x+WIDTH,y+HEIGHT))
        OUT.parent.mkdir(parents=True,exist_ok=True)
        im.save(OUT)
        print('SAVED',OUT,im.size)
        root.destroy()
    root.after(550,capture)
root.mainloop()
