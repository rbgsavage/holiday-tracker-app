from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///holiday_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User roles
ROLES = ['admin', 'employee', 'manager', 'reviewer']

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class HoursEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    month = db.Column(db.String(20))
    hours = db.Column(db.Float)
    approved = db.Column(db.Boolean, default=False)

class HolidayRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    = db.Column(db.Boolean, default=False)

@app.before_first_request
def create_tables():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password_hash=generate_password_hash('adminpass'), role='admin')
        db.session.add(admin)
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role == 'employee':
        hours = HoursEntry.query.filter_by(user_id=user.id).all()
        holidays = HolidayRequest.query.filter_by(user_id=user.id).all()
        approved_hours = sum(h.hours for h in hours if h.approved)
        accrued = round(approved_hours * 0.1207, 2)
        used = sum((h.end_date - h.start_date).days + 1 for h in holidays if h.approved)
        remaining = round(accrued - used, 2)
        return render_template('employee_dashboard.html', hours=hours, holidays=holidays, accrued=accrued, used=used, remaining=remaining)
    elif user.role == 'manager':
        pending_hours = HoursEntry.query.filter_by(approved=False).all()
        pending_holidays = HolidayRequest.query.filter_by(approved=False).all()
        return render_template('manager_dashboard.html', pending_hours=pending_hours, pending_holidays=pending_holidays)
    elif user.role in ['admin', 'reviewer']:
        users = User.query.all()
        return render_template('admin_dashboard.html', users=users)
    return "Unknown role"

@app.route('/submit_hours', methods=['POST'])
def submit_hours():
    if 'user_id' in session and session['role'] == 'employee':
        month = request.form['month']
        hours = float(request.form['hours'])
        entry = HoursEntry(user_id=session['user_id'], month=month, hours=hours)
        db.session.add(entry)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/request_holiday', methods=['POST'])
def request_holiday():
    if 'user_id' in session and session['role'] == 'employee':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        request_entry = HolidayRequest(user_id=session['user_id'], start_date=start_date, end_date=end_date)
        db.session.add(request_entry)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/approve_hours/<int:entry_id>')
def approve_hours(entry_id):
    if 'user_id' in session and session['role'] == 'manager':
        entry = HoursEntry.query.get(entry_id)
        entry.approved = True
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/approve_holiday/<int:request_id>')
def approve_holiday(request_id):
    if 'user_id' in session and session['role'] == 'manager':
        request_entry = HolidayRequest.query.get(request_id)
        request_entry.approved = True
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
