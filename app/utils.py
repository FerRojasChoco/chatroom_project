import random
from string import ascii_uppercase
from flask_socketio import emit
from .models import Code

#~~~ Global in-memory store for rooms ~~~#
rooms = {}


#~~~ Helper functions ~~~#

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code

def start_game(room_id):
    rooms[room_id]["game_active"] = True
    rooms[room_id]["snippets_completed"] = 0
    rooms[room_id]["used_snippets"] = set()
    rooms[room_id]["ready_users"] = set()

    load_new_snippet(room_id)

    emit("game_started", {
        "message": ": All players ready! Game started.",
        "snippets_remaining": rooms[room_id]["max_snippets"]
    }, to=room_id)

def load_new_snippet(room_id):
    used_ids = rooms[room_id]["used_snippets"]
    available_snippets = Code.query.filter(~Code.id.in_(used_ids)).all()

    if available_snippets:
        new_snippet = random.choice(available_snippets)
        rooms[room_id]["current_code"] = new_snippet
        emit("new_snippet", {
            "snippet": new_snippet.full_code,
            "message": f"Snippet {rooms[room_id]['snippets_completed'] + 1}/{rooms[room_id]['max_snippets']}"
        }, to=room_id)
    else:
        end_game(room_id, "No more snippets available!")

def end_game(room_id, message):
    rooms[room_id]["game_active"] = False
    emit("game_ended", {
        "message": message,
        "show_ready": True
    }, to=room_id)

