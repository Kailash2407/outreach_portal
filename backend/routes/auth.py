from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from models import db, User

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student.student_dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username').lower().strip()
        reg_no = request.form.get('register_number').strip()
        section = request.form.get('section').upper()
        dept = request.form.get('dept')
        sigbed = request.form.get('sigbed_team')
        password = request.form.get('password')
        
        # Check if username or register number exists
        existing_user = User.query.filter(
            (User.username == username) | (User.register_number == reg_no)
        ).first()
        
        if existing_user:
            flash('Username or Register Number already exists.', 'error')
            return redirect(url_for('auth.register'))
            
        new_user = User(
            name=name, 
            username=username, 
            register_number=reg_no,
            section=section,
            dept=dept,
            sigbed_team=sigbed,
            role='student'
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').lower().strip()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.admin_dashboard' if user.role == 'admin' else 'student.student_dashboard'))
        
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))