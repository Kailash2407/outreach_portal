from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)  # ✅ FIXED
    name = db.Column(db.String(100), nullable=False)

    register_number = db.Column(db.String(20), unique=True, nullable=False)
    section = db.Column(db.String(10), nullable=False)
    dept = db.Column(db.String(50), nullable=False)
    sigbed_team = db.Column(db.String(100), nullable=False)

    role = db.Column(db.String(20), default='student')
    pair_id = db.Column(db.Integer, db.ForeignKey('pair.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')


class Pair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    students = db.relationship('User', backref='pair', lazy=True)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    team_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school_name = db.Column(db.String(200), nullable=True)
    outreach_date = db.Column(db.String(50), nullable=True)
    time_interval = db.Column(db.String(50), nullable=True)
    topic = db.Column(db.String(200), nullable=True)

    material_filename = db.Column(db.String(200), nullable=True)

    pairs = db.relationship('Pair', backref='team', lazy=True)
