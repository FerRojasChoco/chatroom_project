from flask import session, current_app
from flask_socketio import join_room, leave_room, send, emit
from . import socketio 
from .utils import rooms, start_game, load_new_snippet, end_game
from .models import db, User, Code
from .InGameLeaderboardMongo import log_game_result, update_global_leaderboard, generate_leaderboard
from datetime import datetime
from flask import session
import threading
import time

#~~~ Function for handling messages ~~~#
@socketio.on("message")
def message(data):
    room_id = session.get("room")
    name = session.get("name")

    if not room_id or room_id not in rooms:
        current_app.logger.warning(f"Message from {name} for invalid room {room_id}") #log
        return

    current_code_obj = rooms[room_id]["current_code"]
    user_message = data["data"]

    content = {
        "name": name,
        "message": user_message
    }
    send(content, to=room_id)
    rooms[room_id]["messages"].append(content) #TODO correct the message time

    #~~~ Handles user submitting corrected line of code ~~~#
    if current_code_obj and user_message.strip() == current_code_obj.correct_line.strip():
        
        rooms[room_id]["snippets_completed"] += 1
        rooms[room_id]["used_snippets"].add(current_code_obj.id) #adds the correct answered snippet to the already used snippets

        victory_content = {
            "name": "System",
            "message": f": Correct! {name} found the answer. ({rooms[room_id]['snippets_completed']}/{rooms[room_id]['max_snippets']} completed)"
        }

        send(victory_content, to=room_id)
        rooms[room_id]["messages"].append(victory_content)

        #~~~ Leaderboard time related sub block ~~~#
        user = User.query.filter_by(username=name).first()
        start_time = rooms[room_id].get("start_time")

        if not start_time:
            start_time = datetime.utcnow()
            rooms[room_id]["start_time"] = start_time

        duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        user_id = user.id 
        username = name
        submitted_line = user_message.strip()
        code_id = current_code_obj.id
        score = 100  # Later make it more complex
        is_correct = True
        room_name = room_id

        print("HOLA SOY ANTES DE LOG GAME")
        log_game_result(user_id, username, code_id, submitted_line, score, is_correct, duration_seconds, room_name)
        socketio.emit("update_in_game_leaderboard", generate_leaderboard(room_id), to=room_id)
        
        print("HOLA SOY DESPUES DE LOG GAME")

        if rooms[room_id]["snippets_completed"] >= rooms[room_id]["max_snippets"]:
            end_game(room_id, "Game completed! All snippets solved.")
        else:
            load_new_snippet(room_id)


#~~~ Confirmation of snippet displayed ~~~#
@socketio.on("snippet_displayed")
def snippet_displayed():
    room_id = session.get("room")
    print(f"[SERVER] Received snippet_displayed for room {room_id}")
    if room_id in rooms:
        rooms[room_id]["start_time"] = datetime.utcnow()



#~~~ Function for handling user connections to a chatroom ~~~#
@socketio.on("connect")
def connect(auth):
    room_id = session.get("room")
    name = session.get("name")

    if not room_id or not name:
        current_app.logger.warning(f"Connection attempt with no room/name in session.") #log
        return 
    
    if room_id not in rooms:
        rooms[room_id] = {
            "members": 0,
            "messages": [],
            "current_code": None,
            "start_time": datetime.utcnow()  
        }
        current_app.logger.info(f"Initialized room {room_id} for the first time.")

        first_code = Code.query.order_by(db.func.rand()).first()
        if first_code:
            rooms[room_id]["current_code"] = first_code
            

            # Delay the emit by 0.5 seconds to give client time to fully join
            def delayed_emit():
                time.sleep(0.5)
                socketio.emit("new_snippet", {
                "snippet": first_code.full_code,
                "message": "First snippet loaded"
            }, to=room_id)
            threading.Thread(target=delayed_emit).start()
            
    join_room(room_id)
    rooms[room_id]["members"] += 1

    emit("member_count_update", {
        "count": rooms[room_id]["members"],
        "ready_count": len(rooms[room_id]["ready_users"])
    }, to=room_id)

    send({"name": name, "message": "has entered the room"}, to=room_id)
    current_app.logger.info(f"{name} joined room {room_id}. Members: {rooms[room_id]['members']}") #log



@socketio.on("request_in_game_leaderboard")
def send_in_game_leaderboard():
    room_id = session.get("room")
    if not room_id:
        return
    leaderboard = generate_leaderboard(room_id)  
    emit("update_in_game_leaderboard", leaderboard, to=room_id)


#~~~ Function for handling user disconnection from a chatroom ~~~#
@socketio.on("disconnect")
def disconnect():
    room_id = session.get("room")
    name = session.get("name")

    if room_id and name and room_id in rooms:
        leave_room(room_id)
        rooms[room_id]["members"] -= 1

        #~~~ REmove from ready users ~~~#
        if name in rooms[room_id]["ready_users"]:
            rooms[room_id]["ready_users"].remove(name)

        emit("member_count_update", {
            "count": rooms[room_id]["members"],
            "ready_count": len(rooms[room_id]["ready_users"])    
        }, to=room_id)

        if rooms[room_id]["members"] <= 0:
            current_app.logger.info(f"Room {room_id} is empty, deleting.") #log
            success, msg = update_global_leaderboard(room_id)
            
            if not success:
                current_app.logger.warning(f"FAiled to update leaderboard: {msg}")

            del rooms[room_id]
        
        send({"name": name, "message": "has left the room"}, to=room_id)
        current_app.logger.info(f"{name} left room {room_id}. Members left: {rooms[room_id].get('members', 0) if room_id in rooms else 'N/A (room deleted)'}") #log
   


@socketio.on("ready")
def handle_ready():
    room_id = session.get("room")
    name = session.get("name")

    if not room_id or room_id not in rooms:
        return

    rooms[room_id]["ready_users"].add(name)

    emit("user_ready", {
        "name": name,
        "ready_count": len(rooms[room_id]["ready_users"]),
        "total_users": rooms[room_id]["members"],
        "all_ready": False
    }, to=room_id)

    if len(rooms[room_id]["ready_users"]) == rooms[room_id]["members"]:
        start_game(room_id)
