from flask import Flask
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

from .config import Config
from .models import db, User

#~~~ Define extensions (sockets, password encryption, login manager and limiter related~~~#
socketio = SocketIO()
bcrypt = Bcrypt()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

#~~~ Login manager configuration ~~~#
login_manager.login_view = "auth.login"  # Use this structure -> blueprint_name.name_view

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#~~~ Initialize extensions with app context, import bp and sockets, register bp

def create_app(config_class=Config):

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    app = Flask(__name__,
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))
    
    app.config.from_object(config_class)

    db.init_app(app)
    socketio.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    from .main.routes import main_bp
    from .auth.routes import auth_bp
    from .chat.routes import chat_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth') 
    app.register_blueprint(chat_bp, url_prefix='/chat') 

    from . import sockets 

    return app