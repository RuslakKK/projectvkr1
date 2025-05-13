from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
import pyodbc
import os
from openpyxl import Workbook
from flask import send_file
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super-secret'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    r'DBQ=database/computers.accdb;'  
)


from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, username, fullname, role):
        self.id = username
        self.username = username
        self.fullname = fullname
        self.role = role



@login_manager.user_loader
def load_user(user_id):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT username, fullname, role FROM users WHERE username = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return User(username=user.username, fullname=user.fullname, role=user.role)
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT username, password, fullname, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and password == user.password:
            user_obj = User(username=user.username, fullname=user.fullname, role=user.role)
            login_user(user_obj)
            return redirect(url_for('index'))
        else:
            flash('❌ Неверное имя пользователя или пароль')

    return render_template('login.html')


@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username, fullname=current_user.fullname)


@app.route('/api/departments')
def get_departments():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT dp_name FROM deportament")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([r.dp_name for r in rows])

@app.route('/api/computers')
def get_computers():
    department = request.args.get("department")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    if department:
        cursor.execute("""
            SELECT c.pc_name, c.sam_account_name, u.cn
            FROM computers c
            LEFT JOIN pc_users u ON c.sam_account_name = u.sam_account_name
            WHERE c.[deportament-name] = ?
        """, (department,))
    else:
        cursor.execute("""
            SELECT c.pc_name, c.sam_account_name, u.cn
            FROM computers c
            LEFT JOIN pc_users u ON c.sam_account_name = u.sam_account_name
        """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "pc_name": r[0],
            "sam_account_name": r[1],
            "full_name": r[2] or "",
            "id": r[0],
            "name": f"{r[0]}/{r[1]}"
        }
        for r in rows
    ])



def table_exists(cursor, table_name):
    try:
        cursor.execute(f"SELECT * FROM {table_name} WHERE 1=0")
        return True
    except:
        return False


#@app.route('/api/add-custom-field', methods=['POST'])
#@login_required
# def add_custom_field():
 #   if current_user.role != "Руководство":
  #      return jsonify({"status": "error", "message": "Доступ запрещён"}), 403

#    data = request.json
 #   field_name = data["field_name"].strip().lower().replace(" ", "_")
#    label = data["label"].strip()
#    ref_table = field_name
#    column_name = f"{field_name}-name"

#    conn = pyodbc.connect(conn_str)
#    cursor = conn.cursor()

#    try:
        # Проверка: поле уже есть в таблице computers
#        cursor.execute("SELECT * FROM computers")
#        col_names = [desc[0].lower() for desc in cursor.description]
#        if column_name.lower() in col_names:
#            return jsonify({"status": "error", "message": "Поле уже существует в таблице компьютеров"}), 400

        # Проверка: существует ли уже таблица справочника
#        if table_exists(cursor, ref_table):
#            return jsonify({"status": "error", "message": "Справочная таблица уже существует"}), 400

        # Добавляем колонку в таблицу computers
#        cursor.execute(f"ALTER TABLE computers ADD COLUMN [{column_name}] TEXT")

        # Создаём справочник
 #       cursor.execute(f"""
  #          CREATE TABLE {ref_table} (
   #             id AUTOINCREMENT PRIMARY KEY,
    #            name TEXT,
     #           description TEXT
       #     )
      #  """)

     #   conn.commit()
    # except Exception as e:
    #    conn.rollback()
     #   return jsonify({"status": "error", "message": str(e)}), 500
   # finally:
    #    conn.close()

 #   return jsonify({"status": "ok", "field": field_name})

#@app.route('/api/custom-fields')
#@login_required
# def get_custom_fields():
#    conn = pyodbc.connect(conn_str)
#    cursor = conn.cursor()
#
#    cursor.execute("SELECT * FROM computers")
#    col_names = [desc[0] for desc in cursor.description]
#    conn.close()
#
#    standard = {
#        "pc_name", "sam_account_name", "processor-name", "storageunit-name",
#        "monitor-name", "ram-number", "device-type", "deportament-name"
#    }
#
 #   custom = [col for col in col_names if col.endswith("-name") and col not in standard]
  #  return jsonify(custom)


