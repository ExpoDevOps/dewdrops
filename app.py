from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import time
import os

app = Flask(__name__)

CATEGORIES = ["code", "research", "building", "meeting", "field", "social"]

def init_db():
    db_path = '/var/www/dewdrops/dewdrops.db' if os.path.exists('/var/www/dewdrops') else 'dewdrops.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notes 
                 (id INTEGER PRIMARY KEY, category TEXT, timestamp TEXT, content TEXT, start_time REAL)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/dewdrops/', methods=['GET', 'POST'])
def index():
    current_category = request.args.get('category', CATEGORIES[0])
    print(f"DEBUG: Current category is {current_category}")
    if request.method == 'POST':
        content = request.form['note']
        current_category = request.form.get('category', request.args.get('category', CATEGORIES[0]))
        timestamp = datetime.now().strftime('%H:%M:%S')
        start_time = time.time()
        conn = sqlite3.connect('dewdrops.db' if os.path.exists('dewdrops.db') else '/var/www/dewdrops/dewdrops.db')
        c = conn.cursor()
        c.execute('INSERT INTO notes (category, timestamp, content, start_time) VALUES (?, ?, ?, ?)',
                  (current_category, timestamp, content, start_time))
        conn.commit()
        conn.close()
        print(f"DEBUG: Saved note '{content}' to {current_category} at {timestamp}")
        return redirect(url_for('index', category=current_category))

    conn = sqlite3.connect('dewdrops.db' if os.path.exists('dewdrops.db') else '/var/www/dewdrops/dewdrops.db')
    c = conn.cursor()
    c.execute('SELECT * FROM notes WHERE category = ?', (current_category,))
    notes = c.fetchall()
    conn.close()
    print(f"DEBUG: Loaded {len(notes)} notes for {current_category}")
    return render_template('index.html', categories=CATEGORIES, current_category=current_category, notes=notes)

@app.route('/dewdrops/report')
def report():
    conn = sqlite3.connect('dewdrops.db' if os.path.exists('dewdrops.db') else '/var/www/dewdrops/dewdrops.db')
    c = conn.cursor()
    c.execute('SELECT * FROM notes')
    notes = c.fetchall()
    conn.close()
    print(f"DEBUG: Loaded {len(notes)} total notes for report")

    task_times = {cat: 0.0 for cat in CATEGORIES}
    for note in notes:
        category = note[1]
        start_time = note[4] if len(note) > 4 else None
        if start_time:
            elapsed = (time.time() - start_time) / 60.0
            task_times[category] = task_times.get(category, 0) + elapsed

    return render_template('report.html', notes=notes, task_times=task_times, categories=CATEGORIES)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)