from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Замените на безопасный ключ

# Проверка прав администратора
def is_admin():
    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            print(f"Пользователь найден: is_admin = {user['is_admin']}")
            return user['is_admin'] == 1
        else:
            print("Пользователь не найден в базе данных")
            return False
    return False

# Контекстный процессор для шаблонов
@app.context_processor
def utility_processor():
    return dict(is_admin=is_admin)

# Маршрут админ-панели
@app.route('/admin', methods=['GET'])
def admin_panel():
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице')
        return redirect(url_for('task_list'))
    
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, login, password, is_admin, role FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_panel.html', users=users)

# Добавление пользователя
@app.route('/add_user', methods=['POST'])
def add_user():
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице')
        return redirect(url_for('task_list'))
    
    data = request.get_json()
    if data and 'username' in data and 'password' in data:
        username = data['username']
        password = data['password']
        admin_status = data.get('is_admin', 0)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (login, password, is_admin, role) VALUES (%s, %s, %s, %s)",
            (username, password, admin_status, 'user'))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Неверные данные'}), 400

# Редактирование пользователя
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице')
        return redirect(url_for('task_list'))
    
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if request.method == 'POST':
        data = request.get_json()
        if data and 'username' in data and 'is_admin' in data:
            username = data['username']
            is_admin = data['is_admin']
            password = data.get('password')
            if password:
                cur.execute("UPDATE users SET login = %s, password = %s, is_admin = %s WHERE id = %s",
                (username, password, is_admin, user_id))
            else:
                cur.execute("UPDATE users SET login = %s, is_admin = %s WHERE id = %s",
                (username, is_admin, user_id))

            conn.commit()
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Неверные данные'}), 400
    
    cur.execute("SELECT id, login, is_admin FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user:
        return render_template('edit_user.html', user=user)
    flash('Пользователь не найден')
    return redirect(url_for('admin_panel'))

# Удаление пользователя
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице')
        return redirect(url_for('task_list'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Пользователь успешно удален')
    return redirect(url_for('admin_panel'))

# Функция подключения к базе данных
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci'
    )
    return conn

# Главная страница
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('task_list'))
    return redirect(url_for('login'))

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Попытка входа: {username}")
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE login = %s", (username,))
        user = cur.fetchone()
        if user:
            print(f"Пользователь найден: {user['login']}")
            if user['password'] == password:
                print("Пароль верен")
                session['user_id'] = user['id']
                print(f"Сессия установлена: user_id = {session['user_id']}")
                return redirect(url_for('task_list'))
            else:
                print("Неверный пароль")
                flash('Неверное имя пользователя или пароль')
        else:
            print("Пользователь не найден")
            flash('Неверное имя пользователя или пароль')
        cur.close()
        conn.close()
    return render_template('login.html')

# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Попытка регистрации: {username}")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE login = %s", (username,))
        if cur.fetchone():
            print("Пользователь уже существует")
            flash('Имя пользователя уже занято')
        else:
            cur.execute("INSERT INTO users (login, password, is_admin, role) VALUES (%s, %s, %s, %s)",
            (username, password, 0, 'user'))
            conn.commit()
            print("Пользователь успешно зарегистрирован")
            flash('Регистрация прошла успешно, войдите в систему')
            return redirect(url_for('login'))
        cur.close()
        conn.close()
    return render_template('register.html')

# Выход из системы
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы')
    return redirect(url_for('login'))

# Список задач
@app.route('/tasks')
def task_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM items WHERE user_id = %s ORDER BY order_index", (user_id,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('task_list.html', tasks=tasks)

# Добавление задачи
@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = request.get_json()
    if data and 'text' in data:
        text = data['text']
        user_id = session['user_id']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT MAX(order_index) FROM items WHERE user_id = %s", (user_id,))
        max_index = cur.fetchone()[0]
        new_index = 1 if max_index is None else max_index + 1
        cur.execute("INSERT INTO items (text, user_id, order_index) VALUES (%s, %s, %s)",
                    (text, user_id, new_index))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Неверные данные'}), 400

# Редактирование задачи
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if request.method == 'POST':
        text = request.form['text']
        cur.execute("UPDATE items SET text = %s WHERE id = %s AND user_id = %s",
                    (text, task_id, user_id))
        conn.commit()
        if cur.rowcount > 0:
            flash('Задача успешно обновлена')
        else:
            flash('Задача не найдена или у вас нет прав')
        cur.close()
        conn.close()
        return redirect(url_for('task_list'))
    cur.execute("SELECT * FROM items WHERE id = %s AND user_id = %s", (task_id, user_id))
    task = cur.fetchone()
    cur.close()
    conn.close()
    if task:
        return render_template('edit_task.html', task=task)
    flash('Задача не найдена или у вас нет прав')
    return redirect(url_for('task_list'))

# Удаление задачи
@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE id = %s AND user_id = %s", (task_id, user_id))
    conn.commit()
    if cur.rowcount > 0:
        flash('Задача успешно удалена')
    else:
        flash('Задача не найдена или у вас нет прав')
    cur.close()
    conn.close()
    return redirect(url_for('task_list'))

# Реорганизация задач
@app.route('/reorder_tasks', methods=['POST'])
def reorder_tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = request.get_json()
    if data and 'task_ids' in data:
        task_ids = data['task_ids']
        conn = get_db_connection()
        cur = conn.cursor()
        for index, task_id in enumerate(task_ids):
            cur.execute("UPDATE items SET order_index = %s WHERE id = %s AND user_id = %s",
                        (index + 1, task_id, session['user_id']))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Неверные данные'}), 400
