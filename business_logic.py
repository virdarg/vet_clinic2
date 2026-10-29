"""Business Logic: validation, authorization and transaction workflows."""
import hashlib,hmac,os
from datetime import datetime
from data_access import Database

def password_hash(password,salt=None):
    salt=salt or os.urandom(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),salt,180_000)
    return salt.hex()+"$"+digest.hex()
def verify_password(password,stored):
    try:
        salt,digest=stored.split("$",1)
        actual=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),bytes.fromhex(salt),180_000).hex()
        return hmac.compare_digest(actual,digest)
    except (ValueError,TypeError,AttributeError): return False

class ClinicService:
    def __init__(self,db:Database): self.db=db
    def login(self,login,password):
        rows=self.db.query("SELECT UserID,FullName,Role,PasswordHash FROM Users WHERE Login=?",(login,))
        if not rows or not verify_password(password,rows[0][3]): return None
        return {"id":rows[0][0],"name":rows[0][1],"role":rows[0][2]}
    def pets(self,user_id):
        return self.db.query("SELECT PetID,PetName,Species,COALESCE(Breed,''),Age FROM Pets WHERE OwnerID=? ORDER BY PetName",(user_id,))
    def add_pet(self,user_id,name,species,breed,age):
        name=name.strip(); species=species.strip()
        if not name: raise ValueError("Введите кличку.")
        if not species: raise ValueError("Выберите вид.")
        try: age=int(age)
        except (ValueError,TypeError): raise ValueError("Возраст должен быть целым числом.")
        if not 0<=age<=100: raise ValueError("Возраст должен быть от 0 до 100.")
        with self.db.connect() as con:
            con.execute("INSERT INTO Pets(OwnerID,PetName,Species,Breed,Age) VALUES(?,?,?,?,?)",(user_id,name,species,breed.strip() or None,age))
    def appointments(self,user_id,kind=None):
        sql="""SELECT a.AppointmentID,p.PetName,strftime('%Y-%m-%d %H:%M',a.StartAt),a.Reason,a.Status
        FROM Appointments a JOIN Pets p ON p.PetID=a.PetID
        WHERE a.OwnerID=? AND (? IS NULL OR a.Kind=?) ORDER BY a.StartAt"""
        return self.db.query(sql,(user_id,kind,kind))
    def book(self,user_id,pet_id,when,reason,kind):
        if not reason.strip(): raise ValueError("Заполните описание записи.")
        try: dt=datetime.strptime(when,"%Y-%m-%d %H:%M")
        except ValueError: raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД ЧЧ:ММ.")
        if dt<=datetime.now(): raise ValueError("Выберите дату и время в будущем.")
        if kind not in ("Приём","Прививка"): raise ValueError("Неизвестный тип записи.")
        with self.db.connect() as con:
            if not con.execute("SELECT 1 FROM Pets WHERE PetID=? AND OwnerID=?",(pet_id,user_id)).fetchone():
                raise ValueError("Можно записать только своего питомца.")
            con.execute("INSERT INTO Appointments(PetID,OwnerID,StartAt,Reason,Kind) VALUES(?,?,?,?,?)",(pet_id,user_id,dt.strftime("%Y-%m-%d %H:%M:%S"),reason.strip(),kind))
    def products(self):
        return self.db.query("SELECT ProductID,ProductName,Price,Stock FROM Products WHERE Active=1 ORDER BY ProductName")
    def buy(self,user_id,product_id,quantity):
        try:
            if isinstance(quantity, bool):
                raise ValueError
            q=int(quantity)
            if isinstance(quantity, float) and not quantity.is_integer():
                raise ValueError
        except (ValueError,TypeError,OverflowError):
            raise ValueError("Количество должно быть целым числом.")
        if not 1<=q<=99: raise ValueError("Количество должно быть от 1 до 99.")
        with self.db.connect() as con:
            p=con.execute("SELECT Price,Stock FROM Products WHERE ProductID=? AND Active=1",(product_id,)).fetchone()
            if not p: raise ValueError("Товар не найден или недоступен.")
            if p["Stock"]<q: raise ValueError("Недостаточно товара на складе.")
            con.execute("INSERT INTO Purchases(UserID,ProductID,Quantity,UnitPrice) VALUES(?,?,?,?)",(user_id,product_id,q,p["Price"]))
            con.execute("UPDATE Products SET Stock=Stock-? WHERE ProductID=?",(q,product_id))
    def report(self):
        return self.db.query("""SELECT 'Всего питомцев',CAST(COUNT(*) AS TEXT) FROM Pets
        UNION ALL SELECT 'Записей на приём',CAST(COUNT(*) AS TEXT) FROM Appointments
        UNION ALL SELECT 'Продажи, сумма',printf('%.2f',COALESCE(SUM(Quantity*UnitPrice),0)) FROM Purchases
        UNION ALL SELECT 'Средний чек',printf('%.2f',COALESCE(AVG(Quantity*UnitPrice),0)) FROM Purchases""")
    def audit(self):
        return self.db.query("SELECT AuditID,TableName,Operation,Username,ChangedAt,Data FROM AuditLog ORDER BY AuditID DESC LIMIT 200")
