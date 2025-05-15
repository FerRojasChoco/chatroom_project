from flask import Blueprint
chat_bp = Blueprint('chat', __name__, template_folder='../../templates/chat')
from . import routes