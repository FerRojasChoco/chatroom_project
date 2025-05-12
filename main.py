import sql_setup

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError

import csv
import random
from string import ascii_uppercase


#~~~ Flask app and SQLalchemy object defintions ~~~#
app = Flask(__name__)


#~~~ Setting up database connection and app key ~~~#
app.config['SQLALCHEMY_DATABASE_URI'] = (f'mysql+pymysql://{sql_setup.user}:{sql_setup.pw}@{sql_setup.host}/chatroomdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disables a warning
app.config["SECRET_KEY"] = "antone" # TODO: make this more secure

sql_setup.db.init_app(app)


socketio = SocketIO(app)
rooms = {}  #for storing info about different rooms

bcrypt = Bcrypt(app)    #bcrypt object defined for encrypting the user's passwords

#~~~ Login Manager block ~~~#
login_manager = LoginManager()
login_manager.init_app(app) 
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return sql_setup.User.query.get(int(user_id))


#~~~ Function for random generating a code ~~~#
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code



#~~~ Route defs for each site/page ~~~#
#the @app.something is for defining things about each page
@app.route("/", methods=['GET', 'POST'])    #defines methods applicable in this route
def home():
    session.clear() #resets when entering "home" again
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

    

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code", code=code, name=name)
        
        room = code 
        #handle whether a user is joining or creating a room
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code  not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")



@app.route("/room") #this is where we get into sockets as well
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:    #this is so the user cant just go directly to a room, he must go first to home and then follow the registration for a room
        return redirect(url_for("home"))

    

    return render_template("room.html", code=room, messages=rooms[room]["messages"])    #last thing returned is for saving messages, this should be implemented with SQL



#~~~ Login functionality block ~~~#
@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()        

    if form.validate_on_submit():
        user = sql_setup.User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password ,form.password.data):   #compares given pw with stored pw (hashed ofc)
                login_user(user)
                return redirect(url_for('dashboard'))

    return render_template('login.html', form=form)

class LoginForm(FlaskForm):  
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")

#~~~ Logout block ~~~#
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


#~~~ Register functionality block ~~~#
@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = sql_setup.User(username=form.username.data, password=hashed_password)

        sql_setup.db.session.add(new_user)
        sql_setup.db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

class RegisterForm(FlaskForm):  
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Register")

    def validate_username(self, username):  #checks wheter if the username is taken or not
        existing_user = sql_setup.User.query.filter_by(username=username.data).first() 

        if existing_user:
            raise ValidationError('That username already exists. Please write a different one.')


#~~~ Dashboard (logged in) route block ~~~#
@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == "POST":
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if join != False and not code:
            return render_template("dashboard.html", error="Please enter a room code.")
        
        room = code

        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("dashboard.html", error="Room does not exist", code=code)
        
        session["room"] = room
        session["name"] = current_user.username
        return redirect(url_for("room"))

    return render_template('dashboard.html', name=current_user.username)



#~~~ Functions for interacting with a room ~~~#
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content) #TODO correct the date thing mentioned in room.html
    print(f"{session.get('name')} said: {data['data']}") #logs


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")

    if not room or not name:    #verifies room existence
        return
    if room not in rooms:       #verifies valid room
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)    #sends to everyone
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}") # logs

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]     #deletes the room if there are no members

        send({"name": name, "message": "has left the room"}, to=room)   
        print(f"{name} has left the room {room}") #just for debugging




if __name__ == "__main__":
    with app.app_context():
        sql_setup.db.create_all()

        sql_setup.Code.query.delete()
        sql_setup.db.session.commit()

        # inside the app context --> safe for DB actions
        with open('code.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                code_entry = sql_setup.Code(
                    id=int(row['id']),
                    full_code=row['full_code'],
                    error_line_number=int(row['error_line_number']),
                    correct_line=row['correct_line']
                )
                sql_setup.db.session.add(code_entry)
            sql_setup.db.session.commit()

    #socketio.run(app, host='0.0.0.0', port=5000, debug=False)   #run with this instead when testing for non local connections

    socketio.run(app, debug=True)   #debug true: any change made on the server that doesn't "break" the code will auto refresh, otherwise we need to re-run