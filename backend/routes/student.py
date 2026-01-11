from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Pair, Team, Request

student = Blueprint('student', __name__)

@student.route('/student/dashboard')
@login_required
def student_dashboard():
    # 1. Get the current user's partner if they have one
    partner = None
    if current_user.pair_id:
        pair = Pair.query.get(current_user.pair_id)
        partner = next((s for s in pair.students if s.id != current_user.id), None)

    # 2. Get incoming requests (sent TO current user)
    incoming_requests = Request.query.filter_by(receiver_id=current_user.id, status='pending').all()

    # 3. Get IDs of people user already sent requests TO
    sent_request_ids = [r.receiver_id for r in Request.query.filter_by(sender_id=current_user.id).all()]

    # 4. Fetch available students for pairing
    available_students = User.query.filter_by(role='student', pair_id=None)\
        .filter(User.id != current_user.id)\
        .filter(~User.id.in_(sent_request_ids))\
        .all()

    return render_template('student_dashboard.html', 
                           partner=partner, 
                           requests=incoming_requests, 
                           available_students=available_students)

@student.route('/student/select-partner', methods=['GET', 'POST'])
@login_required
def select_pair():
    if current_user.pair_id:
        flash("You are already paired!", "info")
        return redirect(url_for('student.student_dashboard'))

    if request.method == 'POST':
        receiver_id = request.form.get('partner_id')
        receiver = User.query.get(receiver_id)
        
        if not receiver or receiver.pair_id:
            flash("That student is no longer available.", "danger")
            return redirect(url_for('student.select_pair'))

        existing_req = Request.query.filter_by(sender_id=current_user.id, 
                                             receiver_id=receiver_id, 
                                             status='pending').first()
        if existing_req:
            flash("Request already pending.", "warning")
            return redirect(url_for('student.student_dashboard'))

        new_request = Request(sender_id=current_user.id, receiver_id=receiver_id)
        db.session.add(new_request)
        db.session.commit()
        
        flash(f"Invitation sent to {receiver.name}!", "success")
        return redirect(url_for('student.student_dashboard'))

    available_students = User.query.filter_by(role='student', pair_id=None).filter(User.id != current_user.id).all()
    return render_template('student_select_pair.html', students=available_students)

@student.route('/student/accept-request/<int:request_id>')
@login_required
def accept_request(request_id):
    invite = Request.query.get_or_404(request_id)

    if invite.receiver_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for('student.student_dashboard'))

    sender = User.query.get(invite.sender_id)
    if sender.pair_id or current_user.pair_id:
        db.session.delete(invite)
        db.session.commit()
        flash("Request expired.", "warning")
        return redirect(url_for('student.student_dashboard'))

    try:
        new_pair = Pair()
        db.session.add(new_pair)
        db.session.flush()

        sender.pair_id = new_pair.id
        current_user.pair_id = new_pair.id

        # Clean up all related requests
        Request.query.filter((Request.sender_id == current_user.id) | 
                             (Request.receiver_id == current_user.id) |
                             (Request.sender_id == sender.id) | 
                             (Request.receiver_id == sender.id)).delete()

        db.session.commit()
        flash(f"Success! You are now paired with {sender.name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error creating pair.", "danger")

    return redirect(url_for('student.student_dashboard'))

@student.route('/student/view-team')
@login_required
def view_team():
    # Validation: Must have a pair AND that pair must be assigned to a team by admin
    if not current_user.pair_id or not current_user.pair.team_id:
        flash("Your 4-member outreach team has not been formed yet. Please wait for faculty assignment.", "info")
        return redirect(url_for('student.student_dashboard'))

    # Fetch the team and pass it to the template
    team = Team.query.get(current_user.pair.team_id)
    return render_template('student_view_team.html', team=team)