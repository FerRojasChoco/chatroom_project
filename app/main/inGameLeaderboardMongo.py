from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017/")
mongo_db = client['chatroom_game']
game_logs = mongo_db['game_logs']

def log_game_result(user_id, username, code_id, submitted_line, score, is_correct, duration, room_name):
    game_logs.insert_one({
        "user_id": user_id,
        "username": username,
        "code_id": code_id,
        "submitted_line": submitted_line,
        "score": score,
        "is_correct": is_correct,
        "duration_seconds": duration,
        "room": room_name,
        "game_time": datetime.utcnow()
    })
