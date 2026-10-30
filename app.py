import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from business_logic import ClinicService
from data_access import Database

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ВетКлиника — запись и забота о питомцах"); self.geometry("900x620")
        try:
            self.db=Database(); self.db.initialize(); self.service=ClinicService(self.db)
        except Exception as e:
            messagebox.showerror("Ошибка БД",f"Не удалось создать базу данных.\\n{e}"); self.destroy(); return
        self.user=None; self.login_screen()
    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def login_screen(self):
        self.clear(); box=ttk.Frame(self,padding=35); box.pack(expand=True)
        ttk.Label(box,text="Ветеринарная клиника",font=("Segoe UI",20,"bold")).pack(pady=10)
        ttk.Label(box,text="Логин").pack(anchor="w")
        self.login=ttk.Entry(box,width=32); self.login.pack(pady=4)
        ttk.Label(box,text="Пароль").pack(anchor="w")
        self.password=ttk.Entry(box,width=32,show="*"); self.password.pack(pady=4)
        ttk.Button(box,text="Войти",command=self.do_login).pack(fill="x",pady=12)
        ttk.Label(box,text="Демо: admin / admin123  |  user / user123").pack()
        self.password.bind("<Return>",lambda e:self.do_login())
    def do_login(self):
        try:
            self.user=self.service.login(self.login.get().strip(),self.password.get())
            if not self.user: raise ValueError("Неверный логин или пароль.")
            self.home()
        except Exception as e: messagebox.showerror("Вход",str(e))
    def home(self):
        self.clear(); top=ttk.Frame(self,padding=10); top.pack(fill="x")
        ttk.Label(top,text=f"Здравствуйте, {self.user['name']} ({self.user['role']})",font=("Segoe UI",12,"bold")).pack(side="left")
        ttk.Button(top,text="Выйти",command=self.login_screen).pack(side="right")
        self.pet_choice_widgets=[]
        tabs=ttk.Notebook(self); tabs.pack(fill="both",expand=True,padx=10,pady=10)
        self.make_pets(tabs); self.make_appointments(tabs); self.make_vaccines(tabs); self.make_shop(tabs)
        if self.user["role"]=="admin": self.make_reports(tabs); self.make_audit(tabs)
    def tree_tab(self,tabs,title,cols):
        frame=ttk.Frame(tabs,padding=10); tabs.add(frame,text=title)
        tree=ttk.Treeview(frame,columns=cols,show="headings",height=13)
        for c in cols: tree.heading(c,text=c); tree.column(c,width=125)
        tree.pack(fill="both",expand=True); return frame,tree
    def make_pets(self,tabs):
        f,t=self.tree_tab(tabs,"Мои питомцы",("ID","Кличка","Вид","Порода","Возраст"))
        row=ttk.Frame(f); row.pack(fill="x",pady=8)
        name=ttk.Entry(row,width=18); name.insert(0,"Кличка")
        species=ttk.Combobox(row,values=("Кошка","Собака","Другое"),width=12,state="readonly"); species.set("Кошка")
        breed=ttk.Entry(row,width=16); breed.insert(0,"Порода")
        age=ttk.Entry(row,width=8); age.insert(0,"0")
        for w in (name,species,breed,age): w.pack(side="left",padx=3)
        def refresh():
            t.delete(*t.get_children())
            for r in self.service.pets(self.user["id"]): t.insert("","end",values=tuple(r))
        def add():
            try:
                self.service.add_pet(self.user["id"],name.get(),species.get(),breed.get(),age.get())
                refresh(); self.refresh_pet_choices()
            except Exception as e: messagebox.showerror("Питомец",str(e))
        ttk.Button(row,text="Добавить питомца",command=add).pack(side="left",padx=5); refresh()
    def pet_choices(self): return self.service.pets(self.user["id"])
    def refresh_pet_choices(self):
        values=[f"{p[0]} — {p[1]}" for p in self.pet_choices()]
        for combo in self.pet_choice_widgets:
            combo.configure(values=values)
            if values and not combo.get(): combo.current(0)
            elif not values: combo.set("")
    def make_appointments(self,tabs):
        f,t=self.tree_tab(tabs,"Приём",("ID","Питомец","Дата и время","Причина","Статус"))
        row=ttk.Frame(f); row.pack(fill="x",pady=8); pets=self.pet_choices()
        choice=ttk.Combobox(row,values=[f"{p[0]} — {p[1]}" for p in pets],width=22,state="readonly")
        if pets: choice.current(0)
        self.pet_choice_widgets.append(choice)
        dt=ttk.Entry(row,width=20); dt.insert(0,(datetime.now()+timedelta(days=3)).replace(second=0,microsecond=0).strftime("%Y-%m-%d %H:%M"))
        reason=ttk.Entry(row,width=22); reason.insert(0,"Осмотр")
        for w in (choice,dt,reason): w.pack(side="left",padx=3)
        def refresh():
            t.delete(*t.get_children())
            for r in self.service.appointments(self.user["id"],"Приём"): t.insert("","end",values=tuple(r))
        def add():
            try:
                if not choice.get(): raise ValueError("Сначала добавьте питомца.")
                self.service.book(self.user["id"],int(choice.get().split(" — ")[0]),dt.get().strip(),reason.get().strip(),"Приём")
                refresh(); messagebox.showinfo("Запись","Запись создана.")
            except Exception as e: messagebox.showerror("Запись",str(e))
        ttk.Button(row,text="Записаться",command=add).pack(side="left",padx=5); refresh()
    def make_vaccines(self,tabs):
        f,t=self.tree_tab(tabs,"Прививки",("ID","Питомец","Дата и время","Причина","Статус"))
        row=ttk.Frame(f); row.pack(fill="x",pady=8); pets=self.pet_choices()
        choice=ttk.Combobox(row,values=[f"{p[0]} — {p[1]}" for p in pets],width=22,state="readonly")
        if pets: choice.current(0)
        self.pet_choice_widgets.append(choice)
        dt=ttk.Entry(row,width=20); dt.insert(0,(datetime.now()+timedelta(days=4)).replace(second=0,microsecond=0).strftime("%Y-%m-%d %H:%M"))
        vaccine=ttk.Entry(row,width=22); vaccine.insert(0,"Комплексная вакцина")
        for w in (choice,dt,vaccine): w.pack(side="left",padx=3)
        def refresh():
            t.delete(*t.get_children())
            for r in self.service.appointments(self.user["id"],"Прививка"): t.insert("","end",values=tuple(r))
        def add():
            try:
                if not choice.get(): raise ValueError("Сначала добавьте питомца.")
                self.service.book(self.user["id"],int(choice.get().split(" — ")[0]),dt.get().strip(),vaccine.get().strip(),"Прививка")
                refresh(); messagebox.showinfo("Прививка","Запись на прививку создана.")
            except Exception as e: messagebox.showerror("Прививка",str(e))
        ttk.Button(row,text="Записаться на прививку",command=add).pack(side="left",padx=5); refresh()
    def make_shop(self,tabs):
        f,t=self.tree_tab(tabs,"Магазин",("ID","Товар","Цена","Остаток"))
        row=ttk.Frame(f); row.pack(fill="x",pady=8); products=self.service.products()
        choice=ttk.Combobox(row,values=[f"{p[0]} — {p[1]} ({p[2]})" for p in products],width=40,state="readonly")
        if products: choice.current(0)
        qty=ttk.Entry(row,width=6); qty.insert(0,"1")
        choice.pack(side="left",padx=4); qty.pack(side="left",padx=4)
        def refresh():
            t.delete(*t.get_children())
            for r in self.service.products(): t.insert("","end",values=tuple(r))
        def buy():
            try:
                if not choice.get(): raise ValueError("Нет доступных товаров.")
                self.service.buy(self.user["id"],int(choice.get().split(" — ")[0]),qty.get())
                refresh(); messagebox.showinfo("Покупка","Покупка оформлена.")
            except Exception as e: messagebox.showerror("Покупка",str(e))
        ttk.Button(row,text="Купить",command=buy).pack(side="left",padx=4); refresh()
    def make_reports(self,tabs):
        f,t=self.tree_tab(tabs,"Отчёты администратора",("Показатель","Значение"))
        def refresh():
            t.delete(*t.get_children())
            for r in self.service.report(): t.insert("","end",values=tuple(r))
        ttk.Button(f,text="Обновить отчёт",command=refresh).pack(anchor="w",pady=8); refresh()
    def make_audit(self,tabs):
        f,t=self.tree_tab(tabs,"Аудит",("ID","Таблица","Операция","Пользователь","Дата","Данные"))
        def refresh():
            t.delete(*t.get_children())
            for r in self.service.audit(): t.insert("","end",values=tuple(r))
        ttk.Button(f,text="Обновить журнал",command=refresh).pack(anchor="w",pady=8); refresh()
if __name__=="__main__": App().mainloop()
