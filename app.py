from flask import Flask, render_template, request, redirect, flash, session, Response
import sqlite3
import os
import csv
import io
from functools import wraps
from database import init_db, DB_PATH
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'ignite_fallback_secret')

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'studentportal')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '123rusa123')

if not os.path.exists(DB_PATH):
    init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('logged_in') is not True:
            flash("Please log in to access the admin portal.", "error")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ── REGISTER ──
@app.route('/')
def register():
    return render_template('register.html')

# ── SUBMIT ──
@app.route('/submit', methods=['POST'])
def submit():
    name             = request.form.get('name', '').strip()
    roll_number      = request.form.get('roll_number', '').strip()
    department       = request.form.get('department', '').strip()
    interested_domains = request.form.get('interested_domains', '').strip()
    events           = request.form.get('events', '').strip()
    email            = request.form.get('email', '').strip()

    if not all([name, roll_number, department, interested_domains, events, email]):
        flash("All fields are required!", "error")
        return redirect('/')

    if len(roll_number) != 8 or not roll_number.isdigit():
        flash("Roll Number must be exactly 8 digits.", "error")
        return redirect('/')

    conn = get_db()

    # Duplicate roll number check
    if conn.execute('SELECT 1 FROM students WHERE roll_number = ?', (roll_number,)).fetchone():
        flash("This roll number is already registered.", "error")
        conn.close()
        return redirect('/')

    # Duplicate email check
    if conn.execute('SELECT 1 FROM students WHERE LOWER(email) = LOWER(?)', (email,)).fetchone():
        flash("This email address is already registered.", "error")
        conn.close()
        return redirect('/')

    conn.execute(
        'INSERT INTO students (name, roll_number, email, department, interested_domains, events) VALUES (?, ?, ?, ?, ?, ?)',
        (name, roll_number, email, department, interested_domains, events)
    )
    conn.commit()
    conn.close()

    return render_template('success.html', name=name, roll_number=roll_number, department=department.upper())

# ── LOGIN ──
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/admin')
        flash("Invalid credentials. Try again.", "error")
    return render_template('login.html')

# ── LOGOUT ──
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

# ── ADMIN DASHBOARD ──
@app.route('/admin')
@login_required
def admin():
    conn = get_db()
    search = request.args.get('q', '').strip()
    dept_filter = request.args.get('dept', '').strip()

    query = 'SELECT * FROM students'
    params = []
    conditions = []

    if search:
        conditions.append("(name LIKE ? OR roll_number LIKE ? OR email LIKE ?)")
        params += [f'%{search}%', f'%{search}%', f'%{search}%']

    if dept_filter:
        conditions.append("department = ?")
        params.append(dept_filter)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY name COLLATE NOCASE ASC'

    students = conn.execute(query, params).fetchall()
    total    = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    conn.close()

    return render_template('admin.html',
                           students=students,
                           total=total,
                           search=search,
                           dept_filter=dept_filter)

# ── EXPORT CSV ──
@app.route('/admin/export')
@login_required
def export_csv():
    conn = get_db()
    students = conn.execute(
        'SELECT name, roll_number, email, department, interested_domains, events FROM students ORDER BY name COLLATE NOCASE ASC'
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Roll Number', 'Email', 'Department', 'Interested Domains', 'Events'])
    for s in students:
        writer.writerow([s['name'], s['roll_number'], s['email'],
                         s['department'], s['interested_domains'], s['events']])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=registered_students.csv'}
    )

# ── DELETE ONE STUDENT ──
@app.route('/admin/delete/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    conn = get_db()
    conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()
    flash('Student record deleted successfully.', 'success')
    return redirect('/admin')

# ── DELETE ALL STUDENTS ──
@app.route('/admin/delete-all', methods=['POST'])
@login_required
def delete_all_students():
    conn = get_db()
    conn.execute('DELETE FROM students')
    conn.commit()
    conn.close()
    flash('All student records have been deleted.', 'success')
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
