import os
import csv
import io
from datetime import datetime
from flask import send_file
from werkzeug.utils import secure_filename
from flask import current_app, Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Pair, Team

admin = Blueprint('admin', __name__)

# --- DASHBOARD & VIEWING ---

@admin.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('student.student_dashboard'))
    total_students = User.query.filter_by(role='student').count()
    unpaired_students = User.query.filter_by(role='student', pair_id=None).count()
    total_teams = Team.query.count()
    return render_template('admin_dashboard.html', total_students=total_students, unpaired=unpaired_students, total_teams=total_teams)

@admin.route('/admin/view_teams')
@login_required
def view_teams():
    if current_user.role != 'admin': return redirect(url_for('student.student_dashboard'))
    teams = Team.query.all()
    return render_template('admin_view_teams.html', teams=teams)

@admin.route('/admin/view_enrollments')
@login_required
def view_enrollments():
    if current_user.role != 'admin': return redirect(url_for('student.student_dashboard'))
    students = User.query.filter_by(role='student').all()
    return render_template('admin_view_enrollments.html', students=students)

# --- MEMBER ENROLLMENT (STUDENT & ADMIN) ---

@admin.route('/admin/enroll', methods=['GET', 'POST'])
@login_required
def enroll_member():
    """Enroll both students and admins/faculty"""
    if current_user.role != 'admin':
        return redirect(url_for('student.student_dashboard'))
    
    if request.method == 'POST':
        # Get common fields
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')  # 'student' or 'admin'
        
        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('admin.enroll_student'))
        
        try:
            if role == 'student':
                # Create student
                new_user = User(
                    username=username,
                    name=name,
                    register_number=request.form.get('register_number'),
                    section=request.form.get('section'),
                    dept=request.form.get('dept'),
                    sigbed_team=request.form.get('sigbed_team'),
                    role='student'
                )
                new_user.set_password(password)
                
            elif role == 'admin':
                # Create admin/faculty
                new_user = User(
                    username=username,
                    name=name,
                    role='admin',
                    register_number='ADMIN',
                    section='ADMIN',
                    dept='ADMINISTRATION',
                    sigbed_team='CORE'
                )
                new_user.set_password(password)
                
            else:
                flash('Invalid role selected', 'danger')
                return redirect(url_for('admin.enroll_student'))
            
            db.session.add(new_user)
            db.session.commit()
            flash(f'Successfully enrolled {name} as {role}!', 'success')
            return redirect(url_for('admin.view_enrollments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error enrolling member: {str(e)}', 'danger')
            return redirect(url_for('admin.enroll_student'))
    
    # GET request - show enrollment form
    return render_template('admin_enroll_student.html')  # Your HTML template name

# --- STUDENT MANAGEMENT ---

@admin.route('/admin/delete_student/<int:user_id>')
@login_required
def delete_student(user_id):
    if current_user.role != 'admin': return redirect(url_for('student.student_dashboard'))
    student = User.query.get_or_404(user_id)
    if student.pair_id:
        flash('Cannot delete a paired student. Unpair them first.', 'error')
    else:
        db.session.delete(student)
        db.session.commit()
        flash(f'Student {student.name} deleted.', 'success')
    return redirect(url_for('admin.view_enrollments'))

@admin.route('/admin/reset_password/<int:user_id>')
@login_required
def reset_password(user_id):
    student = User.query.get_or_404(user_id)
    student.set_password("reset123")
    db.session.commit()
    flash(f'Password reset to reset123', 'success')
    return redirect(url_for('admin.view_enrollments'))

# --- TEAM & PAIR MANAGEMENT ---

@admin.route('/admin/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    if current_user.role != 'admin': return redirect(url_for('student.student_dashboard'))
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        p1_id = request.form.get('pair1_id')
        p2_id = request.form.get('pair2_id')
        if p1_id == p2_id:
            flash('Error: You must select two different pairs!', 'error')
            return redirect(url_for('admin.create_team'))
        new_team = Team(team_name=team_name)
        db.session.add(new_team)
        db.session.flush()
        for p_id in [p1_id, p2_id]:
            pair = Pair.query.get(p_id)
            if pair: pair.team_id = new_team.id
        db.session.commit()
        flash(f'Team {team_name} assembled!', 'success')
        return redirect(url_for('admin.view_teams'))
    available_pairs = Pair.query.filter_by(team_id=None).all()
    return render_template('admin_create_team.html', pairs=available_pairs)

@admin.route('/disband_team/<int:team_id>', methods=['POST'])
@login_required
def disband_team(team_id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
        
    team = Team.query.get_or_404(team_id)
    
    try:
        # 1. Unlink the pairs from this team
        for pair in team.pairs:
            pair.team_id = None
        
        # 2. Delete the associated file if it exists
        if team.material_filename:
            file_path = os.path.join(current_app.root_path, 'static/uploads', team.material_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 3. Delete the team itself
        db.session.delete(team)
        db.session.commit()
        flash(f'Team "{team.team_name}" has been disbanded. Pairs are now available for reassignment.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error disbanding team.', 'danger')
        
    return redirect(url_for('admin.view_teams')) 

@admin.route('/admin/unpair_student/<int:user_id>')
@login_required
def unpair_student(user_id):
    if current_user.role != 'admin': return redirect(url_for('student.student_dashboard'))
    student = User.query.get_or_404(user_id)
    if student.pair_id:
        pair = Pair.query.get(student.pair_id)
        partner = User.query.filter(User.pair_id == pair.id, User.id != student.id).first()
        student.pair_id = None
        if partner: partner.pair_id = None
        db.session.delete(pair)
        db.session.commit()
        flash(f'Pairing dissolved for {student.name}.', 'success')
    return redirect(url_for('admin.view_enrollments'))

# --- MISSION & FILE UPLOAD ---

@admin.route('/admin/assign-mission/<int:team_id>', methods=['GET', 'POST'])
@login_required
def assign_mission(team_id):
    if current_user.role != 'admin': return redirect(url_for('student.student_dashboard'))
    team = Team.query.get_or_404(team_id)
    if request.method == 'POST':
        team.school_name = request.form.get('school_name')
        team.outreach_date = request.form.get('outreach_date')
        team.time_interval = request.form.get('time_interval')
        team.topic = request.form.get('topic')
        
        file = request.files.get('material_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            file.save(os.path.join(upload_path, filename))
            team.material_filename = filename 
            
        db.session.commit()
        flash(f'Mission and materials updated for {team.team_name}!', 'success')
        return redirect(url_for('admin.view_teams'))
    return render_template('admin_assign_mission.html', team=team)

# --- EXPORT FUNCTIONS ---

@admin.route('/export/students')
def export_students_csv():
    """Export all students to CSV"""
    try:
        # Get all student users (role='student')
        students = User.query.filter_by(role='student').all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Register Number', 'Name', 'Department', 'Section', 
                         'SIGBED Team', 'Username', 'Date Joined'])
        
        # Write student data
        for user in students:
            writer.writerow([
                user.register_number if hasattr(user, 'register_number') else '',
                user.name if hasattr(user, 'name') else '',
                user.dept if hasattr(user, 'dept') else '',
                user.section if hasattr(user, 'section') else '',
                user.sigbed_team if hasattr(user, 'sigbed_team') else '',
                user.username if hasattr(user, 'username') else '',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S') 
                if hasattr(user, 'date_joined') and user.date_joined else ''
            ])
        
        # Prepare response
        output.seek(0)
        
        filename = f"acm_sigbed_students_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting students: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin.route('/export/teams')
def export_teams_csv():
    """Export all teams to CSV"""
    try:
        teams = Team.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Team ID', 'Team Name', 'School', 'Outreach Date', 
                         'Topic', 'Total Pairs', 'Total Students', 'Status'])
        
        # Write team data
        for team in teams:
            total_students = 0
            for pair in team.pairs:
                total_students += len(pair.students) if pair.students else 0
            
            writer.writerow([
                team.id,
                team.team_name if team.team_name else '',
                team.school_name if team.school_name else '',
                team.outreach_date.strftime('%Y-%m-%d') if team.outreach_date else '',
                team.topic if team.topic else '',
                len(team.pairs) if team.pairs else 0,
                total_students,
                'Active' if team.pairs else 'Inactive'
            ])
        
        output.seek(0)
        
        filename = f"acm_sigbed_teams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting teams: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
