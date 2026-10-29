"""Data Access: SQLite connection and database initialization."""
import os
import sqlite3
from contextlib import contextmanager
ROOT=os.path.dirname(os.path.abspath(__file__))
class Database:
    def __init__(self,path=None): self.path=path or os.path.join(ROOT,"vet_clinic.db")
    @contextmanager
    def connect(self):
        """Yield a configured connection and always close it after the transaction."""
        con=sqlite3.connect(self.path,timeout=10)
        con.row_factory=sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
    def initialize(self):
        from business_logic import password_hash
        with self.connect() as con:
            with open(os.path.join(ROOT,"schema.sql"),encoding="utf-8") as f: con.executescript(f.read())
            with open(os.path.join(ROOT,"vet_clinic_triggers.sql"),encoding="utf-8") as f: con.executescript(f.read())
            for login,password,name,role in (("admin","admin123","Администратор","admin"),("user","user123","Демо-пользователь","user")):
                if not con.execute("SELECT 1 FROM Users WHERE Login=?",(login,)).fetchone():
                    con.execute("INSERT INTO Users(Login,PasswordHash,FullName,Role) VALUES(?,?,?,?)",(login,password_hash(password),name,role))
            if not con.execute("SELECT 1 FROM Products LIMIT 1").fetchone():
                con.executemany("INSERT INTO Products(ProductName,Price,Stock) VALUES(?,?,?)",[
                    ("Корм для кошек 1 кг",12.50,30),("Лакомства для собак",5.90,25),("Шампунь для животных",8.20,12)])
    def query(self,sql,params=()):
        with self.connect() as con: return [tuple(r) for r in con.execute(sql,params).fetchall()]
