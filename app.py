from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
import os
from functools import wraps
from database import init_db, DB_PATH

app = Flask(__name__)
app.secret_key = 'super_secret_amazing_key' # for flash messages

# Ensure DB is initialized
if not os.path.exists(DB_PATH):
    init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') is not True:
            flash("Please log in to access the admin portal.", "error")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def register():
    return render_template('register.html')

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        department = request.form.get('department')
        interested_domains = request.form.get('interested_domains')
        events = request.form.get('events')

        # Basic server-side validation
        if not name or not roll_number or not department or not interested_domains or not events:
            flash("All fields are required!", "error")
            return redirect('/')
        
        if len(roll_number) != 8 or not roll_number.isdigit():
            flash("Roll Number must be exactly 8 digits.", "error")
            return redirect('/')
        
        conn = get_db_connection()
        
        # Check if roll number is already registered
        existing = conn.execute('SELECT 1 FROM students WHERE roll_number = ?', (roll_number,)).fetchone()
        if existing:
            flash("This roll number has registered. Please register with another roll number.", "error")
            conn.close()
            return redirect('/')
            
        conn.execute('INSERT INTO students (name, roll_number, department, interested_domains, events) VALUES (?, ?, ?, ?, ?)',
                     (name, roll_number, department, interested_domains, events))
        conn.commit()
        conn.close()
        
        flash("Registration successful!", "success")
        return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Hardcoded credentials for the admin
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            flash("Successfully logged in.", "success")
            return redirect('/admin')
        else:
            flash("Invalid credentials. Try again.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You have been logged out.", "success")
    return redirect('/login')

@app.route('/admin')
@login_required
def admin():
    conn = get_db_connection()
    # Order by name alphabetically (case-insensitive)
    students = conn.execute('SELECT * FROM students ORDER BY name COLLATE NOCASE ASC').fetchall()
    conn.close()
    return render_template('admin.html', students=students)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
