from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import datetime
import os
from sqlalchemy.sql import func
from random import randint

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py', silent=True)

# Set the database URI here
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'todo.db')

db = SQLAlchemy(app)

# Define the database model for tasks
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    narrative = db.Column(db.String(500))
    priority = db.Column(db.Integer, default=3)
    date = db.Column(db.Date, server_default=func.now())  # Use server_default for date
    type = db.Column(db.String(50))
    who = db.Column(db.String(20))
    status = db.Column(db.String(10))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'narrative': self.narrative,
            'priority': self.priority,
            'date': self.date.strftime('%Y-%m-%d'),  # Convert date to string
            'type': self.type,
            'who': self.who,
            'status': self.status,
        }

    def __repr__(self):
        return f'<Task {self.title}>'

# Define the database model for types
class Type(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    shade = db.Column(db.String(7), nullable=False)  # Store color as HEX value

    def __repr__(self):
        return f'<Type {self.name}>'

# Create the database tables (if they don't exist)
with app.app_context():
    db.create_all()

# Utility function to generate a random pastel color
def random_pastel_color():
    r = randint(127, 255)
    g = randint(127, 255)
    b = randint(127, 255)
    return f'#{r:02x}{g:02x}{b:02x}'

# Route for the main page
@app.route('/')
def index():
    filter_status = request.args.get('filter_status')
    sort_by = request.args.get('sort_by', 'date')

    if filter_status:
        tasks = Task.query.filter_by(status=filter_status).order_by(sort_by).all()
    else:
        tasks = Task.query.order_by(sort_by).all()

    type_counts = db.session.query(Task.type, func.count(Task.id)).group_by(Task.type).all()
    type_counts = {type_: count for type_, count in type_counts}

    types = Type.query.order_by(Type.name).all()

    # Add missing types from tasks to the Type table
    for task_type in type_counts.keys():
        if not Type.query.filter_by(name=task_type).first():
            new_type = Type(name=task_type, shade=random_pastel_color())
            db.session.add(new_type)
            db.session.commit()

    # Update type counts
    for type_obj in types:
        type_obj.count = type_counts.get(type_obj.name, 0)

    # Convert tasks to JSON-serializable format
    tasks_json = [task.to_dict() for task in tasks]

    current_date = datetime.date.today().strftime('%Y-%m-%d')  # Convert current_date to string

    # Update render_template line
    return render_template('index.html', tasks=tasks_json, filter_status=filter_status, sort_by=sort_by, type_counts=type_counts, types=types, current_date=current_date)


# Route for adding a new task
@app.route('/add', methods=['POST'])
def add():
    title = request.form['title']
    narrative = request.form['narrative']
    priority = int(request.form['priority'])
    date_str = request.form.get('date')  # Get the date from the form
    if date_str:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        date = datetime.date.today()  # Use today's date as default
    type = request.form['type']
    who = request.form.get('who')
    status = request.form.get('status', 'open')

    new_task = Task(title=title, narrative=narrative, priority=priority, date=date, type=type, who=who, status=status)

    # Add the type to the Type table if it doesn't exist
    if not Type.query.filter_by(name=type).first():
        new_type = Type(name=type, shade=random_pastel_color())
        db.session.add(new_type)

    try:
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error adding task: {e}")  # Print the error for debugging
        return 'There was an issue adding your task'

# Route for updating a task
@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    task = Task.query.get_or_404(id)
    task.title = request.form['title']
    task.narrative = request.form['narrative']
    task.priority = int(request.form['priority'])
    date_str = request.form.get('date')
    if date_str:
        task.date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        task.date = datetime.date.today()
    task.type = request.form['type']
    task.who = request.form['who']
    task.status = request.form['status']

    # Add the type to the Type table if it doesn't exist
    if not Type.query.filter_by(name=task.type).first():
        new_type = Type(name=task.type, color=random_pastel_color())
        db.session.add(new_type)

    try:
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error updating task: {e}")
        return 'There was an issue updating your task'

if __name__ == '__main__':
    app.run(debug=True)
