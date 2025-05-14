from flask import render_template, session, current_app
from . import main_bp

@main_bp.route("/", methods=['GET', 'POST'])
def home():
    session.clear()
    current_app.logger.info("Session cleared, user at home page.")
    return render_template("home.html")