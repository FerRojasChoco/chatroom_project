from pymongo import MongoClient
from datetime import datetime
from app import db
from app.models import GlobalLeaderboard, User

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client['chatroom_game']
game_logs = mongo_db['game_logs']

def log_game_result(user_id, username, code_id, submitted_line, score, is_correct, duration, room_name):
    """Log a game result to MongoDB"""
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


def generate_leaderboard(room_id):
    pipeline = [
        {"$match": {"room": room_id}},
        {"$group": {"_id": "$username", "score": {"$sum": "$score"}}},
        {"$sort": {"score": -1}},
        {"$limit": 10}
    ]
    leaderboard = list(game_logs.aggregate(pipeline))
    
    for entry in leaderboard:
        entry["username"] = entry.pop("_id")

    return leaderboard

def update_global_leaderboard(room_id):
    try:
        mongo_collection = mongo_client["chatroom_game"]["game_logs"]
        room_results = list(mongo_collection.find({"room": room_id}))

        if not room_results:
            return False, "No game results found for room"

        leaderboard_updates = {}

        for result in room_results:
            uid = result["user_id"]
            username = result["username"]
            score = result["score"]

            if uid not in leaderboard_updates:
                leaderboard_updates[uid] = {"username": username, "score": 0}
            leaderboard_updates[uid]["score"] += score

        for uid, data in leaderboard_updates.items():
            existing_entry = GlobalLeaderboard.query.filter_by(user_id=uid).first()
            if existing_entry:
                existing_entry.score += data["score"]
            else:
                new_entry = GlobalLeaderboard(user_id=uid, username=data["username"], score=data["score"])
                db.session.add(new_entry)

        db.session.commit()
        print(">>> Updating leaderboard for room:", room_id)
        print(">>> Fetched room results:", room_results)
        return True, "Leaderboard updated"




    except Exception as e:
        return False, str(e)
