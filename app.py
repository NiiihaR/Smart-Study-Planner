from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# --- Database Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///study_planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models ---
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Relationship to link tasks and sessions to a subject
    tasks = db.relationship('Task', backref='subject', lazy=True)
    sessions = db.relationship('StudySession', backref='subject', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    duration_minutes = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(200))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

# --- Routes ---

@app.route('/')
def dashboard():
    # 1. Fetch Data
    subjects = Subject.query.all()
    tasks = Task.query.filter_by(is_completed=False).order_by(Task.deadline).all()
    
    # 2. Analytics: Calculate Total Study Time per Subject
    subject_names = []
    subject_hours = []
    
    for sub in subjects:
        total_mins = sum([session.duration_minutes for session in sub.sessions])
        subject_names.append(sub.name)
        subject_hours.append(total_mins / 60) # Convert to hours

    # 3. Analytics: Check for "Neglected Subjects" (Zero study time)
    neglected_subjects = [name for name, hours in zip(subject_names, subject_hours) if hours == 0]
    insight_msg = ""
    if neglected_subjects:
        insight_msg = f"Tip: You haven't studied {', '.join(neglected_subjects)} yet. Plan a session soon!"
    else:
        insight_msg = "Great job! You are maintaining a balanced study schedule."

    return render_template('dashboard.html', 
                           subjects=subjects, 
                           tasks=tasks, 
                           chart_labels=json.dumps(subject_names), 
                           chart_data=json.dumps(subject_hours),
                           insight_msg=insight_msg)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form.get('name')
    if name:
        new_subject = Subject(name=name)
        db.session.add(new_subject)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_task', methods=['POST'])
def add_task():
    title = request.form.get('title')
    subject_id = request.form.get('subject_id')
    deadline_str = request.form.get('deadline')
    
    if title and subject_id and deadline_str:
        deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        new_task = Task(title=title, subject_id=subject_id, deadline=deadline_date)
        db.session.add(new_task)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/log_session', methods=['POST'])
def log_session():
    subject_id = request.form.get('subject_id')
    duration = request.form.get('duration')
    notes = request.form.get('notes')
    
    if subject_id and duration:
        new_session = StudySession(subject_id=subject_id, duration_minutes=int(duration), notes=notes)
        db.session.add(new_session)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task:
        task.is_completed = True
        db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Creates the database file automatically
    app.run(debug=True)
