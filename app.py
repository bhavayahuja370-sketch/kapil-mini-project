import csv
import io
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from pathlib import Path

import qrcode
from flask import Flask, abort, flash, redirect, render_template, request, send_file, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['DATABASE'] = str(Path(__file__).with_name('campus.db'))
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'college123')

@contextmanager
def db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, date TEXT NOT NULL, venue TEXT NOT NULL, description TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id), name TEXT NOT NULL, roll TEXT NOT NULL, email TEXT NOT NULL, course TEXT NOT NULL, token TEXT UNIQUE NOT NULL, checked_at TEXT, UNIQUE(event_id,roll));
        ''')
        if not conn.execute('SELECT id FROM events LIMIT 1').fetchone():
            conn.executemany('INSERT INTO events(title,category,date,venue,description) VALUES(?,?,?,?,?)', [
                ('TechVista 2026', 'Technology', '2026-11-25T10:00', 'Innovation Auditorium', 'Code, collaborate and explore ideas with your campus community.'),
                ('Campus Unplugged', 'Culture', '2026-11-27T16:00', 'Open Air Theatre', 'An evening of music, performances and unforgettable campus moments.'),
                ('Career Launchpad', 'Workshop', '2026-12-02T11:00', 'Seminar Hall B', 'Build your resume, practise interviews and prepare for your next opportunity.')])

def organizer(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped

@app.before_request
def csrf():
    session.setdefault('csrf', secrets.token_hex(24))
    if request.method == 'POST' and not secrets.compare_digest(session['csrf'], request.form.get('csrf', '')):
        abort(400, 'Form expired. Reload and try again.')

@app.get('/')
def home():
    with db() as conn:
        events = conn.execute('SELECT e.*, count(r.id) total FROM events e LEFT JOIN registrations r ON r.event_id=e.id GROUP BY e.id ORDER BY e.date').fetchall()
    return render_template('home.html', events=events)

@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    with db() as conn:
        event = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
        if not event: abort(404)
        if request.method == 'POST':
            values = [request.form.get(k, '').strip() for k in ['name', 'roll', 'email', 'course']]
            if any(not v or len(v)>150 for v in values) or '@' not in values[2]:
                flash('Please enter valid details in every field.', 'error')
            else:
                token = secrets.token_urlsafe(24)
                try:
                    conn.execute('INSERT INTO registrations(event_id,name,roll,email,course,token) VALUES(?,?,?,?,?,?)', (event_id,*values,token))
                    return redirect(url_for('ticket', token=token))
                except sqlite3.IntegrityError:
                    flash('This roll number is already registered for this event. Use the original pass or ask the organizer.', 'error')
    return render_template('register.html', event=event)

def get_ticket(token):
    with db() as conn:
        row = conn.execute('SELECT r.*,e.title,e.date,e.venue FROM registrations r JOIN events e ON r.event_id=e.id WHERE r.token=?', (token,)).fetchone()
    if not row: abort(404)
    return row

@app.get('/pass/<token>')
def ticket(token):
    return render_template('ticket.html', r=get_ticket(token))

@app.get('/qr/<token>.png')
def qr(token):
    get_ticket(token)
    output = io.BytesIO()
    qrcode.make(token).save(output, format='PNG')
    output.seek(0)
    return send_file(output, mimetype='image/png', download_name='campus-pass.png')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if secrets.compare_digest(request.form.get('password',''), ADMIN_PASSWORD):
            session['admin'] = True
            return redirect(url_for('dashboard'))
        flash('Incorrect organizer password.', 'error')
    return render_template('login.html')

@app.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.get('/organizer')
@organizer
def dashboard():
    with db() as conn:
        events = conn.execute('SELECT * FROM events ORDER BY date').fetchall()
        selected = request.args.get('event', type=int) or events[0]['id']
        rows = conn.execute('SELECT * FROM registrations WHERE event_id=? ORDER BY id DESC',(selected,)).fetchall()
    return render_template('dashboard.html', events=events, selected=selected, rows=rows, checked=sum(bool(r['checked_at']) for r in rows))

@app.post('/checkin')
@organizer
def checkin():
    token = request.form.get('token','').strip()
    event_id = request.form.get('event',type=int)
    with db() as conn:
        row = conn.execute('SELECT * FROM registrations WHERE token=?',(token,)).fetchone()
        if not row:
            flash('Invalid QR pass. No registration found.', 'error')
        elif row['event_id'] != event_id:
            flash('This pass belongs to a different event.', 'error')
        else:
            result = conn.execute('UPDATE registrations SET checked_at=? WHERE token=? AND checked_at IS NULL', (datetime.now().astimezone().isoformat(timespec='seconds'),token))
            if result.rowcount:
                flash(f"Welcome, {row['name']}! Check-in successful.", 'success')
            else:
                flash(f"{row['name']} has already checked in. Duplicate entry blocked.", 'error')
    return redirect(url_for('dashboard', event=event_id))

@app.post('/events')
@organizer
def create_event():
    keys = ['title','category','date','venue','description']
    values = [request.form.get(k,'').strip() for k in keys]
    try:
        datetime.fromisoformat(values[2])
        if any(not v or len(v)>500 for v in values): raise ValueError()
    except ValueError:
        flash('Enter all event details and a valid date.', 'error')
        return redirect(url_for('dashboard'))
    with db() as conn:
        result = conn.execute('INSERT INTO events(title,category,date,venue,description) VALUES(?,?,?,?,?)', values)
        event_id = result.lastrowid
    flash('Your event is ready for registrations.', 'success')
    return redirect(url_for('dashboard',event=event_id))

@app.get('/export/<int:event_id>')
@organizer
def export(event_id):
    with db() as conn:
        rows = conn.execute('SELECT name,roll,email,course,checked_at FROM registrations WHERE event_id=?',(event_id,)).fetchall()
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['Name','Roll number','Email','Course','Check-in time'])
    for row in rows:
        writer.writerow(["'"+str(v) if str(v).startswith(('=','+','-','@','\t','\r')) else (v or '') for v in row])
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name=f'event-{event_id}-attendance.csv')

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=False)
