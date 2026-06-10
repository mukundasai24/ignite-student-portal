from flask import Flask, render_template, request, redirect, flash, session, Response
import sqlite3
import os
import csv
import io
import requests
import threading
from functools import wraps
from database import init_db, migrate_db, DB_PATH
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'ignite_fallback_secret')

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'studentportal')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '123rusa123')

if not os.path.exists(DB_PATH):
    init_db()
migrate_db()

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

# ── LANDING ──
@app.route('/')
def landing():
    return render_template('landing.html')

# ── GOOGLE SHEETS WEBHOOK ──
def send_to_google_sheet(data):
    webhook_url = os.getenv('GOOGLE_SHEET_URL')
    if not webhook_url:
        return {"status": "success", "message": "Local only"}
    try:
        response = requests.post(webhook_url, json=data, timeout=8)
        return response.json()
    except Exception as e:
        print(f"Error sending to Google Sheet: {e}")
        # If it fails, we still want to allow local registration to proceed just in case
        return {"status": "success"}

# ── REGISTER ──
@app.route('/register')
def register():
    return render_template('register.html')

# ── SUBMIT ──
@app.route('/submit', methods=['POST'])
def submit():
    name               = request.form.get('name', '').strip()
    roll_number        = request.form.get('roll_number', '').strip()
    department         = request.form.get('department', '').strip()
    interested_domains = request.form.get('interested_domains', '').strip()
    events             = request.form.get('events', '').strip()
    email              = request.form.get('email', '').strip()
    phone_number       = request.form.get('phone_number', '').strip()
    suggestions        = request.form.get('suggestions', '').strip()
    expectations       = request.form.get('expectations', '').strip()
    rating_raw         = request.form.get('rating', '').strip()
    involvement        = request.form.get('involvement_interest', '').strip()

    if not all([name, roll_number, department, interested_domains, events, email, phone_number, suggestions, expectations, involvement, rating_raw]):
        flash("All fields are required!", "error")
        return redirect('/register')

    if len(roll_number) != 8 or not roll_number.isdigit():
        flash("Roll Number must be exactly 8 digits.", "error")
        return redirect('/register')

    rating = None
    if rating_raw:
        try:
            rating = int(rating_raw)
            if not (1 <= rating <= 10):
                rating = None
        except ValueError:
            rating = None

    conn = get_db()

    # Duplicate roll number check
    if conn.execute('SELECT 1 FROM students WHERE roll_number = ?', (roll_number,)).fetchone():
        flash("This roll number is already registered.", "error")
        conn.close()
        return redirect('/register')

    # Duplicate email check
    if conn.execute('SELECT 1 FROM students WHERE LOWER(email) = LOWER(?)', (email,)).fetchone():
        flash("This email address is already registered.", "error")
        conn.close()
        return redirect('/register')

    # Send to Google Sheets and check for permanent duplicates
    sheet_data = {
        "name": name,
        "roll_number": roll_number,
        "email": email,
        "phone_number": phone_number,
        "department": department,
        "interested_domains": interested_domains,
        "events": events,
        "suggestions": suggestions,
        "expectations": expectations,
        "rating": rating,
        "involvement": involvement
    }
    sheet_response = send_to_google_sheet(sheet_data)
    if sheet_response and sheet_response.get("status") == "duplicate":
        flash(sheet_response.get("message", "Already registered."), "error")
        conn.close()
        return redirect('/register')
    elif sheet_response and sheet_response.get("status") == "error":
        flash(sheet_response.get("message", "Error connecting to database."), "error")
        conn.close()
        return redirect('/register')

    # Insert into local database
    conn.execute(
        'INSERT INTO students (name, roll_number, email, phone_number, department, interested_domains, events, suggestions, expectations, rating, involvement_interest) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (name, roll_number, email, phone_number or None, department, interested_domains, events, suggestions or None, expectations or None, rating, involvement or None)
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
        'SELECT name, roll_number, email, phone_number, department, interested_domains, events, suggestions, expectations, rating, involvement_interest FROM students ORDER BY name COLLATE NOCASE ASC'
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Roll Number', 'Email', 'Phone Number', 'Department', 'Interested Domains', 'Events', 'Suggestions', 'Expectations', 'Rating', 'Involvement Interest'])
    for s in students:
        writer.writerow([s['name'], s['roll_number'], s['email'], s['phone_number'] or '',
                         s['department'], s['interested_domains'], s['events'],
                         s['suggestions'] or '', s['expectations'] or '', s['rating'] or '',
                         s['involvement_interest'] or ''])

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
