from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask
from flask_login import LoginManager

from models import db, User
from routes.auth import auth as auth_blueprint
from routes.admin import admin as admin_blueprint
from routes.student import student as student_blueprint


def create_app():
    app = Flask(__name__)

    # --------------------------------------------------
    # 1. BASIC CONFIGURATION
    # --------------------------------------------------
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'dev-secret-key-999'  # used only if env var missing
    )

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///database.db'
    )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --------------------------------------------------
    # 2. FILE UPLOAD CONFIGURATION
    # --------------------------------------------------
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # --------------------------------------------------
    # 3. INITIALIZE EXTENSIONS
    # --------------------------------------------------
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --------------------------------------------------
    # 4. REGISTER BLUEPRINTS
    # --------------------------------------------------
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(student_blueprint)

    # --------------------------------------------------
    # 5. DATABASE INITIALIZATION (SAFE)
    # --------------------------------------------------
    with app.app_context():
        try:
            db.create_all()
            print("✓ Database tables ensured")

            # ❗ Admin creation ONLY for local/dev
            if os.environ.get('FLASK_ENV') != 'production':
                admin_user = User.query.filter_by(role='admin').first()
                if not admin_user:
                    admin = User(
                        name="System Admin",
                        username="admin",
                        role="admin",
                        register_number="ADMIN001",
                        section="MAIN",
                        dept="ADMINISTRATION",
                        sigbed_team="CORE"
                    )
                    admin.set_password("admin123")
                    db.session.add(admin)
                    db.session.commit()
                    print("✓ Dev admin user created")

        except Exception as e:
            # 🚨 Critical: do NOT crash production on DB warm-up/network delay
            print("⚠️ Database initialization skipped:", str(e))

    return app


# --------------------------------------------------
# APP ENTRYPOINT (Gunicorn compatible)
# --------------------------------------------------
app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_ENV") == "development"
    )
