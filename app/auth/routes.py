from flask import render_template, request, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from . import auth_bp
from ..forms import LoginForm, RegisterForm
from ..models import db, User
from .. import bcrypt, limiter


#~~~ Login functionality block ~~~#
@auth_bp.route("/login", methods=['GET', 'POST'])
@limiter.limit("30 per minute") 
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                current_app.logger.info(f"User {user.username} logged in.") #log
                return redirect(url_for('chat.dashboard'))
            
    return render_template('login.html', form=form, title="Login")


#~~~ Logout functionality block ~~~#
@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    current_app.logger.info(f"User {current_user.username} logging out.") #log
    logout_user()
    return redirect(url_for('auth.login'))


#~~~ Register functionality block ~~~#
@auth_bp.route("/register", methods=['GET', 'POST'])
@limiter.limit("10 per hour") 
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        try:

            hashed_password = bcrypt.generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password=hashed_password)

            db.session.add(new_user)
            db.session.commit()

            current_app.logger.info(f"New user registered: {form.username.data}") #log

            return redirect(url_for('auth.login'))
        
        #~~~ Handle database error and unexpected errors ~~~#
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during registration for {form.username.data}: {str(e)}")
            return redirect(url_for('auth.register'))
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.critical(f"Unexpected error during registration for {form.username.data}: {str(e)}")
            return redirect(url_for('auth.register'))
        
    return render_template('register.html', form=form, title="Register")