@app.route('/api/computer/<string:pc_name>')
def get_computer_info(pc_name):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.pc_name, c.sam_account_name, p.cn,
               c.[processor-name], c.[storageunit-name],
               c.[monitor-name], c.[ram-number], c.[device-type]
        FROM computers c
        LEFT JOIN pc_users p ON c.sam_account_name = p.sam_account_name
        WHERE c.pc_name = ?
    """, (pc_name,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "pc_name": row[0],
            "sam_account_name": row[1],  # логин
            "full_name": row[2],         # ФИО
            "processor": row[3],
            "storage": row[4],
            "monitor": row[5],
            "ram": row[6],
            "type": row[7]
        })
    else:
        return jsonify({"message": "Компьютер не найден"}), 404



@app.route('/api/computer', methods=['POST'])
def add_computer():
    data = request.json
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO computers (pc_name, sam_account_name, [processor-name], 
            [storageunit-name], [monitor-name], [ram-number], [device-type], [deportament-name])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(data["pc_name"]),
        str(data["sam_account_name"]),
        str(data["processor"]),
        str(data["storage"]),
        str(data["monitor"]),
        str(data["ram"]),
        str(data["type"]),
        str(data["department"])
    ))
    
    #Автоматическое добавление процессора
    #cursor.execute("SELECT COUNT(*) FROM processor WHERE p_name = ?", (data["processor"],))
    #if cursor.fetchone()[0] == 0:
        #cursor.execute("INSERT INTO processor (p_name, rate) VALUES (?, ?)", (data["processor"], 0))

    #Автоматическое добавление монитора
    #cursor.execute("SELECT COUNT(*) FROM monitor WHERE m_name = ?", (data["monitor"],))
    #if cursor.fetchone()[0] == 0:
        #cursor.execute("INSERT INTO monitor (m_name, dioganal) VALUES (?, ?)", (data["monitor"], 0))

    #Автоматическое добавление накопителя
    #cursor.execute("SELECT COUNT(*) FROM storageunit WHERE su_name = ?", (data["storage"],))
    #if cursor.fetchone()[0] == 0:
         #cursor.execute("INSERT INTO storageunit (su_name, type, number) VALUES (?, ?, ?)", (data["storage"], "", 0))


    
        # Запись в историю добавления
    cursor.execute("""
        INSERT INTO history (pc_name, username, old_value, new_value, date_changed)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["pc_name"],
        current_user.fullname,
        "Компьютер не существовал",
        "Добавлен новый компьютер",
        datetime.now()
    ))
    if "-COPY" in data["pc_name"]:  # только для копий
        cursor.execute("""
        INSERT INTO history (pc_name, username, old_value, new_value, date_changed)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["pc_name"],
        current_user.fullname,
        "Копия компьютера",
        f"Скопировано с: {data['pc_name'].replace('-COPY','')}",
        datetime.now()
    ))

    conn.commit()
    conn.close()
    return jsonify({"status": "added"}), 201

@app.route('/api/computer/<string:pc_name>', methods=['DELETE'])
@login_required
def delete_computer(pc_name):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Получить текущего пользователя компьютера
    cursor.execute("SELECT sam_account_name FROM computers WHERE pc_name = ?", (pc_name,))
    row = cursor.fetchone()
    old_user = row[0] if row else "неизвестно"

    # Удалить компьютер
    cursor.execute("DELETE FROM computers WHERE pc_name = ?", (pc_name,))

    # Записать в историю
    cursor.execute("""
        INSERT INTO history (pc_name, username, old_value, new_value, date_changed)
        VALUES (?, ?, ?, ?, ?)
    """, (
        pc_name,
        current_user.fullname,
        f"Был пользователь: {old_user}",
        "Компьютер удалён",
        datetime.now()
    ))

    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})


@app.route('/api/computer/<string:pc_name>', methods=['PUT'])
@login_required
def update_computer(pc_name):
    data = request.json
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Получаем старые значения
    cursor.execute("""
        SELECT sam_account_name, [processor-name], [storageunit-name],
               [monitor-name], [ram-number], [device-type], [deportament-name]
        FROM computers WHERE pc_name = ?
    """, (pc_name,))
    old = cursor.fetchone()

    if not old:
        conn.close()
        return jsonify({"status": "not_found"}), 404

    old_fields = {
        "sam_account_name": old[0],
        "processor": old[1],
        "storage": old[2],
        "monitor": old[3],
        "ram": old[4],
        "type": old[5],
        "department": old[6]
    }

    # Обновляем значения
    cursor.execute("""
        UPDATE computers SET 
            sam_account_name=?, [processor-name]=?, [storageunit-name]=?,
            [monitor-name]=?, [ram-number]=?, [device-type]=?, [deportament-name]=?
        WHERE pc_name=?
    """, (
        data["sam_account_name"], data["processor"], data["storage"],
        data["monitor"], data["ram"], data["type"], data["department"], pc_name
    ))

    # Сравниваем и записываем в историю каждое изменение
    for key, old_val in old_fields.items():
        new_val = data.get(key)
        if str(old_val) != str(new_val):
            cursor.execute("""
                INSERT INTO history (pc_name, username, old_value, new_value, date_changed)
                VALUES (?, ?, ?, ?, ?)
            """, (
                pc_name,
                current_user.fullname,
                f"{key}: {old_val}",
                f"{key}: {new_val}",
                datetime.now()
            ))

    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})


@app.route('/api/autocomplete/<string:field>')
def autocomplete(field):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    if field == "processor-name":
        cursor.execute("SELECT DISTINCT p_name FROM processor")
    elif field == "monitor-name":
        cursor.execute("SELECT DISTINCT m_name FROM monitor")
    elif field == "storageunit-name":
        cursor.execute("SELECT DISTINCT su_name FROM storageunit")
    else:
        return jsonify([])

    rows = cursor.fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])


@app.route("/api/history")
@login_required
def get_history():
    page = int(request.args.get("page", 1))
    limit = 30
    offset = (page - 1) * limit

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Получаем дату, до которой нужно брать записи
    if offset > 0:
        cursor.execute(f"""
            SELECT MIN(date_changed)
            FROM (
                SELECT TOP {offset} date_changed
                FROM history
                ORDER BY date_changed DESC
            ) AS sub
        """)
        result = cursor.fetchone()
        date_cutoff = result[0] if result else None

        if not date_cutoff:
            return jsonify({"entries": [], "page": page})

        query = f"""
            SELECT TOP {limit} pc_name, username, date_changed, old_value, new_value
            FROM history
            WHERE date_changed < ?
            ORDER BY date_changed DESC
        """
        cursor.execute(query, (date_cutoff,))
    else:
        query = f"""
            SELECT TOP {limit} pc_name, username, date_changed, old_value, new_value
            FROM history
            ORDER BY date_changed DESC
        """
        cursor.execute(query)

    rows = cursor.fetchall()
    conn.close()

    entries = [{
        "pc": r[0] or "",
        "user": r[1] or "",
        "date": r[2].strftime("%Y-%m-%d %H:%M:%S") if r[2] else "",
        "old": r[3] or "",
        "new": r[4] or ""
    } for r in rows]

    return jsonify({
        "entries": entries,
        "page": page,
        "has_more": len(entries) == limit
    })




@app.route('/api/modernization-save', methods=['POST'])
@login_required
def save_modernization():
    if current_user.role != 'Руководство':
        return jsonify({"status": "error", "message": "Только руководитель может составлять план модернизации"}), 403   
    data = request.json
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM modernization_results")  # храним одно состояние
    cursor.execute("""
        INSERT INTO modernization_results (username, result_json, date_created)
        VALUES (?, ?, ?)
    """, (current_user.fullname, str(data), datetime.now()))
    conn.commit()
    conn.close()
    return jsonify({"status": "saved"})

@app.route('/api/modernization-load')
@login_required
def load_modernization():
    if current_user.role != 'Руководство':
        return jsonify({"status": "error", "message": "Только руководитель может составлять план модернизации"}), 403  
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT result_json FROM modernization_results")
    row = cursor.fetchone()
    conn.close()
    return jsonify(eval(row[0]) if row else [])


@app.route('/api/modernization-check', methods=['POST'])
@login_required
def modernization_check():
    data = request.json
    conditions = data.get('conditions', [])

    if not conditions:
        return jsonify([])

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    
    where_clauses = []
    values = []

    for cond in conditions:
        field = cond['field']
        op = cond['operator'].upper()
        value = cond['value']

      
        if op == 'LIKE':
            where_clauses.append(f"[{field}] LIKE ?")
            values.append(f"%{value}%")
        else:
            where_clauses.append(f"[{field}] {op} ?")
            values.append(value)

    where_str = " AND ".join(where_clauses)
    query = f"SELECT pc_name, sam_account_name FROM computers WHERE {where_str}"

    cursor.execute(query, values)
    rows = cursor.fetchall()
    conn.close()

    return jsonify([{"pc_name": r.pc_name, "sam_account_name": r.sam_account_name} for r in rows])



@app.route('/api/add-department', methods=['POST'])
@login_required
def add_department():
    if current_user.role != "Руководство":
        return jsonify({"status": "error", "message": "Доступ только для руководства"}), 403

    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({"status": "error", "message": "Название не может быть пустым"}), 400

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Проверим, существует ли уже такое подразделение
        cursor.execute("SELECT COUNT(*) FROM deportament WHERE dp_name = ?", (name,))
        if cursor.fetchone()[0] > 0:
            return jsonify({"status": "error", "message": "Подразделение уже существует"}), 409

        # Добавим
        cursor.execute("INSERT INTO deportament (dp_name) VALUES (?)", (name,))
        conn.commit()
        conn.close()

        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/report/inventory/excel")
@login_required
def download_inventory_excel():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            pc_name,
            sam_account_name,
            [deportament-name],
            [device-type],
            [processor-name],
            [ram-number],
            [storageunit-name],
            [monitor-name]
        FROM computers
    """)
    rows = cursor.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Учет техники"

    headers = [
        "Имя компьютера", "Имя пользователя", "Подразделение",
        "Тип устройства", "Процессор", "Оперативная память",
        "Накопитель", "Монитор"
    ]
    ws.append(headers)
    for row in rows:
        ws.append([cell for cell in row])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="Отчет_Учет_Техники.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/api/components/processors')
