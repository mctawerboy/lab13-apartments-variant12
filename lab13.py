import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3, json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

WIDTH, HEIGHT = 910, 600
root = tk.Tk()
root.title("Квартиры — вариант 12")
root.update_idletasks()
x = (root.winfo_screenwidth() - WIDTH) // 2
y = (root.winfo_screenheight() - HEIGHT) // 2
root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

def center(win, w, h):
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

db = sqlite3.connect("apartments.db")
db.execute("CREATE TABLE IF NOT EXISTS flats(id INTEGER PRIMARY KEY, number INTEGER,"
           " people INTEGER, rooms INTEGER, areas TEXT)")

def refresh(data=None):
    tree.delete(*tree.get_children())
    if data is None:
        data = db.execute("SELECT * FROM flats").fetchall()
    for r in data:
        areas = [float(a) for a in r[4].split(",")] if r[4] else []
        tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], round(sum(areas), 1)))

def form(title, old=None):
    win = tk.Toplevel(root)
    win.title(title)
    center(win, 320, 280)
    inputs = []
    for name in ["Номер квартиры", "Жильцы", "Комнаты", "Площади комнат (через запятую)"]:
        ttk.Label(win, text=name).pack()
        entry = ttk.Entry(win)
        entry.pack()
        inputs.append(entry)
    if old:
        for i, entry in enumerate(inputs):
            entry.insert(0, old[i + 1])
    def save():
        try:
            values = (int(inputs[0].get()), int(inputs[1].get()),
                      int(inputs[2].get()), inputs[3].get())
        except ValueError:
            return messagebox.showerror("Ошибка", "Введите числа!")
        if old:
            db.execute("UPDATE flats SET number=?,people=?,rooms=?,areas=? WHERE id=?",
                       values + (old[0],))
        else:
            db.execute("INSERT INTO flats VALUES(NULL,?,?,?,?)", values)
        db.commit()
        win.destroy()
        refresh()
    ttk.Button(win, text="Сохранить", command=save).pack(pady=10)

def selected():
    pick = tree.selection()
    if not pick:
        return messagebox.showwarning("Внимание", "Выберите запись в таблице")
    return db.execute("SELECT * FROM flats WHERE id=?",
                      (tree.item(pick[0])["values"][0],)).fetchone()

def add(): form("Ввести запись")

def edit():
    row = selected()
    if row: form("Редактировать запись", row)

def delete():
    row = selected()
    if row and messagebox.askyesno("Удалить?", f"Квартира №{row[1]}"):
        db.execute("DELETE FROM flats WHERE id=?", (row[0],))
        db.commit()
        refresh()

def clear():
    if messagebox.askyesno("Очистить?", "Удалить все записи?"):
        db.execute("DELETE FROM flats")
        db.commit()
        refresh()

def goto():
    number = simpledialog.askinteger("Переход", "Номер квартиры:", parent=root)
    if not number: return
    for item in tree.get_children():
        if tree.item(item)["values"][1] == number:
            tree.selection_set(item)
            tree.see(item)
            return
    messagebox.showinfo("Поиск", "Квартира не найдена")

def search():
    field = simpledialog.askstring("Поиск", "Поле: number / people / rooms", parent=root)
    if field not in ("number", "people", "rooms"): return
    value = simpledialog.askstring("Поиск", "Значение:", parent=root)
    refresh(db.execute(f"SELECT * FROM flats WHERE {field} LIKE ?",
                       ("%" + str(value) + "%",)).fetchall())

def import_json():
    file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if not file: return
    with open(file, encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        areas = ",".join(map(str, item["room_areas"]))
        db.execute("INSERT INTO flats VALUES(NULL,?,?,?,?)",
                   (item["apt_number"], item["residents"], item["rooms_count"], areas))
    db.commit()
    refresh()

def export_json():
    file = filedialog.asksaveasfilename(defaultextension=".json")
    if not file: return
    data = []
    for r in db.execute("SELECT * FROM flats"):
        data.append({"apt_number": r[1], "residents": r[2], "rooms_count": r[3],
                     "room_areas": [float(a) for a in r[4].split(",")] if r[4] else []})
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def calculate():
    areas, people = {}, {}
    for r in db.execute("SELECT * FROM flats"):
        total = sum(float(a) for a in r[4].split(",")) if r[4] else 0
        key = "до 40" if total < 40 else "40-70" if total < 70 else "больше 70"
        areas[key] = areas.get(key, 0) + 1
        people[str(r[2])] = people.get(str(r[2]), 0) + 1
    win = tk.Toplevel(root)
    win.title("Вычисленные характеристики")
    center(win, 800, 450)
    fig = plt.Figure(figsize=(8, 4))
    fig.add_subplot(121).bar(areas.keys(), areas.values())
    fig.add_subplot(122).bar(people.keys(), people.values())
    fig.tight_layout()
    FigureCanvasTkAgg(fig, master=win).get_tk_widget().pack()

btn_frame = ttk.Frame(root)
btn_frame.pack(fill="x", padx=10, pady=5)

buttons = [("Импорт JSON", import_json), ("Экспорт JSON", export_json),
           ("Просмотр БД", lambda: refresh()), ("Вычислить", calculate),
           ("Ввести запись", add), ("Перейти к записи", goto),
           ("Редактировать", edit), ("Удалить", delete),
           ("Поиск", search), ("Очистить БД", clear)]
for i, (name, action) in enumerate(buttons):
    ttk.Button(btn_frame, text=name, command=action).grid(row=0, column=i, padx=2)

columns = ["id", "number", "people", "rooms", "areas", "total"]
tree = ttk.Treeview(root, columns=columns, show="headings")
for i, name in enumerate(["ID", "№ квартиры", "Жильцы", "Комнаты", "Площади комнат", "Общая площадь"]):
    tree.heading(columns[i], text=name, anchor="center")
    tree.column(columns[i], width=140, anchor="center")
tree.pack(fill="both", expand=True, padx=10, pady=10)

refresh()
root.mainloop()