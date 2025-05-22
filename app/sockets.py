from flask import session, current_app
from flask_socketio import join_room, leave_room, send, emit
from . import socketio 
from .utils import rooms 
# Added by Nico: Imports global leaderboard
from .models import db, User, Code, GlobalLeaderboard 
from .inGameLeaderboardMongo import log_game_result, update_global_leaderboard, generate_leaderboard
from datetime import datetime
from flask import session
import threading
import time

#~~~ Function for handling messages ~~~#
from datetime import datetime

@socketio.on("message")
def message(data):
    room_id = session.get("room")
    name = session.get("name")

     # Debug log: print time right now and what we think the start_time is
    print(f"[MESSAGE EVENT] At {datetime.utcnow().isoformat()} for room {room_id}")
    print(f"[MESSAGE EVENT] Current start_time for room: {rooms[room_id].get('start_time') if room_id in rooms else None}")

    if not room_id or room_id not in rooms:
        current_app.logger.warning(f"Message from {name} for invalid room {room_id}")  # log
        return

    # if rooms[room_id].get("start_time") is None:
    #     print("[MESSAGE EVENT] start_time not set; ignoring answer!")
    #     return

    current_code_obj = rooms[room_id]["current_code"]
    user_message = data["data"]

    content = {
        "name": name,
        "message": user_message
    }

    # Handles user submitting corrected line of code
    if current_code_obj and user_message.strip() == current_code_obj.correct_line.strip():
        victory_content = {
            "name": "System",
            "message": f"Correct! {name} found the answer."
        }

        send(victory_content, to=room_id)
        rooms[room_id]["messages"].append(victory_content)

        user = User.query.filter_by(username=name).first()
        if not user:
            current_app.logger.warning(f"Could not find user with username: {name}")
            return



        # Calculate duration_seconds since snippet start
        
        start_time = rooms[room_id].get("start_time")
        
        print(f"[DURATION DEBUG] start_time: {start_time}, now: {datetime.utcnow()}")
        # if start_time:
        #     duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        # else:
        #     duration_seconds = 0
        if not start_time:
            start_time = datetime.utcnow()
            rooms[room_id]["start_time"] = start_time

        duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        print(f"[DURATION DEBUG] Calculated duration_seconds: {duration_seconds}")


        user_id = user.id 
        username = name
        submitted_line = user_message.strip()
        code_id = current_code_obj.id
        score = 100  # Later make it more complex
        is_correct = True
        room_name = room_id

    
        log_game_result(user_id, username, code_id, submitted_line, score, is_correct, duration_seconds, room_name)

        # Added to update the leaderboard 
        socketio.emit("update_in_game_leaderboard", generate_leaderboard(room_id), to=room_id)


        # Load a new code snippet and reset start_time
        new_random_code = Code.query.order_by(db.func.rand()).first()
        if new_random_code:
            rooms[room_id]["current_code"] = new_random_code
            #rooms[room_id]["start_time"] = datetime.utcnow()  
            emit("new_snippet", {
                "snippet": new_random_code.full_code,
                "message": "New snippet loaded"
            }, to=room_id)
        else:
            emit("new_snippet", {
                "snippet": "No more snippets available!",
                "message": f"{name} solved it! But no more snippets."
            }, to=room_id)

    send(content, to=room_id)
    rooms[room_id]["messages"].append(content)  # TODO correct the message time
    current_app.logger.info(f"{name} in room {room_id} said: {user_message}")  # log

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
        current_app.logger.warning(f"Connection attempt with no room/name in session.")
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
    current_code = rooms[room_id].get("current_code")
    if current_code:
        emit("new_snippet", {
            "snippet": current_code.full_code,
            "message": "New snippet loaded"
        })  # Sends only to the connecting user

    send({"name": name, "message": "has entered the room"}, to=room_id)

    rooms[room_id]["members"] += 1
    emit("member_count_update", {"count": rooms[room_id]["members"]}, to=room_id)
    

    current_app.logger.info(f"{name} joined room {room_id}. Members: {rooms[room_id]['members']}") #log

# Added by Nico: This is to show the in game leaderboard
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
        emit("member_count_update", {"count": rooms[room_id]["members"]}, to=room_id)

        # Nico changed: This is in order to update the global leaderboard once the room is disconnected
        if rooms[room_id]["members"] <= 0:
            current_app.logger.info(f"Room {room_id} is empty, updating leaderboard and deleting room.") #log
            success, msg = update_global_leaderboard(room_id)
            print("LEADERBOARD UPDATED?", success, msg)

            if not success:
                current_app.logger.warning(f"Failed to update leaderboard: {msg}")
            del rooms[room_id]

        
        send({"name": name, "message": "has left the room"}, to=room_id)
        current_app.logger.info(f"{name} left room {room_id}. Members left: {rooms[room_id].get('members', 0) if room_id in rooms else 'N/A (room deleted)'}") #log
   