def get_processors():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT p_name FROM processor")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"p_name": r.p_name} for r in rows])

@app.route('/api/components/storages')
def get_storages():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT su_name FROM storageunit")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"su_name": r.su_name} for r in rows])

@app.route('/api/components/monitors')
def get_monitors():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT m_name FROM monitor")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"m_name": r.m_name} for r in rows])


@app.route("/report/history/excel")
@login_required
def download_history_excel():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            pc_name,
            username,
            date_changed,
            old_value,
            new_value
        FROM history
        ORDER BY date_changed DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "История изменений"

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = length + 2

    headers = [
        "Имя компьютера", "Имя пользователя", "Дата и время",
        "Старое значение", "Новое значение"
    ]
    ws.append(headers)
    for row in rows:
        ws.append([cell for cell in row])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="Отчет_История_Изменений.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Получить всех пользователей
@app.route("/api/users", methods=["GET"])
@login_required
def get_users():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT username, fullname, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return jsonify([{"username": u[0], "fullname": u[1], "role": u[2]} for u in users])

# Добавить нового пользователя
@app.route('/api/users', methods=['POST'])
def add_user():
    try:
        data = request.get_json()
        username = data['username']
        fullname = data['fullname']
        role = data['role']
        password = data['password']

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Проверка на существование пользователя
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        if cursor.fetchone()[0] > 0:
            return jsonify({"error": "Пользователь уже существует"}), 400

        cursor.execute("""
            INSERT INTO users (username, password, fullname, role)
            VALUES (?, ?, ?, ?)
        """, (username, password, fullname, role))
        conn.commit()
        conn.close()

        return jsonify({"message": "User added successfully"}), 201
    except Exception as e:
        print("Error adding user:", e)
        return jsonify({"error": str(e)}), 500


