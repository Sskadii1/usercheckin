from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leave_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.String(10), nullable=False)
    end_date = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='Inprogress')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

# Routes
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['role'] = user.role
        return redirect(url_for('dashboard'))
    flash("Invalid credentials")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    
    if user.role == "employee":
        leave_requests = LeaveRequest.query.filter_by(user_id=user.id).all()
    else:
        leave_requests = LeaveRequest.query.all()
    
    return render_template('dashboard.html', user=user, leave_requests=leave_requests)

@app.route('/create_leave', methods=['GET', 'POST'])
def create_leave():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        leave_request = LeaveRequest(
            start_date=request.form['start_date'],
            end_date=request.form['end_date'],
            reason=request.form['reason'],
            user_id=session['user_id']
        )
        db.session.add(leave_request)
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('create_leave.html')

@app.route('/approve_leave/<int:id>')
def approve_leave(id):
    if 'user_id' not in session or session['role'] not in ['manager', 'admin']:
        return redirect(url_for('dashboard'))
    
    leave_request = LeaveRequest.query.get(id)
    if leave_request:
        leave_request.status = 'Approved'
        leave_request.processed_by = session['user_id']
        db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/reject_leave/<int:id>')
def reject_leave(id):
    if 'user_id' not in session or session['role'] not in ['manager', 'admin']:
        return redirect(url_for('dashboard'))
    
    leave_request = LeaveRequest.query.get(id)
    if leave_request:
        leave_request.status = 'Rejected'
        leave_request.processed_by = session['user_id']
        db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Serve templates dynamically
templates = {
    "login.html": """
    <form action="{{ url_for('login') }}" method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    """,

    "dashboard.html": """
    <h2>Welcome {{ user.username }}</h2>
    <h3>Your Leave Requests</h3>
    <ul>
        {% for request in leave_requests %}
            <li>{{ request.reason }} ({{ request.status }}) 
            {% if request.status == 'Inprogress' %}
                <a href="{{ url_for('approve_leave', id=request.id) }}">Approve</a> | 
                <a href="{{ url_for('reject_leave', id=request.id) }}">Reject</a>
            {% endif %}
            </li>
        {% endfor %}
    </ul>
    <a href="{{ url_for('create_leave') }}">Create Leave Request</a>
    """,

    "create_leave.html": """
    <form action="{{ url_for('create_leave') }}" method="POST">
        <label>Start Date:</label><input type="date" name="start_date" required>
        <label>End Date:</label><input type="date" name="end_date" required>
        <label>Reason:</label><textarea name="reason" required></textarea>
        <button type="submit">Submit</button>
    </form>
    """
}

# Serve templates dynamically
@app.route('/<template>')
def serve_template(template):
    return templates.get(template, "Template not found"), 200, {'Content-Type': 'text/html'}

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if not exist
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password=generate_password_hash("admin123"), role="admin")
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
