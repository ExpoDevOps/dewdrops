from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Categories for notes
categories = ['code', 'research', 'building', 'meeting', 'field', 'social']

def get_db_connection():
    conn = sqlite3.connect('dewdrops.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                timestamp TEXT,
                content TEXT,
                start_time REAL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS archives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                timestamp TEXT,
                content TEXT,
                start_time REAL,
                archive_date TEXT
            )
        ''')
        conn.commit()

init_db()

def archive_notes():
    with get_db_connection() as conn:
        today = datetime.now().strftime('%Y-%m-%d')
        conn.execute('''
            INSERT INTO archives (category, timestamp, content, start_time, archive_date)
            SELECT category, timestamp, content, start_time, ? FROM notes
        ''', (today,))
        conn.execute('DELETE FROM notes')
        conn.commit()
    logger.debug("Notes archived and cleared.")

scheduler = BackgroundScheduler()
scheduler.add_job(archive_notes, 'cron', hour=23, minute=58)
scheduler.start()

def generate_daily_report():
    with get_db_connection() as conn:
        notes = conn.execute('SELECT * FROM notes ORDER BY start_time').fetchall()
        task_times = {cat: 0 for cat in categories}
        for i in range(len(notes)-1):
            current_note = notes[i]
            next_note = notes[i+1]
            time_diff = next_note['start_time'] - current_note['start_time']
            task_times[current_note['category']] += time_diff
        report = {
            'notes': notes,
            'task_times': task_times,
            'categories': categories
        }
        logger.debug(f"Generated daily report: {len(notes)} notes")
        return report

scheduler.add_job(generate_daily_report, 'cron', hour=23, minute=59)

@app.route('/', methods=['GET', 'POST'])
def index():
    current_category = request.form.get('category', request.args.get('category', 'code'))
    if current_category not in categories:
        current_category = 'code'

    if request.method == 'POST':
        content = request.form['note_text']
        if content:
            timestamp = datetime.now().strftime('%m/%d/%Y | %H:%M:%S')
            start_time = time.time()
            with get_db_connection() as conn:
                conn.execute('INSERT INTO notes (category, timestamp, content, start_time) VALUES (?, ?, ?, ?)',
                             (current_category, timestamp, content, start_time))
                conn.commit()
            logger.debug(f"Added note: {content} in category {current_category}")
            return redirect(url_for('index', category=current_category))

    with get_db_connection() as conn:
        notes = conn.execute('SELECT * FROM notes ORDER BY start_time DESC').fetchall()
        logger.debug(f"Loaded {len(notes)} notes")

    return render_template('index.html',
                         categories=categories,
                         current_category=current_category,
                         notes=notes)

@app.route('/report')
def report():
    with get_db_connection() as conn:
        notes = conn.execute('SELECT * FROM notes ORDER BY start_time').fetchall()
        task_times = {cat: 0 for cat in categories}
        for i in range(len(notes)-1):
            current_note = notes[i]
            next_note = notes[i+1]
            time_diff = next_note['start_time'] - current_note['start_time']
            if current_note['category'] in task_times:
                task_times[current_note['category']] += time_diff
        logger.debug(f"Loaded {len(notes)} total notes for report")
    return render_template('report.html',
                         notes=notes,
                         task_times=task_times,
                         categories=categories)

@app.route('/archives')
def archives():
    selected_date = request.args.get('date')
    with get_db_connection() as conn:
        dates = conn.execute('SELECT DISTINCT archive_date FROM archives ORDER BY archive_date DESC').fetchall()
        dates = [row['archive_date'] for row in dates]
        notes = []
        if selected_date:
            notes = conn.execute('SELECT * FROM archives WHERE archive_date = ? ORDER BY start_time', (selected_date,)).fetchall()
        logger.debug(f"Rendering archives.html with dates={dates}, selected_date={selected_date}, notes={len(notes)}")
    return render_template('archives.html',
                         dates=dates,
                         selected_date=selected_date,
                         notes=notes,
                         categories=categories)

if __name__ == '__main__':
    app.run(debug=True)