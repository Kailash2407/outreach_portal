from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from models import db, User
from routes.auth import auth as auth_blueprint
from routes.admin import admin as admin_blueprint
from routes.student import student as student_blueprint
from flask_login import LoginManager
import os

def create_app():
    app = Flask(__name__)
    
    # 1. BASIC CONFIGURATION
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-999')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. FILE UPLOAD CONFIGURATION
    # Explicitly defines the path to backend/static/uploads
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Ensure the upload directory physically exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # 3. INITIALIZE EXTENSIONS
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 4. REGISTER BLUEPRINTS
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(student_blueprint)

    # 5. DATABASE & ADMIN INITIALIZATION
    with app.app_context():
        db.create_all()
        
        # Only create admin if not in production or if doesn't exist
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
                print("--- SYSTEM READY: Admin 'admin' created ---")

    return app
app = create_app()
if __name__ == '__main__':
    # For production, use host='0.0.0.0' and debug=False
    app.run(
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
