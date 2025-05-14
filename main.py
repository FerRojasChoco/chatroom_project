import sql_setup
from dotenv import load_dotenv  #esta mierda no se pq puta hay que importar otv aca si ya esta en sql_setup.py ayuda!
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from flask_login import login_user, LoginManager, login_required, logout_user, current_user

from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError


import random
from string import ascii_uppercase


#flask app definition
app = Flask(__name__)
app.config["SECRET_KEY"] = "antone" # TODO: make this more secure

socketio = SocketIO(app)
rooms = {}  #for storing info about different rooms

bcrypt = Bcrypt(app)    #bcrypt object defined for encrypting the user's passwords

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
@app.route("/", methods=["POST", "GET"])    #defines methods applicable in this route
@app.route("/")
def intro():
   return render_template("intro.html")

@app.route("/home", methods=["GET","POST"])
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



#~~~ Login funcitonality block ~~~#
@app.route("/login", methods=["POST", "GET"])
def login():
    form = LoginForm()

    return render_template('login.html', form=form)

class LoginForm(FlaskForm):  
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")



#~~~ Register functionality block ~~~#
@app.route("/register", methods=["POST", "GET"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        sql_setup.register_user(form.username.data, hashed_password)

    return render_template('register.html', form=form)

class RegisterForm(FlaskForm):  
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Register")

    def validate_username(self, username):  #checks wheter if the username is taken or not
        existing_user = sql_setup.find_username(username.data)  
        if existing_user is not None:
            raise ValidationError('That username already exists. Please write a different one.')



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
    socketio.run(app, debug=True)   #debug true: any change made on the server that doesn't "break" the code will auto refresh, otherwise we need to re-run