# Обновить пользователя
@app.route("/api/users/<username>", methods=["PUT"])
@login_required
def update_user(username):
    data = request.get_json()
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET password = ?, fullname = ?, role = ?
        WHERE username = ?
    """, data["password"], data["fullname"], data["role"], username)
    conn.commit()
    conn.close()
    return jsonify({"message": "Пользователь обновлен"})

# Удалить пользователя
@app.route("/api/users/<username>", methods=["DELETE"])
@login_required
def delete_user(username):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Пользователь удален"})

@app.route('/api/all-pc-users')
@login_required
def get_all_pc_users():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT sam_account_name, cn FROM pc_users")
    users = cursor.fetchall()
    conn.close()
    return jsonify([{"sam_account_name": u[0], "cn": u[1]} for u in users])


@app.route('/api/pc-users', methods=['POST'])
@login_required
def add_pc_user():
    if current_user.role != "Руководство":
        return jsonify({"message": "Доступ запрещён"}), 403

    data = request.get_json()
    required_fields = ["sam_account_name", "cn", "title", "employeeID"]

    if not all(field in data and data[field].strip() for field in required_fields):
        return jsonify({"message": "Не все поля заполнены"}), 400

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Проверка на дубликаты
        cursor.execute("SELECT 1 FROM pc_users WHERE sam_account_name = ?", data["sam_account_name"])
        if cursor.fetchone():
            return jsonify({"message": "Пользователь с таким логином уже существует"}), 409

        cursor.execute("""
            INSERT INTO pc_users (sam_account_name, cn, title, employeeID)
            VALUES (?, ?, ?, ?)
        """, data["sam_account_name"], data["cn"], data["title"], data["employeeID"])

        conn.commit()
        return jsonify({"message": "Пользователь успешно добавлен"}), 200
    except Exception as e:
        print("Ошибка при добавлении пользователя ПК:", e)
        return jsonify({"message": "Ошибка сервера"}), 500


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/history')
@login_required
def history():
    return render_template('history.html', username=current_user.username, fullname=current_user.fullname)

@app.route('/modernization')
@login_required
def modernization():
    return render_template('modernization.html', username=current_user.username, fullname=current_user.fullname)


# Запуск сервера
if __name__ == '__main__':
    app.run(debug=True)
