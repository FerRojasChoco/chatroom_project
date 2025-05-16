from flask import render_template, request, session, redirect, url_for, current_app
from flask_login import login_required, current_user
from . import chat_bp
from ..utils import generate_unique_code, rooms 
from ..models import db, Code 

#~~~ Dashboard (logged in) route block ~~~#
@chat_bp.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == "POST":
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        room_id = code #renamed bc it was confusing in this function's context

        if join != False and not code: 
            return render_template("dashboard.html", error="Please enter a room code.", name=current_user.username)
        
        

        if create != False: 
            room_id = generate_unique_code(4)

            rooms[room_id] = {
                "members": 0,
                "messages": [],
                "current_code": None,
                "used_snippets": set()
            }
            current_app.logger.info(f"User {current_user.username} created room {room_id}") #log
       
        elif code not in rooms: 
            return render_template("dashboard.html", error="Room does not exist", code=code, name=current_user.username)
        
        session["room"] = room_id
        session["name"] = current_user.username
        return redirect(url_for("chat.room"))

    return render_template('dashboard.html', name=current_user.username)

#~~~ Room route block
@chat_bp.route("/room")
@login_required
def room():
    room_id = session.get("room") 
    name = session.get("name")   

    if room_id is None or name is None or room_id not in rooms:
        current_app.logger.warning(f"Access to /room denied or invalid. Room: {room_id}, Name: {name}, Room exists: {room_id in rooms if room_id else 'N/A'}")
        return redirect(url_for("main.home")) 
    
    if rooms[room_id]["current_code"] is None:
        random_code_obj = Code.query.order_by(db.func.rand()).first()
        rooms[room_id]["current_code"] = random_code_obj 

    #~~~ Logs ~~~#
        if random_code_obj: 
            current_app.logger.info(f"Loaded initial code snippet {random_code_obj.id} for room {room_id}")
        else:   
            current_app.logger.warning(f"No code snippets available for room {room_id}. 'current_code' is None.")


    return render_template(
        "room.html", 
        code=room_id, 
        messages=rooms[room_id]["messages"],
        snippet=rooms[room_id]["current_code"].full_code
    )